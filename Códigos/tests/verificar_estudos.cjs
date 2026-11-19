// Somente fixture sintética em SQLite descartável e loopback 5091.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:5091';
const out=path.resolve('.ci-results/estudos-visual',new Date().toISOString().replace(/[:.]/g,'-'));
fs.mkdirSync(out,{recursive:true});
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const captures=[],errors=[];
  async function login(account){
    const context=await browser.newContext();
    const page=await context.newPage();
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);
    await page.locator('#email').fill(account+'@teste01.local');
    await page.locator('#senha').fill('Teste-escolas-2026!');
    await page.locator('button[type=submit]').click();
    await page.waitForURL(url=>new URL(url).pathname!=='/');
    return {page,context};
  }
  async function capture(page,name){
    for(const [suffix,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
      await page.setViewportSize({width,height});
      await page.evaluate(()=>document.fonts.ready);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,name+': overflow');
      const file=name+'-'+suffix+'.png';
      await page.screenshot({path:path.join(out,file),fullPage:true});captures.push(file);
    }
    await page.setViewportSize({width:1440,height:1000});
  }
  try{
    const teacher=await login('professor01'),student=await login('aluno02'),admin=await login('admin');
    const p=teacher.page,s=student.page,a=admin.page;
    await p.goto(base+'/estudos');await capture(p,'disciplinas-professor');
    await p.getByRole('link',{name:'Matemática · Turma Teste 01',exact:true}).click();
    const subject=p.url();await capture(p,'disciplina-vazia');
    await p.getByRole('link',{name:'Preparar conteúdo',exact:true}).click();
    await p.locator('[data-study-field=link]').waitFor({state:'hidden'});
    assert.equal(await p.locator('[data-study-field=link]').isVisible(),false);
    assert.equal(await p.locator('[data-study-field=arquivo]').isVisible(),false);
    await p.getByLabel('Título',{exact:true}).fill('Orientação para a próxima aula');
    await p.getByLabel('Texto ou orientação de estudo',{exact:true}).fill('Revise funções e anote suas dúvidas para discutirmos na próxima aula.');
    await p.getByLabel('Título',{exact:true}).focus();await p.keyboard.press('Tab');
    assert.equal(await p.getByLabel('Texto ou orientação de estudo',{exact:true}).evaluate(el=>el===document.activeElement),true);
    await capture(p,'preparar-aviso');
    await p.getByRole('button',{name:'Salvar rascunho',exact:true}).click();
    await p.getByRole('link',{name:'Editar rascunho',exact:true}).waitFor();
    const draft=p.url();await capture(p,'rascunho');
    assert.equal((await student.context.request.get(draft)).status(),404);
    await s.goto(subject);
    assert.equal(await s.getByRole('link',{name:'Orientação para a próxima aula',exact:true}).count(),0);
    await p.getByRole('button',{name:'Enviar para publicação',exact:true}).click();
    await p.getByText('A publicação está em revisão.',{exact:false}).waitFor();
    await capture(p,'publicacao-pendente');
    async function approve(){
      await a.goto(base+'/solicitacoes');
      const item=a.locator('article').filter({has:a.getByRole('heading',{name:/Publicar aviso ou material de estudo/})}).filter({has:a.getByRole('button',{name:'Aprovar e aplicar',exact:true})}).first();
      await item.getByRole('link',{name:'Conferir aviso ou material',exact:true}).click();
      await a.getByRole('heading',{name:'Organizar conteúdo',exact:true}).waitFor();
      await a.goto(base+'/solicitacoes');
      await a.locator('article').filter({has:a.getByRole('heading',{name:/Publicar aviso ou material de estudo/})}).filter({has:a.getByRole('button',{name:'Aprovar e aplicar',exact:true})}).first().getByRole('button',{name:'Aprovar e aplicar',exact:true}).click();
    }
    await approve();
    await s.goto(subject);await s.getByRole('link',{name:'Orientação para a próxima aula',exact:true}).click();
    await capture(s,'aviso-aluno');
    await p.goto(subject);await p.getByRole('link',{name:'Preparar conteúdo',exact:true}).click();
    await p.getByLabel(/Tipo de conteúdo/).selectOption('arquivo');
    assert.equal(await p.locator('[data-study-field=arquivo]').isVisible(),true);
    assert.equal(await p.locator('[data-study-field=link]').isVisible(),false);
    await p.getByLabel('Título',{exact:true}).fill('Apostila de funções');
    await p.getByLabel('Texto ou orientação de estudo',{exact:true}).fill('Leia o capítulo 1 antes da próxima aula.');
    await p.locator('input[type=file]').setInputFiles({name:'apostila.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nApostila ficticia\n%%EOF')});
    await p.getByRole('button',{name:'Salvar rascunho',exact:true}).click();
    const fileDraft=p.url();
    assert.equal((await student.context.request.get(fileDraft+'/arquivo')).status(),404);
    await p.getByRole('button',{name:'Enviar para publicação',exact:true}).click();
    await approve();
    await s.goto(subject+'?aba=materiais');await s.getByRole('link',{name:'Apostila de funções',exact:true}).click();
    await capture(s,'material-aluno');
    const downloaded=s.waitForEvent('download');
    await s.getByRole('link',{name:'Baixar material de estudo',exact:true}).click();
    const download=await downloaded;assert.ok(download.suggestedFilename().endsWith('.pdf'));
    assert.ok(fs.readFileSync(await download.path()).toString().startsWith('%PDF-1.4'));
    await p.goto(subject);await p.getByRole('link',{name:'Preparar conteúdo',exact:true}).click();
    await p.getByLabel(/Tipo de conteúdo/).selectOption('link');
    await p.getByLabel('Título',{exact:true}).fill('Guia complementar');
    await p.getByLabel('Link HTTPS do material',{exact:true}).fill('https://example.test/guia');
    await p.getByRole('button',{name:'Salvar rascunho',exact:true}).click();
    await p.getByRole('button',{name:'Enviar para publicação',exact:true}).click();
    await approve();
    await s.goto(subject+'?aba=materiais');await capture(s,'materiais-aluno');
    assert.equal(await s.getByRole('link',{name:'Guia complementar',exact:true}).count(),1);
    await p.goto(subject);
    await p.getByRole('link',{name:'Organizar abas',exact:true}).click();
    await capture(p,'abas-vazias');
    await p.getByLabel('Nome da aba',{exact:true}).fill('Unidade 1');
    await p.getByLabel('Ordem da aba',{exact:true}).fill('10');
    await p.getByLabel('Nome da aba',{exact:true}).focus();await p.keyboard.press('Tab');
    assert.equal(await p.getByLabel('Ordem da aba',{exact:true}).evaluate(el=>el===document.activeElement),true);
    await p.getByRole('button',{name:'Criar aba',exact:true}).click();
    await p.getByRole('link',{name:'Unidade 1',exact:true}).waitFor();
    const sectionArticle=p.locator('article').filter({has:p.getByRole('link',{name:'Unidade 1',exact:true})});
    await sectionArticle.getByLabel('Nome',{exact:true}).fill('Revisão de funções');
    await sectionArticle.getByLabel('Ordem',{exact:true}).fill('2');
    await sectionArticle.getByRole('button',{name:'Salvar aba',exact:true}).click();
    await p.getByRole('link',{name:'Revisão de funções',exact:true}).waitFor();
    await capture(p,'abas-organizadas');
    await p.getByRole('link',{name:'Revisão de funções',exact:true}).click();
    const customTab=p.url();await capture(p,'aba-personalizada-vazia');
    await p.getByRole('link',{name:'Preparar conteúdo',exact:true}).click();
    assert.equal(await p.getByLabel('Aba do conteúdo',{exact:true}).inputValue(),new URL(customTab).searchParams.get('aba').slice(6));
    await p.getByLabel('Título',{exact:true}).fill('Exercícios da unidade');
    await p.getByLabel('Texto ou orientação de estudo',{exact:true}).fill('Resolva os exercícios 1 a 5 e registre suas dúvidas.');
    await capture(p,'rascunho-na-aba');
    await p.getByRole('button',{name:'Salvar rascunho',exact:true}).click();
    await p.getByRole('link',{name:'Editar rascunho',exact:true}).waitFor();
    const customContent=p.url();
    await s.goto(customTab);
    assert.equal(await s.getByRole('link',{name:'Exercícios da unidade',exact:true}).count(),0);
    await p.getByRole('button',{name:'Enviar para publicação',exact:true}).click();
    await approve();
    await s.goto(customTab);
    await s.getByRole('link',{name:'Exercícios da unidade',exact:true}).waitFor();
    await capture(s,'aba-aluno-publicada');
    await p.goto(subject);await p.getByRole('link',{name:'Organizar abas',exact:true}).click();
    await p.locator('article').filter({has:p.getByRole('link',{name:'Revisão de funções',exact:true})}).getByRole('button',{name:'Arquivar aba',exact:true}).click();
    await p.getByText('Aba arquivada. Os alunos perderam o acesso',{exact:false}).waitFor();
    await capture(p,'aba-arquivada');
    assert.equal((await student.context.request.get(customTab)).status(),404);
    assert.equal((await student.context.request.get(customContent)).status(),404);
    await s.goto(subject);
    assert.equal(await s.getByRole('link',{name:'Revisão de funções',exact:true}).count(),0);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'resumo.json'),JSON.stringify({passed:true,captures,errors,
      scope:'MS02 e MS03: conteúdo com revisão, download privado, criar/renomear/ordenar/arquivar aba; revogação de acesso direto; teclado e desktop/mobile'},null,2));
    console.log('Espaço da disciplina aprovado no navegador. Evidências: '+out);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});

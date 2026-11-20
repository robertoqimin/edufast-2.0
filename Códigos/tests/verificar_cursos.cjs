// Executar apenas na demonstração QA descartável 5093; jamais no ambiente manual.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:5093';
const out=path.resolve('.ci-results/cursos-visual',new Date().toISOString().replace(/[:.]/g,'-'));
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const captures=[],errors=[];
 async function login(account,js=true){
  const context=await browser.newContext({javaScriptEnabled:js});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.locator('#email').fill(account+'@teste01.local');
  await page.locator('#senha').fill('Teste-escolas-2026!');await page.locator('button[type=submit]').click();
  await page.waitForURL(u=>new URL(u).pathname!=='/');return {page,context};
 }
 async function capture(page,name){
  for(const [suffix,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
   await page.setViewportSize({width,height});await page.evaluate(()=>document.fonts.ready);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,name+' overflow');
   assert.equal(await page.evaluate(()=>{
    const sample=document.createElement('span');sample.style.color='var(--text)';document.body.append(sample);
    const expected=getComputedStyle(sample).color;sample.remove();
    return [...document.querySelectorAll('.course-workspace .notice')].every(el=>getComputedStyle(el).color===expected);
   }),true,name+' cores dos avisos');
   const file=name+'-'+suffix+'.png';await page.screenshot({path:path.join(out,file),fullPage:true});captures.push(file);
  }await page.setViewportSize({width:1440,height:1000});
 }
 try{
  const student=await login('aluno02'),teacher=await login('professor01'),admin=await login('admin');
  const s=student.page,p=teacher.page,a=admin.page;
  await s.goto(base+'/cursos');await capture(s,'biblioteca-aluno');
  await s.getByRole('button',{name:'Continuar estudando',exact:true}).click();
  await s.getByRole('heading',{name:'Razões e escalas',exact:true}).waitFor();
  await capture(s,'aula-texto');assert.equal(await s.locator('iframe').count(),0);
  await s.getByRole('button',{name:'Próxima aula',exact:true}).click();
  await s.getByRole('heading',{name:'Regra de três e proporcionalidade',exact:true}).waitFor();
  await s.goto(base+'/cursos');await s.getByRole('button',{name:'Continuar estudando',exact:true}).click();
  await s.getByRole('heading',{name:'Regra de três e proporcionalidade',exact:true}).waitFor();
  await s.getByRole('button',{name:'Marcar como concluída',exact:true}).click();
  await s.getByText('✓ Aula concluída',{exact:true}).waitFor();await capture(s,'aula-concluida');
  await s.getByRole('button',{name:'Leitura de gráficos e pontos',exact:true}).click();
  const download= s.waitForEvent('download');await s.getByRole('link',{name:'Baixar Gráfico de f(x) = 2x + 3',exact:true}).click();
  const downloaded=await download;assert.equal(await downloaded.failure(),null);
  assert.equal((await student.context.request.get(base+'/aprendizagem/cursos/2')).status(),403);
  await p.goto(base+'/cursos');await capture(p,'biblioteca-professor');
  await p.locator('article').filter({has:p.getByRole('heading',{name:'Matemática para o ENEM — laboratório do professor',exact:true})}).getByRole('link',{name:'Organizar curso',exact:true}).click();
  await capture(p,'editor-professor');
  await p.getByLabel('Título do novo módulo',{exact:true}).fill('Revisão final');
  await p.getByRole('button',{name:'Adicionar módulo',exact:true}).click();
  const module=p.locator('.course-module').filter({has:p.getByRole('heading',{name:/Revisão final/})});
  await module.getByLabel('Título do novo capítulo',{exact:true}).fill('Simulado autoral');
  await module.getByRole('button',{name:'Adicionar capítulo',exact:true}).click();
  const chapter=p.locator('.course-chapter').filter({has:p.getByRole('heading',{name:'Simulado autoral',exact:true})});
  await chapter.getByRole('link',{name:'Nova aula de texto',exact:true}).click();
  await p.getByLabel('Título da aula',{exact:true}).fill('Questão de revisão');
  await p.getByLabel('Conteúdo da aula de texto',{exact:true}).fill('Uma turma acertou 18 de 30 questões. Qual foi a porcentagem de acertos?\nGabarito: 60%.');
  await p.getByLabel('Título da aula',{exact:true}).focus();await p.keyboard.press('Tab');
  assert.equal(await p.locator('select[name=tipo_aula]').evaluate(el=>el===document.activeElement),true);
  await capture(p,'editar-aula');await p.getByRole('button',{name:'Salvar aula',exact:true}).click();
  await p.getByRole('heading',{name:'Questão de revisão',exact:true}).waitFor();
  await p.locator('summary').filter({hasText:'Adicionar link'}).click();
  await p.getByLabel('Título do link',{exact:true}).fill('Material complementar');
  await p.getByLabel('Endereço do material',{exact:true}).fill('https://example.com/estudo');
  await p.getByRole('button',{name:'Adicionar link',exact:true}).click();
  await p.getByRole('heading',{name:'Material complementar',exact:true}).waitFor();
  await p.getByRole('link',{name:'← Organização do curso',exact:true}).click();
  await p.locator('.course-chapter').filter({has:p.getByRole('heading',{name:'Simulado autoral',exact:true})}).getByRole('link',{name:'Nova aula de vídeo',exact:true}).click();
  await p.getByLabel('Título da aula',{exact:true}).fill('Vídeo de teste do player');
  await p.getByLabel('Vídeo do YouTube (para formato vídeo)',{exact:true}).fill('abcdefghijk');
  await p.getByRole('button',{name:'Salvar aula',exact:true}).click();
  await p.getByRole('link',{name:'← Organização do curso',exact:true}).click();
  await p.getByRole('button',{name:'Solicitar publicação',exact:true}).click();
  await p.getByText('Publicação aguardando revisão',{exact:false}).waitFor();
  await capture(p,'curso-em-revisao');
  await a.goto(base+'/solicitacoes');
  const proposal=a.locator('article').filter({has:a.getByRole('heading',{name:/Publicar curso de aprendizagem/})}).filter({has:a.getByRole('button',{name:'Aprovar e aplicar',exact:true})}).first();
  await proposal.getByRole('link',{name:'Conferir curso',exact:true}).click();
  await capture(a,'revisao-administracao');await a.goto(base+'/solicitacoes');
  await proposal.getByRole('button',{name:'Aprovar e aplicar',exact:true}).click();
  await a.goto(base+'/aprendizagem/cursos/2');
  await a.getByRole('heading',{name:'Turmas com acesso',exact:true}).waitFor();
  await a.getByRole('button',{name:'Salvar acesso da turma',exact:true}).click();
  await a.getByText('Preparatório ENEM — 2026 · Acesso ativo',{exact:true}).waitFor();
  await capture(a,'curso-publicado');
  await s.goto(base+'/aprendizagem');
  await s.locator('article').filter({has:s.getByRole('heading',{name:'Matemática para o ENEM — laboratório do professor',exact:true})}).getByRole('button',{name:'Continuar estudando',exact:true}).click();
  await s.getByRole('button',{name:'Vídeo de teste do player',exact:true}).click();
  assert.equal(await s.locator('iframe').count(),0);
  await capture(s,'video-sob-demanda');
  await s.route('https://www.youtube-nocookie.com/**',route=>route.fulfill({status:200,contentType:'text/html',body:'<p>Player externo substituído somente neste teste.</p>'}));
  await s.getByRole('button',{name:'Carregar vídeo do YouTube',exact:true}).click();
  assert.match(await s.locator('iframe').getAttribute('src'),/youtube-nocookie.com\/embed\/abcdefghijk$/);
  const signed=await login('aluno03');
  const nojsContext=await browser.newContext({javaScriptEnabled:false,storageState:await signed.context.storageState()});
  const nojs={page:await nojsContext.newPage()};await nojs.page.goto(base+'/aprendizagem');
  await nojs.page.locator('article').first().getByRole('button',{name:'Continuar estudando',exact:true}).click();
  await nojs.page.getByRole('button',{name:'Próxima aula',exact:true}).click();
  await nojs.page.getByRole('heading',{name:'Regra de três e proporcionalidade',exact:true}).waitFor();
  assert.equal(await nojs.page.getByRole('button',{name:'Marcar como concluída',exact:true}).count(),1);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'resumo.json'),JSON.stringify({passed:true,captures,errors,base},null,2));
  console.log(JSON.stringify({passed:true,out,captures:captures.length}));
 }catch(error){fs.writeFileSync(path.join(out,'resumo.json'),JSON.stringify({passed:false,error:error.stack,captures,errors},null,2));throw error;}
 finally{await browser.close();}
})();

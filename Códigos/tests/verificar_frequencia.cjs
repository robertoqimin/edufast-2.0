// Somente o servidor sintético e descartável na porta 5091.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const out = path.resolve('.ci-results/frequencia-visual');
fs.mkdirSync(out, {recursive: true});
const base = 'http://127.0.0.1:5091';
(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const captures = [], errors = [];
  const teacher = await browser.newContext(), admin = await browser.newContext(), student = await browser.newContext();
  async function login(context, account) {
    const page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    await page.locator('#email').fill(account+'@teste01.local');
    await page.locator('#senha').fill('Teste-escolas-2026!');
    await page.locator('button[type=submit]').click();
    await page.waitForURL(url => new URL(url).pathname !== '/');
    return page;
  }
  async function capture(page, name) {
    for (const [suffix,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
      await page.setViewportSize({width,height}); await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth+1), false, `${name}: overflow`);
      const file = `${name}-${suffix}.png`;
      await page.screenshot({path:path.join(out,file),fullPage:true}); captures.push(file);
    }
    await page.setViewportSize({width:1440,height:1000});
  }
  try {
    const p = await login(teacher,'professor01');
    await p.goto(base+'/frequencia'); await capture(p,'professor-painel');
    await p.getByRole('link',{name:'Turma Teste 01 · Matemática',exact:true}).click();
    await capture(p,'chamada');
    const when = await p.locator('[name=dia]').inputValue();
    const selects = p.locator('select[name^=aluno_]');
    assert.equal(await selects.count(),20);
    for(let i=0;i<20;i++) await selects.nth(i).selectOption(i===1?'falta':'presente');
    await p.getByRole('button',{name:'Enviar chamada para aprovação'}).click();
    await p.getByText('Chamada enviada para aprovação administrativa.',{exact:true}).waitFor();
    const a = await login(admin,'admin');
    await a.goto(base+'/frequencia');
    await a.getByRole('link',{name:'Conferir chamada',exact:true}).first().click();
    await capture(a,'aprovacao');
    await a.locator('[name=motivo]').fill('Chamada conferida no teste');
    await a.getByRole('button',{name:'Aprovar chamada',exact:true}).click();
    const s = await login(student,'aluno02');
    await s.goto(base+'/frequencia');
    await s.locator('[name=inicio]').last().fill(when);
    await s.locator('[name=fim]').last().fill(when);
    await s.locator('[name=arquivo]').setInputFiles({name:'atestado-teste.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nDocumento sintetico\n%%EOF')});
    await s.getByRole('button',{name:'Enviar para análise'}).click();
    await a.goto(base+'/frequencia'); await capture(a,'atestados');
    await a.locator('form[action*="/atestado/"] [name=motivo]').fill('Período conferido sem dados médicos');
    await a.getByRole('button',{name:'Aceitar atestado',exact:true}).click();
    await a.goto(base+`/frequencia/relatorio?inicio=${when}&fim=${when}`);
    await capture(a,'relatorio');
    const row = a.locator('table').first().locator('tbody tr').filter({hasText:'Aluno 02 - Teste 01'});
    assert.equal((await row.locator('td').allTextContents()).join('|'),'Aluno 02 - Teste 01|1|0|0|1|1|0.00%');
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'resumo.json'),JSON.stringify({passed:true,captures,errors,
      scope:'professor envia 20 alunos, admin aprova, aluno envia atestado, admin aceita, falta permanece justificada'},null,2));
    console.log('Frequencia: chamada, aprovacao, atestado e relatorio aprovados no navegador.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});

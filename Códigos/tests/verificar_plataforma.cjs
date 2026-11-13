// Regressão headless somente no servidor sintético de platform-demo.cjs.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const base = 'http://127.0.0.1:5093';
const out = path.resolve('.ci-results/plataforma-visual');
fs.mkdirSync(out, {recursive: true});
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const page = await browser.newPage(), errors = [], captures = [];
  page.on('pageerror', error => errors.push(error.message));
  async function capture(name) {
    for (const [suffix,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
      await page.setViewportSize({width,height}); await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth+1), false, name+' overflow');
      const file = name+'-'+suffix+'.png';
      await page.screenshot({path:path.join(out,file),fullPage:true}); captures.push(file);
    }
    await page.setViewportSize({width:1440,height:1000});
  }
  try {
    await page.goto(base+'/login'); await capture('login-proprietario');
    await page.locator('#email').fill('dono@plataforma.local');
    await page.locator('#password').fill('Plataforma-teste-2026!');
    await page.getByRole('button',{name:'Entrar na plataforma'}).click(); await page.waitForURL(base+'/');
    const totals = await page.evaluate(async () => (await fetch('/?formato=json')).json());
    assert.equal(totals.totals.people,52); assert.equal(totals.totals.receita,120000);
    assert.equal(totals.totals.despesa,30000); assert.equal(totals.totals.lucro,90000);
    await capture('escolas-financeiro');
    await page.goto(base+'/pessoas'); await capture('pessoas');
    assert.equal(await page.locator('tbody tr').count(),50);
    await page.getByRole('link',{name:'Próxima página'}).click();
    assert.equal(await page.locator('tbody tr').count(),2);
    await page.goto(base+'/pessoas?escola=1');
    assert.equal(await page.locator('tbody tr').count(),26);
    await page.goto(base+'/escolas/1'); await capture('contrato-lancamentos');
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'Sair do painel'}).click();
    await page.waitForURL(base+'/login');
    await page.goto(base+'/pessoas'); await page.waitForURL(base+'/login');
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'resumo.json'),JSON.stringify({passed:true,captures,errors,
      scope:'Login/logout exclusivo, duas escolas, 52 contas, filtro/paginacao e resultados sinteticos; desktop/mobile'},null,2));
    console.log('Plataforma: login, escolas, financeiro, pessoas e logout aprovados no navegador.');
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});

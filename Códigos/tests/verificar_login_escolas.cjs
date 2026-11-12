// Regressão do app em navegador headless isolado, sem perfil pessoal ou dados reais.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const out = path.resolve('.ci-results/login-escolas');
fs.mkdirSync(out, {recursive: true});
const schools = [{id: 'teste01', port: 5081}, {id: 'teste02', port: 5082}];
(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const errors = [];
  const captures = [];
  async function screenshot(page, name) {
    for (const [suffix, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      await page.setViewportSize({width, height});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      const file = `${name}-${suffix}.png`;
      await page.screenshot({path: path.join(out, file), fullPage: true}); captures.push(file);
    }
    await page.setViewportSize({width: 1440, height: 1000});
  }
  try {
    // Mesmo host e portas diferentes: nomes de cookie precisam coexistir.
    const context = await browser.newContext();
    const pages = [];
    for (const school of schools) {
      const page = await context.newPage(); pages.push(page);
      page.on('pageerror', error => errors.push(error.message));
      const base = `http://127.0.0.1:${school.port}`;
      assert.equal((await page.goto(base)).status(), 200);
      await screenshot(page, `login-${school.id}`);
      await page.locator('#email').fill(`admin@${school.id}.local`);
      await page.locator('#senha').fill('Teste-escolas-2026!');
      await page.locator('button[type=submit]').click();
      await page.waitForURL('**/admin/dashboard');
      assert.equal((await (await page.request.get(base + '/auth/session')).json()).role, 'admin');
      await screenshot(page, `admin-${school.id}`);
    }
    // Entrar em B não encerra a sessão de A.
    for (const page of pages) assert.equal((await page.reload()).status(), 200);
    const cookies = await context.cookies();
    for (const school of schools) {
      assert.ok(cookies.some(c => c.name === `edufast_${school.id}` && c.httpOnly && c.sameSite === 'Lax'));
    }
    for (const school of schools) {
      for (const [role, destination] of [['professor', '/professor'], ['aluno', '/aluno']]) {
        const isolated = await browser.newContext();
        const page = await isolated.newPage(); page.on('pageerror', error => errors.push(error.message));
        await page.goto(`http://127.0.0.1:${school.port}`);
        await page.locator('#email').fill(`${role}01@${school.id}.local`);
        await page.locator('#senha').fill('Teste-escolas-2026!');
        await page.locator('button[type=submit]').click();
        await page.waitForURL(`**${destination}`);
        assert.equal((await page.request.get(`http://127.0.0.1:${school.port}/admin/dashboard`)).status(), 403);
        await isolated.close();
      }
    }
    // Credenciais válidas sem sessão persistida: erro claro, sem redirecionamento.
    const blockedContext = await browser.newContext();
    const blocked = await blockedContext.newPage();
    await blocked.route('**/auth/session', route => route.fulfill({status: 401, contentType: 'application/json', body: '{"authenticated":false}'}));
    await blocked.goto('http://127.0.0.1:5081');
    await blocked.locator('#email').fill('admin@teste01.local');
    await blocked.locator('#senha').fill('Teste-escolas-2026!');
    await blocked.locator('button[type=submit]').click();
    await blocked.locator('#login-error').filter({hasText: 'Não foi possível manter sua sessão'}).waitFor();
    assert.equal(new URL(blocked.url()).pathname, '/');
    assert.equal(await blocked.locator('button[type=submit]').isEnabled(), true);
    await screenshot(blocked, 'sessao-bloqueada');
    await blockedContext.close();
    // Página de preview sintética: aviso para abrir fora do iframe.
    const embeddedContext = await browser.newContext();
    const embedded = await embeddedContext.newPage();
    await embedded.goto('http://127.0.0.1:5081');
    await embedded.setContent('<iframe title="Prévia da escola" src="http://127.0.0.1:5081" width="1200" height="900"></iframe>');
    await embedded.frameLocator('iframe').locator('#login-error').filter({hasText: 'Esta prévia pode bloquear sua sessão'}).waitFor();
    await embeddedContext.close();
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(out, 'resumo.json'), JSON.stringify({passed: true,
      scenarios: ['login HTML admin/professor/aluno nas duas escolas', 'cookies simultaneos no mesmo host',
        'perfis sem privilegio administrativo', 'sessao bloqueada', 'aviso em iframe'], captures, errors}, null, 2));
    console.log('Login em navegador isolado: perfis, cookies simultaneos, aviso em iframe e sessao bloqueada aprovados.');
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});

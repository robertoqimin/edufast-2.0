// Isolated browser context, synthetic manual accounts only; no personal browser profile.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.EDUFAST_VISUAL_URL || 'http://127.0.0.1:5050';
const out = path.resolve(__dirname, '../../.ci-results/restauracao-visual');
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  // Explicitly exercise the HTML representation; API clients may omit Accept.
  await page.setExtraHTTPHeaders({ Accept: 'text/html' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  async function capture(name, route, status = 200) {
    const response = await page.goto(base + route);
    assert.equal(response.status(), status, route);
    await page.locator('main').first().waitFor();
    for (const [suffix, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      await page.setViewportSize({ width, height });
      await page.screenshot({ path: path.join(out, `${name}-${suffix}.png`), fullPage: true });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `${name} ${suffix}: horizontal overflow`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  async function login(name) {
    const response = await page.request.post(base + '/login', { data: { email: name + '@teste.local', senha: 'Teste-local-2026!' } });
    assert.equal(response.status(), 200);
  }
  try {
    await capture('login', '/');
    await page.locator('#email').fill('superadmin@teste.local');
    await page.locator('#senha').fill('Teste-local-2026!');
    await page.locator('button[type=submit]').click();
    await page.waitForURL('**/super/usuarios');
    await capture('usuarios', '/super/usuarios');
    await page.locator('[data-open-create]').click();
    assert.equal(await page.locator('#create-dialog').isVisible(), true);
    await page.screenshot({ path: path.join(out, 'novo-usuario.png'), fullPage: true });
    await page.keyboard.press('Escape');
    await page.locator('[data-edit-user]').first().click();
    assert.equal(await page.locator('#permission-dialog').isVisible(), true);
    assert.equal(await page.locator('#permission-form [name=versao]').inputValue(), '0');
    await page.keyboard.press('Escape');
    await capture('aparencia', '/super/layout');
    await capture('regras', '/super/escola');
    const original = (await (await page.request.get(base + '/super/escola?formato=json')).json()).identidade;
    try {
      const form = page.locator('#school-identity');
      await form.locator('[name=modo]').selectOption('claro');
      for (const [name, value] of Object.entries({ fundo: '#f3f7f6', destaque: '#16745d', superficie: '#ffffff', texto: '#193c3c', muted: '#475569' })) {
        await form.locator(`[name=${name}]`).fill(value);
      }
      await Promise.all([page.waitForNavigation(), form.getByRole('button', { name: 'Salvar identidade', exact: true }).click()]);
      await capture('identidade-personalizada', '/super/escola');
      assert.equal(await page.locator('meta[name=school-theme]').getAttribute('content'), 'claro');
    } finally {
      const current = (await (await page.request.get(base + '/super/escola?formato=json')).json()).identidade;
      const csrf = await page.locator('meta[name=csrf-token]').getAttribute('content');
      const restored = await page.request.post(base + '/super/escola/identidade', { data: { ...original, versao: current.versao }, headers: { 'X-CSRF-Token': csrf } });
      assert.equal(restored.status(), 200);
    }
    await capture('aprovacoes', '/solicitacoes');
    await login('admin');
    await capture('admin', '/admin/dashboard');
    await capture('acesso-negado', '/super/usuarios', 403);
    await login('professor');
    await capture('professor', '/professor/dashboard');
    await capture('propostas-docentes', '/solicitacoes');
    await login('aluno');
    await capture('aluno', '/aluno/dashboard');
    assert.equal((await page.request.get(base + '/super/escola')).status(), 403);
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(out, 'resumo.json'), JSON.stringify({ passed: true, viewports: ['1440x1000', '390x844'], errors }, null, 2));
    console.log('Original design: login, four roles, superprofile and approvals verified in desktop/mobile.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });

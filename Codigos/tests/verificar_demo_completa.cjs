// C1 — verifica a demonstração completa pela interface (Edge), por perfil, em desktop e celular.
// Uso: PLAYWRIGHT_MODULE=<caminho do playwright> node Codigos/tests/verificar_demo_completa.cjs [saida]
const path = require('node:path');
const fs = require('node:fs');
const ROOT = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(ROOT, '.ci-results/demo-video/node_modules/playwright'));
const ESCOLA = 'http://localhost:5095';
const SUPREMO = 'http://127.0.0.1:5093';
const SENHA = 'Demo-EduFast-2026!';
const OUT = process.argv[2] || path.join(ROOT, '.ci-results/demo-completa/capturas');
const D = 'demo.edufast.test';

// [perfil, e-mail, senha, base, [[página, textos esperados]]]
const ROTEIRO = [
  ['supremo', 'dono@plataforma.local', 'Plataforma-teste-2026!', SUPREMO, [['/', ['Escola Teste 01']]]],
  ['super-admin', `diretoria@${D}`, SENHA, ESCOLA, [
    ['/super/usuarios', ['ana.ribeiro@', 'secretaria@']], ['/super/escola', ['Calendário 2026', 'Boletim 2026']],
    ['/calendario-escolar', ['2026']]]],
  ['secretaria', `secretaria@${D}`, SENHA, ESCOLA, [
    ['/admin/dashboard', ['Colégio Horizonte']], ['/admin/turmas', ['1º ano A']], ['/academico', ['Matemática', '1º bimestre']],
    ['/academico/alunos/1/boletim', ['Média ponderada']], ['/frequencia', ['1º ano A']], ['/solicitacoes', ['Solicitações']],
    ['/aprendizagem', ['Matemática para o ENEM']]]],
  ['professora', `ana.ribeiro@${D}`, SENHA, ESCOLA, [
    ['/professor/dashboard', ['Ana Ribeiro', 'Matemática']], ['/academico', ['Prova — 1º bimestre']], ['/frequencia', ['Matemática']],
    ['/estudos/disciplinas/1', ['Unidade 1']], ['/aprendizagem', ['Matemática para o ENEM']]]],
  ['aluno', `bruno.lima@${D}`, SENHA, ESCOLA, [
    ['/aluno/dashboard', ['Bruno Lima']], ['/boletim', ['Matemática', 'Língua Portuguesa', 'Biologia', 'Média ponderada']],
    ['/estudos', ['Matemática', 'Biologia']], ['/estudos/disciplinas/1', ['Boas-vindas à Matemática']],
    ['/aprendizagem', ['Matemática para o ENEM']], ['/frequencia', ['Frequência']]]],
];

(async () => {
  fs.mkdirSync(OUT, {recursive: true});
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const falhas = [];
  let paginas = 0;
  for (const [perfil, email, senha, base, paginasPerfil] of ROTEIRO) {
    for (const [vp, w, h] of [['desktop', 1440, 1000], ['celular', 390, 844]]) {
      const context = await browser.newContext({viewport: {width: w, height: h}});
      const page = await context.newPage();
      const erros = [];
      page.on('pageerror', (e) => erros.push(String(e)));
      const login = await context.request.post(base + '/login', {data: base === SUPREMO ? undefined : {email, senha},
        form: base === SUPREMO ? {email, senha} : undefined, headers: {Origin: base}});
      if (base === SUPREMO) {  // o painel central usa formulário com CSRF
        await page.goto(base + '/login');
        await page.fill('input[name=email]', email);
        await page.fill('input[name=senha], input[name=password]', senha);
        await Promise.all([page.waitForLoadState('load'), page.locator('form button').first().click()]);
      } else if (login.status() !== 200) {
        falhas.push(`${perfil}: login ${login.status()}`);
      }
      for (const [url, textos] of paginasPerfil) {
        const r = await page.goto(base + url);
        await page.waitForLoadState('networkidle').catch(() => {});
        const corpo = await page.locator('body').innerText();
        const faltam = textos.filter((t) => !corpo.includes(t));
        const rolagem = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
        if (!r || r.status() !== 200) falhas.push(`${perfil} ${url} ${vp}: HTTP ${r && r.status()}`);
        if (faltam.length) falhas.push(`${perfil} ${url} ${vp}: falta ${faltam.join(', ')}`);
        if (rolagem) falhas.push(`${perfil} ${url} ${vp}: rolagem horizontal`);
        await page.screenshot({path: path.join(OUT, `${perfil}${url.replace(/\W+/g, '_')}-${vp}.png`), fullPage: true});
        paginas += 1;
      }
      if (erros.length) falhas.push(`${perfil} ${vp}: erro JS ${erros[0]}`);
      await context.close();
    }
  }
  await browser.close();
  console.log(`${paginas} páginas verificadas; ${falhas.length} falha(s).`);
  falhas.forEach((f) => console.log('  FALHA ' + f));
  process.exitCode = falhas.length ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 2; });

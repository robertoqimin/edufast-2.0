// Capturas da apresentação do README: telas atuais da demo completa (escola 5095 e Supremo 5093),
// desktop 1440×900 e celular 390×844, somente dados fictícios.
// Uso: node infra/demo-completa.cjs reset && node api/tests/capturar_apresentacao_readme.cjs <pasta>
// Altera a demo: a professora envia notas do Simulado para aprovação (fica pendente para a captura
// da aprovação em lote). Rode "node infra/demo-completa.cjs reset" depois, se quiser a demo limpa.
const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const ROOT = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(ROOT, '.ci-results/demo-video/node_modules/playwright'));
const B = 'http://localhost:5095', SUPREMO = 'http://127.0.0.1:5093';
const S = 'Demo-EduFast-2026!', D = 'demo.edufast.test';
const OUT = process.argv[2];
if (!OUT) { console.error('Uso: node api/tests/capturar_apresentacao_readme.cjs <pasta>'); process.exit(2); }

const VIEW = {desktop: [1440, 900], celular: [390, 844]};
const feitas = [];
const falhas = [];

async function esperar(p, fn, arg, ms = 15000) {  // a CSP bloqueia waitForFunction
  const fim = Date.now() + ms;
  while (Date.now() < fim) { if (await p.evaluate(fn, arg).catch(() => false)) return true; await p.waitForTimeout(150); }
  return false;
}

async function capturar(p, nome, vp, descricao) {
  await p.waitForLoadState('networkidle').catch(() => {});
  await p.evaluate(() => document.fonts.ready).catch(() => {});
  await p.waitForTimeout(400);
  const rolagem = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  if (rolagem) falhas.push(`${nome}: rolagem horizontal`);
  const arquivo = `${nome}-${vp}.png`;
  await p.screenshot({path: path.join(OUT, arquivo)});
  const sha256 = crypto.createHash('sha256').update(fs.readFileSync(path.join(OUT, arquivo))).digest('hex');
  feitas.push({arquivo, tela: descricao, endereco: new URL(p.url()).pathname, viewport: VIEW[vp].join('x'), sha256});
  console.log(`ok ${arquivo}  ${new URL(p.url()).pathname}`);
}

async function contexto(browser, vp, conta) {
  const [width, height] = VIEW[vp];
  const ctx = await browser.newContext({viewport: {width, height}});
  if (conta) {
    const r = await ctx.request.post(B + '/login', {data: {email: `${conta}@${D}`, senha: S}, headers: {Origin: B}});
    if (r.status() !== 200) falhas.push(`login ${conta}: ${r.status()}`);
  }
  const p = await ctx.newPage();
  p.on('pageerror', (e) => falhas.push(`${conta || 'anônimo'} ${vp}: erro JS ${e}`));
  return [ctx, p];
}

async function leitorPdf(p) {
  await p.goto(B + '/estudos');
  await p.getByRole('link', {name: /Matemática/}).first().click();
  await p.getByRole('link', {name: 'Unidade 1 — Funções'}).click();
  await p.getByRole('link', {name: 'Slides — função afim na prática'}).click();
  if (!await esperar(p, () => document.querySelector('[data-leitor]')?.dataset.paginaAtual === '1', null, 20000)) falhas.push('leitor PDF não desenhou a página 1');
}

(async () => {
  fs.mkdirSync(OUT, {recursive: true});
  const browser = await chromium.launch({channel: 'msedge'});
  let ctx, p;

  // Login
  [ctx, p] = await contexto(browser, 'desktop');
  await p.goto(B + '/');
  await capturar(p, '01-login', 'desktop', 'Login da escola');
  await ctx.close();

  // Direção: Visão geral com o checklist "Primeiros passos"
  [ctx, p] = await contexto(browser, 'desktop', 'diretoria');
  await p.goto(B + '/admin/dashboard');
  await capturar(p, '02-direcao-visao-geral', 'desktop', 'Direção — Visão geral e Primeiros passos');
  await ctx.close();

  // Secretaria: tela única de Turmas, com a primeira turma aberta
  [ctx, p] = await contexto(browser, 'desktop', 'secretaria');
  await p.goto(B + '/admin/gestao-turmas');
  await p.locator('details.turma-cartao summary').first().click();
  await p.evaluate(() => window.scrollTo(0, document.querySelector('details.turma-cartao').getBoundingClientRect().top + scrollY - 140));
  await capturar(p, '03-secretaria-turmas', 'desktop', 'Secretaria — Turmas: matérias, professores e alunos');
  await ctx.close();

  // Professora: chamada e diário da avaliação (envia o Simulado para aprovação)
  for (const vp of ['desktop', 'celular']) {
    [ctx, p] = await contexto(browser, vp, 'ana.ribeiro');
    await p.goto(B + '/frequencia/turmas/1/chamada');
    await capturar(p, '04-professora-chamada', vp, 'Professora — chamada da turma');
    await ctx.close();
  }
  [ctx, p] = await contexto(browser, 'desktop', 'ana.ribeiro');
  await p.goto(B + '/academico');
  await p.getByRole('link', {name: /Simulado/}).first().click();
  const campos = p.locator('input[name^="valor_"]');
  const total = await campos.count();
  for (let i = 0; i < total; i++) await campos.nth(i).fill(['8.5', '7', '9', '6.5'][i % 4]);
  await p.locator('input[name^="valor_"]').first().blur();
  await p.evaluate(() => window.scrollTo(0, 0));
  await capturar(p, '05-professora-diario', 'desktop', 'Professora — diário: a turma inteira numa solicitação');
  await Promise.all([p.waitForURL(/\/solicitacoes/), p.getByRole('button', {name: 'Enviar notas para aprovação'}).click()]);
  await ctx.close();

  // Secretaria: Solicitações pendentes com o resumo do lote
  [ctx, p] = await contexto(browser, 'desktop', 'secretaria');
  await p.goto(B + '/solicitacoes');
  await p.evaluate(() => window.scrollTo(0, document.querySelector('.filtro-solicitacoes').getBoundingClientRect().top + scrollY - 24));
  if (!/Lançar notas da avaliação/.test(await p.locator('main').innerText())) falhas.push('Solicitações sem o lote do Simulado');
  await capturar(p, '06-secretaria-solicitacoes', 'desktop', 'Secretaria — Solicitações pendentes e aprovação em lote');
  await ctx.close();

  // Aluno: painel, leitor de PDF e boletim
  for (const vp of ['desktop', 'celular']) {
    [ctx, p] = await contexto(browser, vp, 'bruno.lima');
    await p.goto(B + '/aluno/dashboard');
    await capturar(p, '07-aluno-painel', vp, 'Aluno — painel');
    await leitorPdf(p);
    await capturar(p, '08-aluno-leitor-pdf', vp, 'Aluno — material em PDF no leitor da plataforma');
    if (vp === 'desktop') {
      await p.goto(B + '/boletim');
      await capturar(p, '09-aluno-boletim', vp, 'Aluno — boletim');
    }
    await ctx.close();
  }

  // Aluna: curso modular, aula com a videoaula enviada pela professora (arquivo cifrado, U2b)
  [ctx, p] = await contexto(browser, 'desktop', 'carla.souza');
  await p.goto(B + '/aprendizagem');
  await p.getByRole('button', {name: 'Continuar estudando'}).first().click();
  await p.getByRole('button', {name: /Leitura de gráficos e pontos/}).first().click();
  await p.waitForLoadState('load');
  if (await p.getByRole('button', {name: 'Abrir aula'}).count()) await p.getByRole('button', {name: 'Abrir aula'}).click();
  await p.waitForLoadState('load');
  const video = p.locator('.course-reading video').first();
  if (!await video.count()) falhas.push('aula sem a videoaula enviada');
  else {
    await video.evaluate((v) => { v.muted = true; v.currentTime = 4; });
    if (!await esperar(p, () => { const v = document.querySelector('.course-reading video'); return v && v.readyState >= 2 && !v.seeking; })) falhas.push('videoaula não carregou');
    await p.evaluate(() => window.scrollTo(0, document.querySelector('.course-reading video').getBoundingClientRect().top + scrollY - 160));
  }
  await capturar(p, '10-aluna-curso-video', 'desktop', 'Aluna — curso Matemática para o ENEM, videoaula enviada pela professora');
  await ctx.close();

  // Painel Supremo (formulário com CSRF)
  [ctx, p] = await contexto(browser, 'desktop');
  await p.goto(SUPREMO + '/login');
  await p.fill('input[name=email]', 'dono@plataforma.local');
  await p.fill('input[name=senha], input[name=password]', 'Plataforma-teste-2026!');
  await Promise.all([p.waitForLoadState('load'), p.locator('form button').first().click()]);
  await p.goto(SUPREMO + '/');
  await capturar(p, '11-supremo-escolas', 'desktop', 'Painel Supremo — escolas da plataforma');
  await ctx.close();

  await browser.close();
  fs.writeFileSync(path.join(OUT, 'manifesto.json'), JSON.stringify({
    data: new Date().toISOString().slice(0, 10),
    navegador: 'Microsoft Edge (Playwright, headless)',
    dados: 'Demo completa recriada (node infra/demo-completa.cjs reset): Colégio Horizonte e painel Supremo; somente dados fictícios',
    verificador: 'node api/tests/capturar_apresentacao_readme.cjs <pasta>',
    falhas,
    capturas: feitas,
  }, null, 2) + '\n');
  console.log(`${feitas.length} capturas; ${falhas.length} falha(s).`);
  falhas.forEach((f) => console.log('  FALHA ' + f));
  process.exitCode = falhas.length ? 1 : 0;
})().catch((e) => { console.error(e); process.exitCode = 2; });

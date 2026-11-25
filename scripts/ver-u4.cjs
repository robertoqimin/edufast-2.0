// U4 em câmera lenta no Edge — ensaio de aceite: uma escola NOVA (só com o acesso da direção) é
// configurada seguindo apenas o checklist "Primeiros passos". A cada passo o roteiro volta à Visão
// geral, clica no botão do próximo passo indicado e preenche a tela de destino; o progresso é conferido.
// Uso (a partir da raiz do projeto):
//   node scripts/ver-u4.cjs                 recria a escola de gravação vazia (porta 5070) e roda (~10 min)
//   node scripts/ver-u4.cjs 1.5             mais lento (0.3 a 4)
//   node scripts/ver-u4.cjs --passo         espera ENTER antes de cada tela
//   node scripts/ver-u4.cjs --capturas DIR  salva capturas (desktop e celular) em DIR
// Apaga e recria SOMENTE a escola de gravação (projeto edufast-gravacao). Dados fictícios.
const path = require('path');
const fs = require('fs');
const readline = require('readline');
const {spawnSync} = require('child_process');
const ROOT = path.resolve(__dirname, '..');
let playwright;
try { playwright = require('playwright'); } catch { playwright = require(path.join(ROOT, '.ci-results/demo-video/node_modules/playwright')); }

const B = 'http://localhost:5070';
const args = process.argv.slice(2);
const PASSO = args.includes('--passo');
const PREPARAR = !args.includes('--sem-preparar');
const CAPTURAS = args.includes('--capturas') ? path.resolve(args[args.indexOf('--capturas') + 1]) : null;
const RITMO = Math.min(4, Math.max(0.3, Number(args.find((a) => /^\d+(\.\d+)?$/.test(a)) || 1)));
const HEADLESS = process.env.DEMO_HEADLESS === '1';
const COMPOSE = ['compose', '--project-name', 'edufast-gravacao', '--env-file', '.ci-results/gravacao/.env',
  '-f', 'Codigos/docker-compose.yml', '-f', 'scripts/compose.manual.yml'];
const DIRECAO = {email: 'direcao@escolanova.test', senha: 'Direcao-Escola-2026!'};
const CONTAS = {
  secretaria: {nome: 'Secretaria Escolar', email: 'secretaria@escolanova.test', senha: 'Secretaria-2026!'},
  professora: {nome: 'Marina Costa', email: 'marina.costa@escolanova.test', senha: 'Professora-Marina-2026!', cpf: '52998224725'},
  alunos: [{nome: 'Lucas Prado', email: 'lucas.prado@escolanova.test', senha: 'Aluno-Lucas-2026!', matricula: '2026101'},
           {nome: 'Sofia Mendes', email: 'sofia.mendes@escolanova.test', senha: 'Aluna-Sofia-2026!', matricula: '2026102'}],
};
let page;
const log = [];
const inicio = Date.now();
const espera = (ms) => page.waitForTimeout(Math.round(ms * RITMO));
const tempo = () => `[${((Date.now() - inicio) / 60000).toFixed(1)} min]`;
const ok = (c, m) => { log.push((c ? 'OK   ' : 'FALHA') + ' ' + m); console.log((c ? 'OK    ' : 'FALHA ') + m); if (!c) process.exitCode = 1; };

function preparar() {
  console.log('Recriando a escola de gravação vazia (porta 5070)...');
  const env = path.join(ROOT, '.ci-results/gravacao/.env');
  if (fs.existsSync(env)) spawnSync('docker', [...COMPOSE, 'down', '-v'], {cwd: ROOT, stdio: 'ignore'});
  const r = spawnSync('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(ROOT, 'iniciar-educafast.ps1'),
    '-Ambiente', 'Gravacao', '-PrepararBancoNovo', '-SemNavegador'], {cwd: ROOT, encoding: 'utf8'});
  if (r.status !== 0 || !/Aplicacao pronta|pronta/i.test(r.stdout || '')) throw new Error('A escola de gravação não subiu: ' + (r.stderr || r.stdout || '').slice(-400));
  const cli = spawnSync('docker', [...COMPOSE, 'exec', '-T', 'app', 'flask', '--app', 'app:create_app()', 'create-admin', '--super-admin'],
    {cwd: ROOT, input: `${DIRECAO.email}\n${DIRECAO.senha}\n${DIRECAO.senha}\n`, encoding: 'utf8'});
  if (cli.status !== 0) throw new Error('create-admin falhou: ' + (cli.stderr || cli.stdout).slice(-300));
  console.log('Escola vazia pronta: só o acesso da direção existe.');
}

function enter(texto) {
  if (!PASSO) return Promise.resolve();
  const rl = readline.createInterface({input: process.stdin, output: process.stdout});
  return new Promise((r) => rl.question(`\n>> Próxima tela: ${texto}\n   Aperte ENTER para continuar... `, () => { rl.close(); r(); }));
}

async function legenda(texto, ms = 5000) {
  console.log(`${tempo()} ${texto}`);
  await page.evaluate((t) => {
    let el = document.getElementById('__demo_legenda');
    if (!el) {
      el = document.createElement('div');
      el.id = '__demo_legenda';
      Object.assign(el.style, {position: 'fixed', left: '50%', bottom: '24px', transform: 'translateX(-50%)', maxWidth: 'min(80vw, 900px)',
        background: 'rgba(8,20,32,.94)', color: '#ecf1f8', border: '2px solid #22d3ee', padding: '12px 22px',
        borderRadius: '14px', font: '600 19px system-ui, sans-serif', zIndex: 2147483647, pointerEvents: 'none',
        boxShadow: '0 8px 30px rgba(0,0,0,.5)', textAlign: 'center', lineHeight: '1.4'});
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, texto).catch(() => {});
  await espera(ms);
}

async function tela(titulo, subtitulo) {
  await enter(titulo);
  console.log(`\n${tempo()} == ${titulo}`);
  await page.evaluate(([t, s]) => {
    const el = document.createElement('div');
    el.id = '__demo_capa';
    const h = document.createElement('div'); h.textContent = t;
    Object.assign(h.style, {font: '800 40px system-ui', color: '#22d3ee', marginBottom: '14px'});
    const p = document.createElement('div'); p.textContent = s;
    Object.assign(p.style, {font: '500 21px system-ui', color: '#ecf1f8', maxWidth: '900px', lineHeight: '1.45'});
    el.append(h, p);
    Object.assign(el.style, {position: 'fixed', inset: '0', background: 'rgba(6,16,28,.96)', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', textAlign: 'center', zIndex: 2147483647, pointerEvents: 'none', padding: '24px'});
    document.body.appendChild(el);
  }, [titulo, subtitulo]).catch(() => {});
  await espera(5000);
  await page.evaluate(() => document.getElementById('__demo_capa')?.remove()).catch(() => {});
}

async function destacar(loc) {
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  await loc.evaluate((el) => { el.style.outline = '4px solid #facc15'; el.style.outlineOffset = '3px';
    setTimeout(() => { el.style.outline = ''; }, 2600); }).catch(() => {});
  await espera(1000);
}

async function clicar(loc, depois = 2000) {
  await destacar(loc);
  await Promise.all([page.waitForLoadState('load').catch(() => {}), loc.click()]);
  await page.waitForLoadState('networkidle').catch(() => {});
  await espera(depois);
}

async function capturar(nome) {
  if (!CAPTURAS) return;
  fs.mkdirSync(CAPTURAS, {recursive: true});
  await page.evaluate(() => document.getElementById('__demo_legenda')?.remove()).catch(() => {});
  await page.screenshot({path: path.join(CAPTURAS, nome + '.png'), fullPage: true});
}

// ---------- formulários (mesmos auxiliares do roteiro de gravação) ----------
async function abrirContexto(form) {
  const fechados = await form.evaluate((f) => { let n = 0, el = f; while (el) { if (el.tagName === 'DETAILS' && !el.open) n++; el = el.parentElement; } return n; });
  for (let i = 0; i < fechados; i++) {
    const summary = form.locator('xpath=ancestor::details[not(@open)][last()]/summary').first();
    if (await summary.count()) await clicar(summary, 700);
  }
  const dialogo = await form.evaluate((f) => { const d = f.closest('dialog'); return d && !d.open ? d.id : null; });
  if (dialogo) await clicar(page.locator('[data-open-create]').first(), 1000);
}
async function formulario(acao, nomes, filtro = {}) {
  const indice = await page.evaluate(({acao, nomes, filtro}) => [...document.forms].findIndex((f) =>
    (f.getAttribute('action') || '').includes(acao) && nomes.every((k) => f.elements[k]) &&
    Object.entries(filtro).every(([k, v]) => f.elements[k] && String(f.elements[k].value) === String(v))), {acao, nomes, filtro});
  if (indice < 0) throw new Error(`formulário ${acao} ${JSON.stringify(filtro)} não encontrado em ${page.url()}`);
  return page.locator('form').nth(indice);
}
async function preencher(form, campos) {
  const ordem = Object.entries(campos).sort(([a], [b]) => (a === 'tipo' ? -1 : b === 'tipo' ? 1 : 0));
  for (const [nome, valor] of ordem) {
    const alvo = form.locator(`[name="${nome}"]`);
    const info = await alvo.first().evaluate((el) => ({tag: el.tagName, tipo: el.type}));
    if (info.tipo === 'hidden') continue;
    if (info.tipo === 'radio') {
      const rotulo = form.locator(`label:has(input[name="${nome}"][value="${valor}"])`);
      await destacar(rotulo.first());
      await form.locator(`input[name="${nome}"][value="${valor}"]`).check({force: true});
      await espera(600);
      continue;
    }
    if (info.tipo === 'checkbox') {
      for (let i = 0; i < await alvo.count(); i++) {
        const c = alvo.nth(i);
        const marcar = valor.includes(await c.getAttribute('value'));
        if ((await c.isChecked()) !== marcar) await c.setChecked(marcar, {force: true});
      }
      continue;
    }
    await destacar(alvo.first());
    if (info.tag === 'SELECT') {
      const rotulo = await alvo.first().evaluate((el, t) => [...el.options].find((o) => o.value === t || o.textContent.includes(t))?.textContent, String(valor));
      if (!rotulo) throw new Error(`opção "${valor}" ausente em ${nome}`);
      await alvo.first().selectOption({label: rotulo});
    } else if (['date', 'number'].includes(info.tipo)) {
      await alvo.first().fill(String(valor));
    } else {
      await alvo.first().fill('');
      await alvo.first().pressSequentially(String(valor), {delay: Math.round(40 * RITMO)});
    }
    await espera(400);
  }
}
async function enviar(acao, campos, {filtro = {}, texto = null} = {}) {
  const form = await formulario(acao, Object.keys(campos), filtro);
  await abrirContexto(form);
  await preencher(form, campos);
  if (texto) await legenda(texto, 3500);
  const b = form.locator('button[type=submit], button:not([type])').last();
  await destacar(b);
  const resposta = page.waitForResponse((r) => r.request().method() === 'POST', {timeout: 30000});
  await b.click();
  const r = await resposta;
  await page.waitForLoadState('networkidle').catch(() => {});
  if (r.status() >= 400) throw new Error(`HTTP ${r.status()} em ${new URL(r.url()).pathname}`);
  await espera(1800);
}

async function entrar(conta, quem) {
  await page.goto(B + '/logout').catch(() => {});
  await page.goto(B + '/');
  await legenda(`Entrando como ${quem}`, 2500);
  await page.locator('#email').pressSequentially(conta.email, {delay: Math.round(40 * RITMO)});
  await page.locator('#senha').pressSequentially(conta.senha, {delay: Math.round(40 * RITMO)});
  await Promise.all([page.waitForURL((u) => u.pathname !== '/', {timeout: 20000}), page.click('button.login-submit')]);
  await page.waitForLoadState('networkidle').catch(() => {});
  await espera(2000);
}

// ---------- o checklist guia cada passo ----------
async function visaoGeral() {
  await clicar(page.getByRole('link', {name: 'Visão geral'}).first(), 1500);
  return Number(((await page.locator('.primeiros-passos-cabecalho p').first().innerText()).match(/(\d+) de 8/) || [])[1]);
}

async function seguir(esperado, feitosAntes) {
  const feitos = await visaoGeral();
  ok(feitos === feitosAntes, `checklist mostra ${feitosAntes} de 8 antes de "${esperado}" (tela: ${feitos})`);
  const proximo = page.locator('.passo-proximo');
  const titulo = (await proximo.locator('h3').innerText()).trim();
  ok(titulo === esperado, `próximo passo indicado: "${titulo}"`);
  await destacar(proximo);
  await legenda(`Próximo passo indicado pelo checklist: ${titulo}.`, 4000);
  const botao = proximo.locator('a.button');
  if (!(await botao.count())) return false;   // passo de outro perfil
  await clicar(botao, 1500);
  return true;
}

(async () => {
  if (PREPARAR) preparar();
  const browser = await playwright.chromium.launch({channel: 'msedge', headless: HEADLESS, slowMo: Math.round(60 * RITMO), args: ['--start-maximized']});
  const context = await browser.newContext({viewport: HEADLESS ? {width: 1440, height: 1000} : null});
  page = await context.newPage();
  await page.goto(B + '/');
  await tela('U4 — Primeiros passos', 'Uma escola nova, só com o acesso da direção. O checklist da Visão geral guia cada passo até a escola ficar pronta.');

  // Direção
  await tela('1. A direção entra pela primeira vez', 'A Visão geral mostra o checklist: 0 de 8 passos e o próximo passo destacado.');
  await entrar(DIRECAO, 'direção (superperfil)');
  ok(new URL(page.url()).pathname === '/admin/dashboard' && await page.locator('.passo-proximo').count() === 1,
     `direção entra direto na Visão geral com o checklist (${new URL(page.url()).pathname})`);
  await legenda('Primeira tela: o checklist de implantação, com o próximo passo destacado.', 6000);
  await capturar('01-direcao-escola-vazia-desktop');

  await seguir('Calendário escolar do ano', 0);
  await enviar('/super/escola/calendarios', {ano: '2026', nome: 'Calendário 2026', inicio: '2026-02-02', fim: '2026-12-11', meta_letivos: '200',
    dias_semana: ['0', '1', '2', '3', '4']}, {texto: 'Calendário 2026: início, fim, dias letivos e meta de 200 dias.'});

  await seguir('Regras do boletim', 1);
  const boletim = {nome: 'Boletim 2026 — bimestral', calendario_id: 'Calendário 2026', divisao: 'bimestres', media_referencia: '6', casas: '1', arredondamento: 'comercial'};
  [['2026-02-02', '2026-04-17'], ['2026-04-20', '2026-07-10'], ['2026-07-27', '2026-09-30'], ['2026-10-01', '2026-12-11']].forEach(([a, b], i) => {
    boletim[`periodo_${i + 1}_inicio`] = a; boletim[`periodo_${i + 1}_fim`] = b; });
  await enviar('/super/escola/politicas', boletim, {texto: 'Quatro bimestres, média 6, uma casa decimal.'});

  await seguir('Contas da equipe', 2);
  await enviar('/super/usuarios', {tipo: 'admin', email: CONTAS.secretaria.email, senha: CONTAS.secretaria.senha},
    {texto: 'Conta da secretaria.'});
  await enviar('/super/usuarios', {tipo: 'professor', nome: CONTAS.professora.nome, email: CONTAS.professora.email, senha: CONTAS.professora.senha, cpf: CONTAS.professora.cpf},
    {texto: 'Conta da professora Marina.'});
  for (const a of CONTAS.alunos) {
    await enviar('/super/usuarios', {tipo: 'aluno', nome: a.nome, email: a.email, senha: a.senha, matricula: a.matricula}, {texto: `Conta do aluno ${a.nome}.`});
  }
  const feitosDirecao = await visaoGeral();
  ok(feitosDirecao === 3, `direção concluiu 3 de 8 (tela: ${feitosDirecao})`);
  await destacar(page.locator('.passo-proximo'));
  await legenda('Agora o próximo passo é da secretaria: disciplinas, turma, professores e alunos.', 6000);

  // Secretaria
  await tela('2. A secretaria continua de onde a direção parou', 'Ela vê os 3 passos feitos e os passos da direção sem botão ("A cargo da direção").');
  await entrar(CONTAS.secretaria, 'secretaria');
  ok(await page.getByText('A cargo da direção').count() >= 1, 'secretaria vê passos da direção sem link ("A cargo da direção")');
  await capturar('02-secretaria-continua-desktop');

  await seguir('Disciplinas', 3);
  await enviar('disciplinas', {nome: 'Matemática', codigo: 'MAT1', carga_horaria: '120'}, {texto: 'Disciplina de Matemática.'});

  await seguir('Turmas do ano', 4);
  await enviar('', {acao: 'criar', nome: '1º ano A', codigo: '1A-2026', ano_letivo: '2026'}, {filtro: {acao: 'criar'}, texto: 'Turma 1º ano A de 2026.'});

  await seguir('Disciplinas e professores de cada turma', 5);
  await enviar('', {acao: 'atribuir', turma_id: '1º ano A', professor_id: CONTAS.professora.nome, disciplina_id: 'Matemática'},
    {filtro: {acao: 'atribuir'}, texto: 'A professora Marina dá Matemática no 1º ano A.'});

  await seguir('Alunos matriculados', 6);
  for (const a of CONTAS.alunos) {
    await enviar('', {turma_id: '1º ano A', aluno_id: a.nome}, {filtro: {acao: 'matricular'}, texto: `Matriculando ${a.nome}.`});
  }
  const ultimo = await seguir('Boletim aplicado às turmas', 7);
  ok(!ultimo, 'último passo é da direção: a secretaria não recebe botão');
  await legenda('Falta só a direção aplicar o boletim à turma.', 5000);

  // Direção de novo
  await tela('3. A direção fecha a implantação', 'Aplica as regras do boletim à turma: os quatro bimestres são criados.');
  await entrar(DIRECAO, 'direção (superperfil)');
  await seguir('Boletim aplicado às turmas', 7);
  await enviar('/aplicar', {turma_id: '1º ano A'}, {texto: 'Aplicando o boletim ao 1º ano A.'});
  await clicar(page.getByRole('link', {name: 'Visão geral'}).first(), 1500);
  const concluido = page.locator('details.primeiros-passos-concluido');
  ok(await concluido.count() === 1, 'checklist recolhido: "Implantação concluída"');
  ok(/8 de 8/.test(await concluido.locator('summary').innerText()), 'resumo mostra 8 de 8 passos');
  await destacar(concluido);
  await legenda('Escola configurada só seguindo o checklist. Ele fica recolhido, para consulta.', 6000);
  await capturar('03-implantacao-concluida-desktop');

  // Celular
  const ctx = await browser.newContext({viewport: {width: 390, height: 844}, deviceScaleFactor: 2});
  const anterior = page;
  page = await ctx.newPage();
  await page.goto(B + '/');
  await entrar(CONTAS.secretaria, 'secretaria (celular)');
  await page.locator('details.primeiros-passos-concluido summary').click();
  await espera(1500);
  ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'celular: checklist sem rolagem horizontal');
  await legenda('No celular, o checklist empilha cada passo.', 4500);
  await capturar('04-checklist-celular');
  await tela('Fim da U4', 'Escola nova configurada seguindo o checklist: calendário, boletim, equipe, disciplina, turma, professora, alunos e boletim aplicado.');
  await ctx.close();
  page = anterior;
  await browser.close();
  console.log('\n' + log.join('\n'));
})().catch((e) => { console.error(log.join('\n')); console.error(e); process.exitCode = 2; });

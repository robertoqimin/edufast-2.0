// Demonstração automática em câmera lenta para gravar a tela (>= 15 min).
// Percorre: Supremo cadastra a escola -> operador ativa o super admin -> super admin cria
// contas, calendário e boletim -> admin cria disciplina e turma -> professora publica
// materiais e curso -> secretaria aprova e libera -> aluno estuda. Digita campo a campo,
// destaca cada controle e mostra legendas. Somente dados fictícios.
// Uso (a partir da raiz): node scripts/demo_video.cjs [ritmo]   (ritmo 1 = padrão; 1.5 = mais lento)
const path = require('path');
const fs = require('fs');
const zlib = require('zlib');
const {spawnSync} = require('child_process');
const ROOT = path.resolve(__dirname, '..');
let playwright;
try { playwright = require('playwright'); } catch { playwright = require(path.join(ROOT, '.ci-results/demo-video/node_modules/playwright')); }

const ESCOLA = process.env.DEMO_ESCOLA || 'http://localhost:5070';
const SUPREMO = process.env.DEMO_SUPREMO || 'http://127.0.0.1:5093';
const RITMO = Number(process.argv[2] || process.env.DEMO_RITMO || 1);
const VIDEO = process.env.DEMO_VIDEO_URL || 'https://www.youtube.com/watch?v=kvGsIo1TmsM';
const OUT = path.join(ROOT, '.ci-results/demo-video');
const SUPER = {email: 'diretoria@colegiohorizonte.test', senha: 'Diretoria-2026!'};
const CONTAS = {
  admin: {nome: 'Secretaria Escolar', email: 'secretaria@colegiohorizonte.test', senha: 'Secretaria-2026!'},
  professor: {nome: 'Ana Ribeiro', email: 'ana.ribeiro@colegiohorizonte.test', senha: 'Professora-Ana-2026!', cpf: '12345678901'},
  aluno1: {nome: 'Bruno Lima', email: 'bruno.lima@colegiohorizonte.test', senha: 'Aluno-Bruno-2026!', matricula: '2026001'},
  aluno2: {nome: 'Carla Souza', email: 'carla.souza@colegiohorizonte.test', senha: 'Aluna-Carla-2026!', matricula: '2026002'},
};
const COMPOSE = ['compose', '--project-name', 'edufast-gravacao', '--env-file', '.ci-results/gravacao/.env',
  '-f', 'Codigos/docker-compose.yml', '-f', 'scripts/compose.manual.yml'];
let page;
const inicio = Date.now();
const espera = (ms) => page.waitForTimeout(Math.round(ms * RITMO));

// ---------- arquivos de exemplo ----------
function pdf(titulo, linhas) {
  const corpo = ['BT /F1 22 Tf 50 740 Td (' + titulo + ') Tj ET',
    ...linhas.map((l, i) => `BT /F1 13 Tf 50 ${700 - i * 22} Td (${l}) Tj ET`)].join('\n');
  const objs = ['<</Type/Catalog/Pages 2 0 R>>', '<</Type/Pages/Kids[3 0 R]/Count 1>>',
    '<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>',
    `<</Length ${corpo.length}>>stream\n${corpo}\nendstream`, '<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>'];
  let saida = '%PDF-1.4\n';
  const offsets = objs.map((o, i) => { const pos = saida.length; saida += `${i + 1} 0 obj${o}endobj\n`; return pos; });
  const xref = saida.length;
  saida += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n` + offsets.map((o) => String(o).padStart(10, '0') + ' 00000 n \n').join('');
  return Buffer.from(saida + `trailer<</Size ${objs.length + 1}/Root 1 0 R>>\nstartxref\n${xref}\n%%EOF\n`, 'latin1');
}
function png() {
  const w = 640, h = 360, px = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) {
    px[y * (w * 3 + 1)] = 0;
    for (let x = 0; x < w; x++) {
      let c = [16, 28, 43];
      if (x === 60 || y === 300) c = [164, 189, 206];
      const fy = 300 - Math.round((x - 60) * 0.42);
      if (x > 60 && Math.abs(y - fy) <= 2) c = [34, 211, 238];
      px.set(c, y * (w * 3 + 1) + 1 + x * 3);
    }
  }
  const crcTable = Array.from({length: 256}, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (b) => { let c = 0xffffffff; for (const x of b) c = crcTable[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (t, d) => { const l = Buffer.alloc(4); l.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t), d]);
    const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([l, td, c]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from('89504e470d0a1a0a', 'hex'), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(px)), chunk('IEND', Buffer.alloc(0))]);
}
function arquivos() {
  const dir = path.join(OUT, 'arquivos');
  fs.mkdirSync(dir, {recursive: true});
  const f = {apostila: path.join(dir, 'Apostila - Funcoes do 1o grau.pdf'), slides: path.join(dir, 'Slides - Aula 1.pdf'),
             grafico: path.join(dir, 'Grafico da funcao afim.png')};
  fs.writeFileSync(f.apostila, pdf('Apostila: Funcoes do 1o grau', ['1. O que e uma funcao', 'Uma funcao associa cada valor de x a um unico valor de y.',
    '2. Funcao afim: f(x) = ax + b', 'a e o coeficiente angular; b e o coeficiente linear.', '3. Exercicios',
    'a) Calcule f(2) para f(x) = 3x - 1.', 'b) Esboce o grafico de f(x) = 2x + 1.']));
  fs.writeFileSync(f.slides, pdf('Slides - Aula 1', ['Funcoes: conceito e exemplos', 'Dominio, imagem e grafico', 'Atividade em sala']));
  fs.writeFileSync(f.grafico, png());
  return f;
}

// ---------- apresentação ----------
async function legenda(texto, ms = 7000) {
  console.log(`[${((Date.now() - inicio) / 60000).toFixed(1)} min] ${texto}`);
  await page.evaluate((t) => {
    let el = document.getElementById('__demo_legenda');
    if (!el) {
      el = document.createElement('div');
      el.id = '__demo_legenda';
      Object.assign(el.style, {position: 'fixed', left: '50%', bottom: '24px', transform: 'translateX(-50%)', maxWidth: '80vw',
        background: 'rgba(8,20,32,.94)', color: '#ecf1f8', border: '2px solid #22d3ee', padding: '14px 24px',
        borderRadius: '14px', font: '600 20px system-ui, sans-serif', zIndex: 2147483647, pointerEvents: 'none',
        boxShadow: '0 8px 30px rgba(0,0,0,.5)', textAlign: 'center', lineHeight: '1.4'});
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, texto).catch(() => {});
  await espera(ms);
}
async function capa(titulo, subtitulo) {
  console.log(`[${((Date.now() - inicio) / 60000).toFixed(1)} min] == ${titulo}`);
  await page.evaluate(([t, s]) => {
    const el = document.createElement('div');
    el.id = '__demo_capa';
    el.innerHTML = `<div style="font:800 44px system-ui;color:#22d3ee;margin-bottom:16px">${t}</div><div style="font:500 22px system-ui;color:#ecf1f8;max-width:900px">${s}</div>`;
    Object.assign(el.style, {position: 'fixed', inset: '0', background: 'rgba(6,16,28,.97)', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', textAlign: 'center', zIndex: 2147483647, pointerEvents: 'none'});
    document.body.appendChild(el);
  }, [titulo, subtitulo]).catch(() => {});
  await espera(8000);
  await page.evaluate(() => document.getElementById('__demo_capa')?.remove()).catch(() => {});
}
async function destacar(loc) {
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  await loc.evaluate((el) => { el.style.outline = '3px solid #facc15'; el.style.outlineOffset = '3px';
    setTimeout(() => { el.style.outline = ''; }, 2500); }).catch(() => {});
  await espera(700);
}
async function percorrer() {
  // Rola a página devagar para mostrar o conteúdo e volta ao topo.
  const altura = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  for (let y = 0; y < altura; y += 260) { await page.mouse.wheel(0, 260); await espera(450); }
  await espera(1200);
  await page.evaluate(() => scrollTo({top: 0, behavior: 'smooth'}));
  await espera(1000);
}
async function ir(url, texto) {
  await page.goto(url);
  await page.waitForLoadState('networkidle').catch(() => {});
  if (texto) await legenda(texto, 5000);
}
async function clicar(loc, depois = 2500) {
  await destacar(loc);
  await Promise.all([page.waitForLoadState('load').catch(() => {}), loc.click()]);
  await page.waitForLoadState('networkidle').catch(() => {});
  await espera(depois);
}

// ---------- formulários (interação visível) ----------
async function abrirContexto(form) {
  // Abre <details> recolhidos e o diálogo que contém o formulário, como um usuário faria.
  const resumos = await form.evaluate((f) => {
    const lista = []; let el = f;
    while (el) { if (el.tagName === 'DETAILS' && !el.open) lista.unshift(el); el = el.parentElement; }
    return lista.length;
  });
  for (let i = 0; i < resumos; i++) {
    const summary = form.locator('xpath=ancestor::details[not(@open)][last()]/summary').first();
    if (await summary.count()) await clicar(summary, 900);
  }
  const dialogo = await form.evaluate((f) => { const d = f.closest('dialog'); return d && !d.open ? d.id : null; });
  if (dialogo) await clicar(page.locator(`[data-open-create]`).first(), 1200);
}
async function formulario(acao, nomes, filtro = {}) {
  const indice = await page.evaluate(({acao, nomes, filtro}) => [...document.forms].findIndex((f) =>
    (f.getAttribute('action') || '').includes(acao) && nomes.every((k) => f.elements[k]) &&
    Object.entries(filtro).every(([k, v]) => f.elements[k] && String(f.elements[k].value) === String(v))), {acao, nomes, filtro});
  if (indice < 0) throw new Error(`formulário ${acao} não encontrado em ${page.url()}`);
  return page.locator('form').nth(indice);
}
async function preencher(form, campos) {
  const ordem = Object.entries(campos).sort(([a], [b]) => (a === 'tipo' ? -1 : b === 'tipo' ? 1 : 0));
  for (const [nome, valor] of ordem) {
    const alvo = form.locator(`[name="${nome}"]`);
    const info = await alvo.first().evaluate((el) => ({tag: el.tagName, tipo: el.type, oculto: el.type === 'hidden'}));
    if (info.oculto) { await alvo.first().evaluate((el, v) => { el.value = v; }, String(valor)); continue; }
    if (info.tipo === 'radio') {
      const r = form.locator(`input[name="${nome}"][value="${valor}"]`);
      const rotulo = form.locator(`label:has(input[name="${nome}"][value="${valor}"])`);
      await destacar((await rotulo.count()) ? rotulo.first() : r);
      await r.check({force: true});
      await espera(900);
      continue;
    }
    if (info.tipo === 'checkbox') {
      const caixas = await alvo.count();
      for (let i = 0; i < caixas; i++) {
        const c = alvo.nth(i);
        const marcar = valor.includes(await c.getAttribute('value'));
        if ((await c.isChecked()) !== marcar) { await destacar(c); await c.setChecked(marcar, {force: true}); await espera(300); }
      }
      continue;
    }
    if (info.tipo === 'file') { await destacar(alvo.first()); await alvo.first().setInputFiles(valor); await espera(1500); continue; }
    await destacar(alvo.first());
    if (info.tag === 'SELECT') {
      const rotulo = await alvo.first().evaluate((el, t) => [...el.options].find((o) => o.value === t || o.textContent.includes(t))?.textContent, String(valor));
      if (!rotulo) throw new Error(`opção "${valor}" ausente em ${nome}`);
      await alvo.first().selectOption({label: rotulo});
      await espera(900);
    } else if (['date', 'number'].includes(info.tipo)) {
      await alvo.first().fill(String(valor));
      await espera(600);
    } else {
      await alvo.first().fill('');
      await alvo.first().pressSequentially(String(valor), {delay: Math.round(55 * RITMO)});
      await espera(400);
    }
  }
}
async function enviar(acao, campos, {filtro = {}, botao = null, texto = null} = {}) {
  const form = await formulario(acao, Object.keys(campos), filtro);
  await abrirContexto(form);
  await preencher(form, campos);
  if (texto) await legenda(texto, 4000);
  const invalidos = await form.evaluate((f) => [...f.elements].filter((e) => !e.disabled && e.willValidate && !e.checkValidity())
    .map((e) => `${e.name}: ${e.validationMessage}`));
  if (invalidos.length) throw new Error('o navegador recusou o formulário: ' + invalidos.join('; '));
  const b = botao ? form.getByRole('button', {name: botao}) : form.locator('button[type=submit], button:not([type])').last();
  await destacar(b.first());
  const resposta = page.waitForResponse((r) => r.request().method() === 'POST', {timeout: 30000});
  await b.first().click();
  const r = await resposta;
  await page.waitForLoadState('networkidle').catch(() => {});
  if (r.status() >= 400) throw new Error(`HTTP ${r.status()} em ${new URL(r.url()).pathname}`);
  await espera(2500);
}
async function entrar(base, email, senha, quem) {
  await page.goto(base + '/logout').catch(() => {});
  await page.goto(base + '/');
  await legenda(`Entrando como ${quem}`, 3500);
  await destacar(page.locator('#email'));
  await page.locator('#email').pressSequentially(email, {delay: Math.round(55 * RITMO)});
  await destacar(page.locator('#senha'));
  await page.locator('#senha').pressSequentially(senha, {delay: Math.round(70 * RITMO)});
  await destacar(page.locator('button.login-submit'));
  await Promise.all([page.waitForURL((u) => u.pathname !== '/', {timeout: 20000}), page.click('button.login-submit')]);
  await page.waitForLoadState('networkidle').catch(() => {});
  await espera(3000);
}

// ---------- roteiro ----------
(async () => {
  const f = arquivos();
  const browser = await playwright.chromium.launch({channel: 'msedge', headless: process.env.DEMO_HEADLESS === '1', slowMo: Math.round(60 * RITMO),
    args: ['--start-maximized']});
  const context = await browser.newContext({viewport: null, acceptDownloads: true});
  page = await context.newPage();
  await page.goto(SUPREMO + '/login');
  await capa('EduFast', 'Gestão escolar completa: da plataforma à sala de aula. Uma escola fictícia criada do zero, passo a passo.');

  // 1. Supremo
  await capa('1. Painel Supremo', 'O dono da plataforma acompanha todas as escolas, as pessoas e o financeiro.');
  await page.locator('input[name=email]').pressSequentially('dono@plataforma.local', {delay: Math.round(55 * RITMO)});
  await page.locator('input[name=senha], input[name=password]').first().pressSequentially('Plataforma-teste-2026!', {delay: Math.round(60 * RITMO)});
  await clicar(page.locator('form button').first(), 3000);
  await legenda('Visão geral: escolas cadastradas, pessoas e resultado financeiro de cada uma.', 8000);
  await percorrer();
  await enviar('/escolas', {name: 'Colégio Horizonte', slug: 'colegio-horizonte-' + (Date.now() % 1000), domain: 'horizonte.example.test', monthly: '890,00'},
    {texto: 'Cadastrando a nova escola: nome, identificador, domínio e mensalidade contratada.'});
  await legenda('Escola cadastrada no diretório e no financeiro. A ativação da instalação é feita pelo operador.', 9000);

  // 2. Operador
  await capa('2. Ativação pelo operador', 'No servidor, o operador ativa a escola e cria o primeiro acesso: o super admin da escola.\n.\\iniciar-educafast.ps1 -Ambiente Gravacao -Acao CriarAdmin -SuperAdmin');
  const cli = spawnSync('docker', [...COMPOSE, 'exec', '-T', 'app', 'flask', '--app', 'app:create_app()', 'create-admin', '--super-admin'],
    {cwd: ROOT, input: `${SUPER.email}\n${SUPER.senha}\n${SUPER.senha}\n`, encoding: 'utf8'});
  if (cli.status !== 0) throw new Error('create-admin falhou: ' + (cli.stderr || cli.stdout).slice(-300));

  // 3. Super admin
  await capa('3. Super admin da escola', 'A direção configura a própria escola: pessoas, calendário e regras do boletim.');
  await entrar(ESCOLA, SUPER.email, SUPER.senha, 'super admin da escola (diretoria)');
  await ir(ESCOLA + '/super/usuarios', 'Usuários e permissões: cada pessoa recebe o acesso certo.');
  await enviar('/super/usuarios', {tipo: 'professor', nome: CONTAS.professor.nome, email: CONTAS.professor.email, senha: CONTAS.professor.senha, cpf: CONTAS.professor.cpf},
    {texto: 'Criando a conta da professora Ana Ribeiro.'});
  await enviar('/super/usuarios', {tipo: 'admin', nome: CONTAS.admin.nome, email: CONTAS.admin.email, senha: CONTAS.admin.senha},
    {texto: 'Criando a conta da secretaria (administração).'});
  for (const c of [CONTAS.aluno1, CONTAS.aluno2]) {
    await enviar('/super/usuarios', {tipo: 'aluno', nome: c.nome, email: c.email, senha: c.senha, matricula: c.matricula},
      {texto: `Criando a conta do aluno ${c.nome}.`});
  }
  await legenda('Professora, secretaria e alunos cadastrados.', 6000);
  await percorrer();
  await ir(ESCOLA + '/super/escola', 'Regras e identidade da escola: calendário letivo e regras do boletim.');
  await enviar('/super/escola/calendarios', {ano: '2026', nome: 'Calendário 2026', inicio: '2026-02-02', fim: '2026-12-11', meta_letivos: '200',
    dias_semana: ['0', '1', '2', '3', '4']}, {texto: 'Calendário 2026: início, fim, dias da semana letivos e meta de 200 dias.'});
  await enviar('/eventos', {titulo: 'Recesso de julho', inicio: '2026-07-13', fim: '2026-07-24'}, {texto: 'Adicionando o recesso escolar de julho.'});
  const boletim = {nome: 'Boletim 2026 — bimestral', calendario_id: 'Calendário 2026', divisao: 'bimestres', media_referencia: '6', casas: '1', arredondamento: 'comercial'};
  [['2026-02-02', '2026-04-17'], ['2026-04-20', '2026-07-10'], ['2026-07-27', '2026-09-30'], ['2026-10-01', '2026-12-11']].forEach(([a, b], i) => {
    boletim[`periodo_${i + 1}_inicio`] = a; boletim[`periodo_${i + 1}_fim`] = b; });
  await enviar('/super/escola/politicas', boletim, {texto: 'Regras do boletim: quatro bimestres, média 6, uma casa decimal e arredondamento comercial.'});
  await legenda('Calendário e regras do boletim prontos. A regra será aplicada à turma assim que ela existir.', 7000);
  await percorrer();

  // 4. Admin
  await capa('4. Secretaria (admin)', 'A secretaria organiza disciplinas e turmas e coloca professores e alunos.');
  await entrar(ESCOLA, CONTAS.admin.email, CONTAS.admin.senha, 'secretaria');
  await ir(ESCOLA + '/admin/disciplinas', 'Disciplinas da escola.');
  await enviar('disciplinas', {nome: 'Matemática', codigo: 'MAT1', carga_horaria: '120'}, {texto: 'Cadastrando a disciplina de Matemática.'});
  await enviar('disciplinas', {professor_id: CONTAS.professor.nome, disciplina_id: 'Matemática'}, {texto: 'A professora Ana fica responsável por Matemática.'});
  // U5: uma tela de turma ("Turmas"): criar, matéria com professor e matrículas.
  await ir(ESCOLA + '/admin/gestao-turmas', 'Turmas da escola: tudo num só lugar.');
  await enviar('', {acao: 'criar', nome: '1º ano A', codigo: '1A-2026', ano_letivo: '2026', turno: 'Matutino'},
    {filtro: {acao: 'criar'}, texto: 'Criando a turma 1º ano A, turno matutino.'});
  await enviar('', {acao: 'atribuir', turma_id: '1º ano A', disciplina_id: 'Matemática', professor_id: CONTAS.professor.nome},
    {filtro: {acao: 'atribuir'}, texto: 'A professora Ana dá Matemática no 1º ano A.'});
  for (const c of [CONTAS.aluno1, CONTAS.aluno2]) {
    await enviar('', {turma_id: '1º ano A', aluno_id: c.nome}, {filtro: {acao: 'matricular'}, texto: `Matriculando ${c.nome} no 1º ano A.`});
  }
  await legenda('Turma pronta: professora e alunos vinculados.', 6000);
  await percorrer();

  await capa('Boletim da turma', 'De volta à direção: a regra do boletim é aplicada à turma e os quatro bimestres são criados.');
  await entrar(ESCOLA, SUPER.email, SUPER.senha, 'super admin da escola');
  await ir(ESCOLA + '/super/escola');
  await enviar('/aplicar', {turma_id: '1º ano A'}, {texto: 'Aplicando as regras do boletim ao 1º ano A.'});

  // 5. Professora
  await capa('5. Professora', 'A professora prepara avisos, vídeos, slides, apostilas e um curso para a turma.');
  await entrar(ESCOLA, CONTAS.professor.email, CONTAS.professor.senha, 'professora Ana Ribeiro');
  await ir(ESCOLA + '/estudos', 'Espaço da disciplina: o lugar dos avisos e materiais de cada turma.');
  await clicar(page.locator('a[href*="/estudos/disciplinas/"]').first(), 3000);
  const par = page.url().match(/disciplinas\/(\d+)/)[1];
  const materiais = [
    [{tipo: 'aviso', titulo: 'Boas-vindas à Matemática', texto: 'Olá, turma! Neste bimestre vamos estudar funções. Leiam a apostila antes da primeira aula.'}, 'Um aviso de boas-vindas para a turma.'],
    [{tipo: 'link', titulo: 'Vídeo: o que é uma função', link: VIDEO, texto: 'Assistam antes da aula.'}, 'Um vídeo do YouTube para assistir antes da aula.'],
    [{tipo: 'link', titulo: 'Slides online da aula 1', link: 'https://docs.google.com/presentation/', texto: 'Slides para acompanhar a aula.'}, 'Os slides da aula, por link.'],
    [{tipo: 'arquivo', titulo: 'Apostila de funções', texto: 'Apostila em PDF para estudo.', arquivo: f.apostila}, 'A apostila em PDF.'],
    [{tipo: 'arquivo', titulo: 'Slides da aula 1 (PDF)', texto: 'Versão em PDF dos slides.', arquivo: f.slides}, 'Os slides também em PDF.'],
    [{tipo: 'arquivo', titulo: 'Gráfico da função afim', texto: 'Imagem para estudar o gráfico.', arquivo: f.grafico}, 'E uma imagem do gráfico.'],
  ];
  for (const [campos, texto] of materiais) {
    await ir(ESCOLA + `/estudos/disciplinas/${par}`);
    await clicar(page.getByRole('link', {name: 'Preparar conteúdo'}).first(), 1500);
    await enviar('', campos, {texto});
    await legenda('Rascunho salvo. Agora a professora envia para publicação: a secretaria revisa antes de a turma ver.', 5000);
    await enviar('/publicar', {}, {});
  }
  await ir(ESCOLA + `/estudos/disciplinas/${par}`, 'Materiais enviados. Eles aguardam a aprovação da secretaria.');
  await percorrer();

  await ir(ESCOLA + '/aprendizagem', 'Meus cursos: cursos organizados em módulos, capítulos e aulas.');
  await enviar('cursos', {titulo: 'Funções do 1º grau', descricao: 'Curso de revisão com vídeo, textos e materiais de apoio.', disciplina_id: 'Matemática'},
    {texto: 'Criando o curso Funções do 1º grau.'});
  const curso = page.url().match(/cursos\/(\d+)/)[1];
  await enviar('/estrutura', {titulo: 'Módulo 1 — Conceitos'}, {filtro: {acao: 'adicionar', tipo: 'capitulo'}, texto: 'Adicionando o primeiro módulo.'});
  await enviar('/estrutura', {titulo: 'Capítulo 1 — Introdução'}, {filtro: {acao: 'adicionar', tipo: 'tema'}, texto: 'E o primeiro capítulo.'});
  await clicar(page.getByRole('link', {name: 'Nova aula de texto'}).first(), 1500);
  await enviar('/estrutura', {titulo: 'Aula 1 — O que é uma função', corpo: 'Uma função associa cada valor de x a um único valor de y.\n\nExemplo: em f(x) = 2x + 1, quando x = 3, temos f(3) = 7.'},
    {texto: 'Uma aula de texto, escrita diretamente na plataforma.'});
  await enviar('/recursos', {tipo: 'arquivo', titulo: 'Slides da aula 1', arquivo: f.slides}, {filtro: {tipo: 'arquivo'}, texto: 'Anexando os slides em PDF à aula.'});
  await enviar('/recursos', {tipo: 'link', titulo: 'Exercícios online', link: 'https://www.khanacademy.org/math'}, {filtro: {tipo: 'link'}, texto: 'E um link de exercícios.'});
  await ir(ESCOLA + `/aprendizagem/cursos/${curso}`);
  await clicar(page.getByRole('link', {name: 'Nova aula de vídeo'}).first(), 1500);
  await enviar('/estrutura', {titulo: 'Aula 2 — Vídeo explicativo', video: VIDEO}, {texto: 'Uma aula em vídeo, a partir de um link do YouTube.'});
  await ir(ESCOLA + `/aprendizagem/cursos/${curso}`, 'Curso montado: um módulo, um capítulo, uma aula de texto e uma de vídeo.');
  await percorrer();
  await enviar('/solicitar-publicacao', {}, {texto: 'A professora pede a publicação do curso.'});

  // 6. Secretaria aprova e libera
  await capa('6. Revisão da secretaria', 'Nada chega ao aluno sem revisão: a secretaria aprova os materiais e o curso e libera o curso para a turma.');
  await entrar(ESCOLA, CONTAS.admin.email, CONTAS.admin.senha, 'secretaria');
  await ir(ESCOLA + '/solicitacoes', 'Solicitações e aprovações: tudo o que a professora enviou.');
  await percorrer();
  for (let i = 0; i < 12; i++) {
    const botao = page.getByRole('button', {name: 'Aprovar e aplicar'}).first();
    if (!(await botao.count())) break;
    if (i === 0) await legenda('Aprovando cada envio.', 3000);
    await clicar(botao, 1800);
  }
  await ir(ESCOLA + `/aprendizagem/cursos/${curso}`, 'Curso publicado. Agora a secretaria o libera para o 1º ano A.');
  await enviar('/ofertas', {turma_disciplina_id: '1º ano A', ativa: 'true'}, {texto: 'Liberando o curso para a turma.'});

  // 7. Aluno
  await capa('7. Aluno', 'O aluno encontra tudo organizado: avisos, materiais e o curso com seu progresso.');
  await entrar(ESCOLA, CONTAS.aluno1.email, CONTAS.aluno1.senha, 'aluno Bruno Lima');
  await ir(ESCOLA + '/estudos', 'Minhas disciplinas.');
  await clicar(page.locator('a[href*="/estudos/disciplinas/"]').first(), 3000);
  await legenda('Avisos da disciplina.', 5000);
  await clicar(page.getByRole('link', {name: 'Materiais de estudo'}).or(page.getByRole('button', {name: 'Materiais de estudo'})).first(), 2000);
  await legenda('Materiais de estudo: vídeo, slides, apostila e imagem.', 6000);
  await percorrer();
  await clicar(page.locator('a', {hasText: 'Apostila de funções'}).first(), 2500);
  await legenda('Abrindo a apostila: o arquivo é baixado com segurança.', 4000);
  const link = page.locator('a[href*="/arquivo"]').first();
  await destacar(link);
  const [download] = await Promise.all([page.waitForEvent('download', {timeout: 20000}), link.click()]);
  await download.saveAs(path.join(OUT, 'baixado-' + download.suggestedFilename()));
  await espera(3000);
  await ir(ESCOLA + '/aprendizagem', 'Meus cursos.');
  await clicar(page.getByRole('button', {name: 'Continuar estudando'}).first(), 3000);
  await legenda('A aula de texto, com os slides e o link de exercícios anexados.', 7000);
  await percorrer();
  await clicar(page.getByRole('button', {name: /Aula 2/}).first(), 3000);
  await legenda('A aula em vídeo: o YouTube só é carregado quando o aluno clica, por privacidade.', 8000);
  const concluir = page.getByRole('button', {name: /Marcar como concluída/});
  if (await concluir.count()) await clicar(concluir.first(), 3000);
  await legenda('Aula concluída: o progresso fica registrado para o aluno e para a escola.', 7000);
  await capa('EduFast', 'Da plataforma à sala de aula: escola criada, configurada, organizada e com conteúdo publicado e estudado.');
  const minutos = ((Date.now() - inicio) / 60000).toFixed(1);
  fs.writeFileSync(path.join(OUT, 'ultima-execucao.txt'), `duracao_min=${minutos}\nritmo=${RITMO}\n`);
  console.log(`Demonstração concluída em ${minutos} minutos (ritmo ${RITMO}).`);
  await espera(4000);
  await browser.close();
})().catch((e) => { console.error('Demonstração interrompida:', e.message); process.exitCode = 1; });

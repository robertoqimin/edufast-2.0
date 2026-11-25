// U3 em câmera lenta no Edge: a professora lança a avaliação inteira num envio (1 solicitação) e a
// secretaria vê o resumo e aprova várias solicitações de uma vez; depois, uma correção rejeitada.
// Legendas explicam cada tela; o controle usado fica destacado em amarelo.
// Uso (a partir da raiz do projeto):
//   node scripts/ver-u3.cjs              ritmo padrão (~8 min), recria a demo antes
//   node scripts/ver-u3.cjs 1.5          mais lento (qualquer número de 0.3 a 4)
//   node scripts/ver-u3.cjs --passo      espera ENTER no terminal antes de cada tela
//   node scripts/ver-u3.cjs --sem-reset  usa a demo como está (o "Simulado" precisa estar sem notas)
// Somente a demo completa (http://localhost:5095, dados fictícios) é usada e, sem --sem-reset, recriada.
const path = require('path');
const readline = require('readline');
const {spawnSync} = require('child_process');
const ROOT = path.resolve(__dirname, '..');
let playwright;
try { playwright = require('playwright'); } catch { playwright = require(path.join(ROOT, '.ci-results/demo-video/node_modules/playwright')); }

const B = 'http://localhost:5095';
const SENHA = 'Demo-EduFast-2026!';
const D = 'demo.edufast.test';
const args = process.argv.slice(2);
const PASSO = args.includes('--passo');
const RESET = !args.includes('--sem-reset');
const RITMO = Math.min(4, Math.max(0.3, Number(args.find((a) => /^\d+(\.\d+)?$/.test(a)) || 1)));
const HEADLESS = process.env.DEMO_HEADLESS === '1';
const NOTAS = ['8.5', '7', '9', '6.5', '10', '7.5', '8', '5.5', '9.5', '7', '8'];   // a última aluna fica pendente
let page;
const inicio = Date.now();
const espera = (ms) => page.waitForTimeout(Math.round(ms * RITMO));
const tempo = () => `[${((Date.now() - inicio) / 60000).toFixed(1)} min]`;

function enter(texto) {
  if (!PASSO) return Promise.resolve();
  const rl = readline.createInterface({input: process.stdin, output: process.stdout});
  return new Promise((ok) => rl.question(`\n>> Próxima tela: ${texto}\n   Aperte ENTER para continuar... `, () => { rl.close(); ok(); }));
}

async function legenda(texto, ms = 6000) {
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
    const h = document.createElement('div');
    h.textContent = t;
    Object.assign(h.style, {font: '800 40px system-ui', color: '#22d3ee', marginBottom: '14px'});
    const p = document.createElement('div');
    p.textContent = s;
    Object.assign(p.style, {font: '500 21px system-ui', color: '#ecf1f8', maxWidth: '900px', lineHeight: '1.45'});
    el.append(h, p);
    Object.assign(el.style, {position: 'fixed', inset: '0', background: 'rgba(6,16,28,.96)', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', textAlign: 'center', zIndex: 2147483647, pointerEvents: 'none', padding: '24px'});
    document.body.appendChild(el);
  }, [titulo, subtitulo]).catch(() => {});
  await espera(5500);
  await page.evaluate(() => document.getElementById('__demo_capa')?.remove()).catch(() => {});
}

async function destacar(loc) {
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  await loc.evaluate((el) => { el.style.outline = '4px solid #facc15'; el.style.outlineOffset = '3px';
    setTimeout(() => { el.style.outline = ''; }, 2600); }).catch(() => {});
  await espera(1200);
}

async function clicar(loc, depois = 2500) {
  await destacar(loc);
  await Promise.all([page.waitForLoadState('load').catch(() => {}), loc.click()]);
  await page.waitForLoadState('networkidle').catch(() => {});
  await espera(depois);
}

async function entrar(email, quem) {
  await page.goto(B + '/logout').catch(() => {});
  await page.goto(B + '/');
  await legenda(`Entrando como ${quem}`, 3000);
  await destacar(page.locator('#email'));
  await page.locator('#email').pressSequentially(email, {delay: Math.round(55 * RITMO)});
  await destacar(page.locator('#senha'));
  await page.locator('#senha').pressSequentially(SENHA, {delay: Math.round(60 * RITMO)});
  await destacar(page.locator('button.login-submit'));
  await Promise.all([page.waitForURL((u) => u.pathname !== '/', {timeout: 20000}), page.click('button.login-submit')]);
  await page.waitForLoadState('networkidle').catch(() => {});
  await espera(2500);
}

async function abrirSimulado() {
  await clicar(page.getByRole('link', {name: 'Diário e avaliações'}).first(), 1500);
  await clicar(page.getByRole('link', {name: /Simulado/}).first(), 1500);
}

async function digitar(loc, texto) {
  await destacar(loc);
  await loc.fill('');
  await loc.pressSequentially(texto, {delay: Math.round(90 * RITMO)});
  await espera(350);
}

async function aprovacaoEmLote() {
  await tela('4. A secretaria recebe UM pedido por avaliação', 'Em vez de uma aprovação por nota, ela vê o resumo da avaliação inteira e decide de uma vez.');
  await entrar(`secretaria@${D}`, 'secretaria');
  await clicar(page.getByRole('link', {name: 'Solicitações e aprovações'}).first(), 1500);
  await destacar(page.locator('#lote-form'));
  await legenda('No topo: quantas solicitações aguardam decisão e as ações em lote.', 6000);
  const lote = page.locator('article', {hasText: 'Lançar notas da avaliação'}).first();
  await destacar(lote.locator('dl'));
  await legenda('Avaliação, turma, disciplina e quantas notas vieram (novas e alteradas).', 6500);
  await destacar(lote.locator('table'));
  await legenda('Para cada aluno: nota atual, nota enviada, observação e situação.', 7000);
  const linhas = lote.locator('tbody tr');
  for (let i = 0; i < Math.min(4, await linhas.count()); i++) await destacar(linhas.nth(i));
  await legenda('A última aluna não aparece: nota em branco é pendência, não entra no pedido.', 6000);
  await destacar(page.locator('article', {hasText: 'Publicar aviso ou material de estudo'}).filter({hasText: 'pendente'}).first());
  await legenda('Também há um aviso da professora aguardando: dá para decidir os dois juntos.', 6000);

  await tela('5. Aprovar selecionadas', 'Cada solicitação é conferida e aplicada separadamente; se alguma falhar, as outras seguem e o motivo aparece.');
  await page.evaluate(() => scrollTo({top: 0, behavior: 'smooth'}));
  await espera(1200);
  await destacar(page.locator('[data-marcar-todas]'));
  await page.locator('[data-marcar-todas]').check();
  await legenda('"Marcar todas" seleciona as solicitações pendentes.', 4500);
  const caixas = page.locator('input[name=ids][form=lote-form]');
  for (let i = 0; i < await caixas.count(); i++) await destacar(caixas.nth(i));
  await clicar(page.getByRole('button', {name: 'Aprovar selecionadas'}), 1500);
  await destacar(page.locator('.notice').first());
  await legenda('Confirmação: as solicitações foram aprovadas de uma vez.', 6000);
}

async function correcaoRejeitada() {
  await tela('7. Correção de uma nota', 'A professora corrige uma nota e envia de novo: só a nota alterada entra no pedido.');
  await entrar(`ana.ribeiro@${D}`, 'professora Ana Ribeiro (Matemática)');
  await abrirSimulado();
  const segunda = page.locator('input[name^="valor_"]').nth(1);
  await digitar(segunda, '7.5');
  await legenda('Carla Souza: de 7 para 7,5. As outras notas ficam como estão.', 5000);
  await clicar(page.getByRole('button', {name: 'Enviar notas para aprovação'}), 2500);

  await tela('8. A secretaria vê o que mudou', 'O resumo marca a nota como "Alterada", com a nota atual ao lado da nova.');
  await entrar(`secretaria@${D}`, 'secretaria');
  await clicar(page.getByRole('link', {name: 'Solicitações e aprovações'}).first(), 1500);
  const pedido = page.locator('article', {hasText: 'Lançar notas da avaliação'}).filter({hasText: 'pendente'}).first();
  await destacar(pedido.locator('table'));
  await legenda('Nota atual 7,00 → enviada 7,5 · situação "Alterada".', 6500);
  await destacar(pedido.locator('input[name=justificativa]'));
  await pedido.locator('input[name=justificativa]').pressSequentially('Confira a nota da Carla com a prova corrigida.', {delay: Math.round(40 * RITMO)});
  await clicar(pedido.getByRole('button', {name: 'Rejeitar'}), 2000);
  await legenda('Rejeitada com justificativa: nada muda no diário.', 5000);

  await tela('9. A professora pode enviar de novo', 'Depois da decisão, o diário volta a aceitar um envio; a nota aprovada continua valendo.');
  await entrar(`ana.ribeiro@${D}`, 'professora Ana Ribeiro (Matemática)');
  await abrirSimulado();
  await destacar(page.locator('input[name^="valor_"]').nth(1));
  await legenda('Carla continua com 7: a correção rejeitada não foi aplicada.', 5500);
  await destacar(page.getByRole('button', {name: 'Enviar notas para aprovação'}));
  await legenda('O formulário está liberado para um novo envio.', 4500);
}

async function celular(browser) {
  const ctx = await browser.newContext({viewport: {width: 390, height: 844}, deviceScaleFactor: 2});
  const anterior = page;
  page = await ctx.newPage();
  await page.goto(B + '/');
  await tela('10. No celular', 'O diário com a turma inteira também funciona numa tela de 390 × 844.');
  await entrar(`ana.ribeiro@${D}`, 'professora Ana Ribeiro (celular)');
  await page.goto(B + '/academico');
  await clicar(page.getByRole('link', {name: /Simulado/}).first(), 1500);
  await destacar(page.locator('.diario-tabela'));
  await legenda('A tabela rola dentro do quadro; cada campo diz de qual aluno é a nota.', 6000);
  await page.locator('.course-scroll').first().evaluate((el) => el.scrollBy({left: 300, behavior: 'smooth'})).catch(() => {});
  await espera(2500);
  await tela('Fim da U3', 'Avaliação inteira em 1 solicitação; a secretaria vê o resumo e aprova várias de uma vez.');
  await ctx.close();
  page = anterior;
}

(async () => {
  if (RESET) {
    console.log('Recriando a demo completa (http://localhost:5095) para o "Simulado" começar sem notas...');
    const r = spawnSync(process.execPath, [path.join(ROOT, 'infra/demo-completa.cjs'), 'reset', '--sem-supremo'], {cwd: ROOT, stdio: 'inherit'});
    if (r.status !== 0) throw new Error('Não foi possível recriar a demo. Abra o Docker Desktop e tente de novo.');
  }
  const browser = await playwright.chromium.launch({channel: 'msedge', headless: HEADLESS, slowMo: Math.round(80 * RITMO),
    args: ['--start-maximized']});
  const context = await browser.newContext({viewport: HEADLESS ? {width: 1440, height: 1000} : null});
  page = await context.newPage();
  await page.goto(B + '/');
  await tela('U3 — Avaliação inteira numa solicitação', 'Antes: uma solicitação por nota (30 alunos = 30 aprovações). Agora: um envio por avaliação e aprovação em lote.');

  await tela('1. O diário da avaliação', 'A professora abre o Simulado do 2º bimestre: a turma inteira numa tabela, com um campo de nota por aluno.');
  await entrar(`ana.ribeiro@${D}`, 'professora Ana Ribeiro (Matemática)');
  await abrirSimulado();
  await destacar(page.locator('.diario-tabela'));
  await legenda('12 alunos, um único formulário e um único botão de envio.', 6000);

  await tela('2. Lançando as notas', 'Ela digita as notas em sequência; a última aluna fica em branco (pendência, não zero).');
  const campos = page.locator('input[name^="valor_"]');
  for (let i = 0; i < NOTAS.length; i++) await digitar(campos.nth(i), NOTAS[i]);
  await digitar(page.locator('input[name^="observacao_"]').first(), 'Ótima evolução');
  await legenda('Observação opcional por aluno. Natália (última) fica sem nota por enquanto.', 5500);
  await clicar(page.getByRole('button', {name: 'Enviar notas para aprovação'}), 1500);
  await destacar(page.locator('.notice').first());
  await legenda('Confirmação: UMA solicitação enviada para a secretaria.', 6000);

  await tela('3. O que a professora vê enquanto espera', 'O diário mostra o envio pendente, aluno por aluno, e bloqueia um segundo envio até a decisão.');
  await abrirSimulado();
  await destacar(page.locator('.notice').first());
  await legenda('Data do envio e quantas notas aguardam aprovação.', 6000);
  await destacar(page.locator('.diario-tabela tbody tr').first());
  await legenda('"Aguardando aprovação: 8,5" — e Natália aparece como "Pendente".', 6000);
  await page.goto(B + '/estudos/disciplinas/1/novo');
  await legenda('Ela também prepara um aviso para a turma (outra solicitação).', 3500);
  await digitar(page.locator('input[name=titulo]'), 'Aviso: revisão para o simulado');
  await digitar(page.locator('textarea[name=texto]'), 'Revisão na quinta-feira, às 10h.');
  await Promise.all([page.waitForURL(/\/estudos\/conteudos\/\d+$/), page.getByRole('button', {name: 'Salvar rascunho'}).click()]);
  await clicar(page.getByRole('button', {name: 'Enviar para publicação'}), 2000);

  await aprovacaoEmLote();

  await tela('6. Notas aplicadas', 'De volta ao diário: as 11 notas entraram juntas, numa única transação.');
  await entrar(`ana.ribeiro@${D}`, 'professora Ana Ribeiro (Matemática)');
  await abrirSimulado();
  await destacar(page.locator('.diario-tabela'));
  await legenda('Notas gravadas; a última aluna continua pendente e pode ser lançada depois.', 6500);

  await correcaoRejeitada();
  await celular(browser);
  console.log(`\n${tempo()} Fim. O navegador fecha em 10 segundos.`);
  await page.waitForTimeout(10000);
  await browser.close();
})().catch((e) => { console.error(e); process.exitCode = 1; });

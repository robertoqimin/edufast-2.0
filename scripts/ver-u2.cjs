// U2 em câmera lenta no Edge: o aluno estuda PDF (slides), imagem, vídeo e recurso de curso
// sem baixar nada. Legendas explicam cada tela; o controle usado fica destacado em amarelo.
// Uso (a partir da raiz do projeto):
//   node scripts/ver-u2.cjs              ritmo padrão (~8 min), recria a demo antes
//   node scripts/ver-u2.cjs 1.5          mais lento (qualquer número de 0.3 a 4)
//   node scripts/ver-u2.cjs --passo      espera ENTER no terminal antes de cada tela
//   node scripts/ver-u2.cjs --sem-reset  usa a demo como está (contagem de vistos pode não começar em 0)
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

async function rolar(seletor, total = 600, passo = 120) {
  for (let y = 0; y < total; y += passo) {
    await page.evaluate(([s, d]) => (s ? document.querySelector(s) : document.scrollingElement)?.scrollBy({top: d, behavior: 'smooth'}), [seletor, passo]);
    await espera(380);
  }
}

async function esperarLeitor() {
  for (let i = 0; i < 150; i++) {
    const ok = await page.evaluate(() => [...document.querySelectorAll('[data-leitor]')]
      .every((h) => h.closest('details:not([open])') || h.dataset.estado)).catch(() => false);
    if (ok) return;
    await page.waitForTimeout(100);
  }
}

async function paginaAtual() {
  return page.evaluate(() => document.querySelector('[data-leitor]')?.dataset.paginaAtual);
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

async function abrirAbaMatematica() {
  await clicar(page.getByRole('link', {name: 'Espaço da disciplina'}).first(), 1500);
  await clicar(page.getByRole('link', {name: /Matemática/}).first(), 1500);
  await clicar(page.getByRole('link', {name: 'Unidade 1 — Funções'}), 1500);
}

async function jornadaAluno() {
  await tela('1. A lista de materiais', 'O aluno vê o tipo de cada material (PDF, Imagem, Link externo), o que é novo e quanto já estudou.');
  await abrirAbaMatematica();
  await destacar(page.locator('main progress'));
  await legenda('Progresso da aba: quantos materiais já foram vistos. Tudo começa como "Novo".', 6500);
  await destacar(page.locator('.leitor-selo').first());
  await legenda('Cada material mostra o tipo e o selo "Novo" ou "✓ Visto".', 5500);

  await tela('2. Slides em PDF dentro da plataforma', 'Leitor próprio (PDF.js no servidor da escola): nada é baixado e nenhum site externo é usado.');
  await clicar(page.getByRole('link', {name: 'Slides — função afim na prática'}), 1000);
  await esperarLeitor();
  await legenda('O PDF abre aqui mesmo, como um slide: a página inteira à vista.', 6500);
  await destacar(page.locator('.leitor-visto'));
  await legenda('Ao abrir, o material é marcado como visto automaticamente.', 5000);
  await destacar(page.locator('.leitor-barra'));
  await legenda('Barra do leitor: página anterior e próxima, zoom, página inteira e tela cheia.', 6000);
  for (let n = 2; n <= 4; n++) {
    await destacar(page.getByRole('button', {name: 'Próxima página'}));
    await page.getByRole('button', {name: 'Próxima página'}).click();
    await espera(1500);
    await legenda(`Página ${await paginaAtual()} de 4`, 3500);
  }
  await legenda('Na última página, "Próxima" fica desativado.', 4000);
  await destacar(page.locator('.leitor-folha'));
  await page.locator('.leitor-folha').focus();
  await legenda('Também dá para usar o teclado: seta para a esquerda volta a página.', 3500);
  for (let i = 0; i < 2; i++) { await page.keyboard.press('ArrowLeft'); await espera(1800); }
  await legenda(`Voltou para a página ${await paginaAtual()} pelo teclado.`, 4000);
  for (let i = 0; i < 2; i++) {
    await destacar(page.getByRole('button', {name: 'Aumentar zoom'}));
    await page.getByRole('button', {name: 'Aumentar zoom'}).click();
    await espera(1500);
  }
  await legenda('Zoom para ler os detalhes; a página rola dentro do leitor.', 4500);
  await rolar('.leitor-folha', 360, 120);
  await destacar(page.getByRole('button', {name: 'Ver a página inteira'}));
  await page.getByRole('button', {name: 'Ver a página inteira'}).click();
  await legenda('"Página inteira" volta ao tamanho original.', 4000);
  if (!HEADLESS) {
    await destacar(page.getByRole('button', {name: 'Abrir o material em tela cheia'}));
    await page.getByRole('button', {name: 'Abrir o material em tela cheia'}).click();
    await espera(1500);
    await legenda('Tela cheia, como numa apresentação (setas continuam funcionando).', 1);
    await page.locator('.leitor-folha').focus().catch(() => {});
    for (let i = 0; i < 3; i++) { await page.keyboard.press('ArrowRight'); await espera(1600); }
    await page.evaluate(() => document.fullscreenElement && document.exitFullscreen()).catch(() => {});
    await espera(1500);
  }
  await destacar(page.getByRole('link', {name: 'Baixar uma cópia'}));
  await legenda('Baixar continua possível, mas agora é opcional (botão secundário).', 5500);
  await destacar(page.locator('.leitor-navegacao'));
  await legenda('Navegação entre materiais: anterior, posição ("2 de 4") e próximo.', 5500);

  await tela('3. Imagem ampliável', 'Próximo material da lista: um gráfico em PNG, mostrado na página.');
  await clicar(page.getByRole('link', {name: /Próximo material/}), 1000);
  await esperarLeitor();
  await legenda('A imagem aparece direto na página.', 5000);
  await destacar(page.getByRole('button', {name: 'Ampliar'}));
  await page.getByRole('button', {name: 'Ampliar'}).click();
  await legenda('"Ampliar" mostra a imagem no tamanho real, com rolagem dentro do quadro.', 5000);
  await page.locator('.leitor-folha').evaluate((el) => el.scrollTo({left: el.scrollWidth, behavior: 'smooth'})).catch(() => {});
  await espera(2000);
  await page.getByRole('button', {name: 'Reduzir'}).click();
  await legenda('"Reduzir" volta a caber na tela.', 3500);

  await tela('4. Apostila em PDF', 'Mais um "Próximo material": a apostila, também lida aqui.');
  await clicar(page.getByRole('link', {name: /Próximo material/}), 1000);
  await esperarLeitor();
  await legenda('Apostila de uma página: os botões de página ficam desativados.', 5000);
  await destacar(page.locator('.leitor-navegacao'));
  await legenda('Último material da lista: só aparece "Material anterior".', 5000);

  await tela('5. Link externo', 'Links de outros sites (que não são vídeo do YouTube) continuam abrindo em nova aba.');
  await page.goto(B + '/estudos');
  await abrirAbaMatematica();
  await clicar(page.getByRole('link', {name: 'Exercícios online'}), 1000);
  await destacar(page.getByRole('link', {name: 'Abrir material de estudo'}));
  await legenda('O aviso explica que o material é de outro site e sugere pedir o PDF ao professor.', 6500);

  await tela('6. A lista depois do estudo', 'O progresso e os selos mostram o que já foi visto.');
  await clicar(page.getByRole('link', {name: /← Matemática/}), 1500);
  await destacar(page.locator('main progress'));
  await legenda(`Agora: ${(await page.locator('main').innerText()).match(/\d+ de \d+ vistos/)?.[0] || ''}.`, 5500);
  await destacar(page.locator('.leitor-selo').first());
  await legenda('Os materiais abertos estão com "✓ Visto".', 5000);

  await tela('7. Vídeo do YouTube embutido', 'O aluno entra no material e o vídeo já está na página, pronto para assistir (modo sem cookies do YouTube).');
  await page.goto(B + '/estudos');
  await clicar(page.getByRole('link', {name: /Biologia/}).first(), 1200);
  await clicar(page.getByRole('link', {name: 'Citologia'}), 1200);
  await clicar(page.getByRole('link', {name: 'Vídeo de exemplo do player'}), 1000);
  await destacar(page.locator('.leitor-video'));
  await legenda('O player já aparece embutido, sem botão extra para carregar.', 5000);
  await page.frameLocator('.course-player iframe').locator('.ytp-large-play-button').click({timeout: 8000}).catch(() => {});
  await legenda('O vídeo toca dentro da plataforma.', 12000);

  await tela('8. Vídeo enviado pela professora', 'A professora subiu um arquivo de vídeo para o sistema: ele fica cifrado no servidor e toca aqui, sem baixar.');
  await page.goto(B + '/estudos');
  await abrirAbaMatematica();
  await clicar(page.getByRole('link', {name: 'Videoaula — função afim'}), 1000);
  await tocarVideo('Player da própria plataforma: o vídeo chega por partes, só o trecho assistido.');
  await page.evaluate(() => { const v = document.querySelector('.leitor-video-arquivo video'); v.currentTime = 12; });
  await legenda('Avançar no vídeo também funciona: o servidor decifra só o pedaço pedido.', 6000);
  await page.evaluate(() => document.querySelector('.leitor-video-arquivo video').pause());

  await tela('9. Aula em vídeo no curso', 'Nos cursos, a aula de vídeo também abre com o player pronto.');
  await page.goto(B + '/aprendizagem');
  await clicar(page.getByRole('button', {name: 'Continuar estudando'}).first(), 1500);
  const aulaVideo = page.locator('.course-index button').filter({hasText: 'Videoaula de exemplo'}).first();
  if (await aulaVideo.count()) {
    await clicar(aulaVideo, 1500);
    if (await page.getByRole('button', {name: 'Abrir aula'}).count()) await clicar(page.getByRole('button', {name: 'Abrir aula'}), 1500);
    await destacar(page.locator('.leitor-video').first());
    await legenda('Aula de vídeo: o aluno entra e o vídeo já está lá para assistir.', 9000);
  }
  await tela('10. Material de aula nos cursos', 'Nesta aula a professora enviou um vídeo (fica no topo) e um gráfico em "Para praticar".');
  await page.goto(B + '/aprendizagem');
  await clicar(page.getByRole('button', {name: 'Continuar estudando'}).first(), 1500);
  await clicar(page.getByRole('button', {name: /Leitura de gráficos e pontos/}).first(), 1500);
  if (await page.getByRole('button', {name: 'Abrir aula'}).count()) await clicar(page.getByRole('button', {name: 'Abrir aula'}), 1500);
  await esperarLeitor();
  await tocarVideo('O vídeo enviado pela professora abre no topo da aula.');
  await destacar(page.locator('.leitor-recurso summary').first());
  await legenda('"Para praticar": o gráfico da aula aparece aqui, sem baixar.', 6000);
  await destacar(page.locator('.leitor-recurso .leitor').first());
  await espera(2500);
  await destacar(page.getByRole('link', {name: /Baixar uma cópia/}).first());
  await legenda('Baixar continua como opção.', 4000);
}

async function tocarVideo(texto) {
  const video = page.locator('.leitor-video-arquivo video').first();
  await destacar(video);
  await page.evaluate(() => { const v = document.querySelector('.leitor-video-arquivo video'); v.muted = true; v.play(); });
  await legenda(texto, 8000);
}

async function jornadaProfessora() {
  await tela('11. A professora vê o mesmo leitor', 'Quem publica confere o material como o aluno vai ver; para docentes não há marcação de visto.');
  await entrar(`ana.ribeiro@${D}`, 'professora Ana Ribeiro (Matemática)');
  await page.goto(B + '/estudos/conteudos/4');
  await esperarLeitor();
  await legenda('Mesmo leitor, sem o aviso de visto, porque não é aluno.', 6000);

  await tela('12. A professora envia um vídeo', 'Novo tipo "Vídeo": MP4 ou WebM de até 300 MB, enviado em partes com barra de progresso.');
  await page.goto(B + '/estudos/disciplinas/1/novo');
  await destacar(page.locator('#conteudo-tipo'));
  await page.selectOption('#conteudo-tipo', 'video');
  await legenda('Tipo de conteúdo: "Vídeo (arquivo MP4 ou WebM)".', 4500);
  await destacar(page.locator('input[name=titulo]'));
  await page.locator('input[name=titulo]').pressSequentially('Videoaula — revisão para a prova', {delay: Math.round(45 * RITMO)});
  await destacar(page.locator('[data-video-arquivo]'));
  await page.setInputFiles('[data-video-arquivo]', path.join(ROOT, 'api/demo/aula_funcao_afim.webm'));
  await legenda('Escolhe o arquivo de vídeo no computador.', 4000);
  await destacar(page.getByRole('button', {name: 'Salvar rascunho'}));
  await Promise.all([page.waitForURL(/\/estudos\/conteudos\/\d+$/, {timeout: 60000}), page.getByRole('button', {name: 'Salvar rascunho'}).click()]);
  await legenda('O vídeo subiu em partes e virou um rascunho: só chega aos alunos depois da aprovação da secretaria.', 7000);
  await tocarVideo('A professora confere o vídeo antes de enviar para publicação.');
}

async function jornadaCelular(browser) {
  const ctx = await browser.newContext({viewport: {width: 390, height: 844}, deviceScaleFactor: 2});
  const anterior = page;
  page = await ctx.newPage();
  await page.goto(B + '/');
  await tela('13. No celular', 'Mesma jornada numa tela de 390 × 844: a barra do leitor quebra em duas linhas e nada sai da tela.');
  await entrar(`carla.souza@${D}`, 'aluna Carla Souza (celular)');
  await page.goto(B + '/estudos/conteudos/4');
  await esperarLeitor();
  await legenda('Slides no celular, ocupando a largura.', 5000);
  await destacar(page.getByRole('button', {name: 'Próxima página'}));
  await page.getByRole('button', {name: 'Próxima página'}).click();
  await legenda('Próxima página.', 3500);
  await rolar(null, 700, 140);
  await legenda('Abaixo do leitor: baixar (opcional) e navegação entre materiais.', 5000);
  await clicar(page.getByRole('link', {name: /Próximo material/}), 1000);
  await esperarLeitor();
  await legenda('A imagem também cabe na tela do celular.', 5000);
  await page.goto(B + '/estudos');
  await page.getByRole('link', {name: /Matemática/}).first().click();
  await page.getByRole('link', {name: 'Unidade 1 — Funções'}).click();
  await clicar(page.getByRole('link', {name: 'Videoaula — função afim'}), 1000);
  await tocarVideo('O vídeo enviado também toca no celular.');
  await tela('Fim da U2', 'Estudar sem baixar: PDF, slides, imagens, vídeos do YouTube e vídeos enviados pela professora, dentro da plataforma.');
  await ctx.close();
  page = anterior;
}

(async () => {
  if (RESET) {
    console.log('Recriando a demo completa (http://localhost:5095) para começar com 0 materiais vistos...');
    const r = spawnSync(process.execPath, [path.join(ROOT, 'infra/demo-completa.cjs'), 'reset', '--sem-supremo'], {cwd: ROOT, stdio: 'inherit'});
    if (r.status !== 0) throw new Error('Não foi possível recriar a demo. Abra o Docker Desktop e tente de novo.');
  }
  const browser = await playwright.chromium.launch({channel: 'msedge', headless: HEADLESS, slowMo: Math.round(80 * RITMO),
    args: ['--start-maximized']});
  const context = await browser.newContext({viewport: HEADLESS ? {width: 1440, height: 1000} : null});
  page = await context.newPage();
  await page.goto(B + '/');
  await tela('U2 — Estudar sem baixar', 'PDF, slides, imagens e vídeos abertos dentro do EduFast, no Espaço da disciplina e nos cursos.');
  await entrar(`bruno.lima@${D}`, 'aluno Bruno Lima');
  await jornadaAluno();
  await jornadaProfessora();
  await jornadaCelular(browser);
  console.log(`\n${tempo()} Fim. O navegador fecha em 10 segundos.`);
  await page.waitForTimeout(10000);
  await browser.close();
})().catch((e) => { console.error(e); process.exitCode = 1; });

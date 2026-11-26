// U2 (plano de UX, O7): jornada do aluno no Edge — estudar PDF (slides), imagem, vídeo e recurso de
// curso sem baixar; anterior/próximo; visto; sem erros de console; desktop e celular.
// Uso: node api/tests/verificar_leitor_u2.cjs <pasta-das-capturas>   (VER=1 abre o navegador)
// Requer a demo completa recém-criada (node infra/demo-completa.cjs reset). Marca materiais como vistos.
const path = require('node:path');
const fs = require('node:fs');
const ROOT = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(ROOT, '.ci-results/demo-video/node_modules/playwright'));
const B = 'http://localhost:5095', S = 'Demo-EduFast-2026!', D = 'demo.edufast.test';
const OUT = process.argv[2] || path.join(ROOT, '.ci-results/ux/u2-leitor');
const HEADLESS = process.env.VER !== '1';
fs.mkdirSync(OUT, {recursive: true});
const log = [];
async function esperar(p, fn, arg, ms = 15000) {
  const fim = Date.now() + ms;
  while (Date.now() < fim) { if (await p.evaluate(fn, arg)) return true; await p.waitForTimeout(100); }
  throw new Error('tempo esgotado esperando: ' + fn);
}
const ok = (cond, msg) => { log.push((cond ? 'OK   ' : 'FALHA') + ' ' + msg); if (!cond) process.exitCode = 1; };

(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: HEADLESS, slowMo: HEADLESS ? 0 : 250});
  for (const [vp, w, h] of [['desktop', 1440, 1000], ['celular', 390, 844]]) {
    const ctx = await browser.newContext({viewport: {width: w, height: h}, acceptDownloads: true});
    const p = await ctx.newPage();
    const erros = [];
    p.on('console', (m) => { if (m.type() === 'error') erros.push(m.text() + ' @ ' + (m.location().url || '')); });
    p.on('pageerror', (e) => erros.push(String(e)));
    p.on('response', (r) => { if (r.status() >= 400) erros.push(r.status() + ' ' + r.url()); });
    let downloads = 0;
    p.on('download', () => downloads++);
    await ctx.clearCookies();
    await ctx.request.post(B + '/login', {data: {email: `bruno.lima@${D}`, senha: S}, headers: {Origin: B}});
    await p.goto(B + '/estudos');
    await p.getByRole('link', {name: /Matemática/}).first().click();
    await p.getByRole('link', {name: 'Unidade 1 — Funções'}).click();
    const antes = (await p.locator('main').innerText()).match(/(\d+) de (\d+) vistos/);
    ok(antes, `${vp}: lista mostra progresso (${antes && antes[0]})`);
    await p.screenshot({path: path.join(OUT, `lista-antes-${vp}.png`), fullPage: true});

    // PDF de slides: abre no leitor, navega por páginas, sem download.
    await p.getByRole('link', {name: 'Slides — função afim na prática'}).click();
    const leitor = p.locator('[data-leitor="pdf"]');
    await leitor.locator('[data-estado="pronto"], .leitor-barra').first().waitFor({timeout: 20000}).catch(() => {});
    await esperar(p, () => document.querySelector('[data-leitor]')?.dataset.paginaAtual === '1', null, 20000);
    ok(await leitor.getAttribute('data-paginas') === '4', `${vp}: PDF de slides com 4 páginas no leitor`);
    ok(await p.getByText('Página 1 de 4').isVisible(), `${vp}: indicador "Página 1 de 4"`);
    ok(await p.getByText(/Marcado como visto|Você já estudou/).isVisible(), `${vp}: aviso de visto`);
    const pixels = await p.evaluate(() => { const c = document.querySelector('.leitor canvas'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let escuros = 0; for (let i = 0; i < d.length; i += 16) if (d[i] < 128) escuros++; return {w: c.width, escuros}; });
    ok(pixels.w > 100 && pixels.escuros > 50, `${vp}: página desenhada no canvas (${pixels.w}px, ${pixels.escuros} amostras de texto)`);
    const texto = await p.locator('.leitor .textLayer').innerText();
    ok(/Funcao afim/.test(texto), `${vp}: camada de texto acessível ("${texto.slice(0, 30).replace(/\s+/g, ' ')}")`);
    await p.screenshot({path: path.join(OUT, `pdf-pagina-1-${vp}.png`), fullPage: true});
    await p.getByRole('button', {name: 'Próxima página'}).click();
    await esperar(p, () => document.querySelector('[data-leitor]').dataset.paginaAtual === '2');
    ok(await p.getByText('Página 2 de 4').isVisible(), `${vp}: botão próxima página`);
    await p.locator('.leitor-folha').focus();
    await p.keyboard.press('ArrowRight');
    await esperar(p, () => document.querySelector('[data-leitor]').dataset.paginaAtual === '3');
    ok(true, `${vp}: seta do teclado avança para a página 3`);
    const larguraAntes = await p.locator('.leitor canvas').evaluate((c) => c.clientWidth);
    await p.getByRole('button', {name: 'Aumentar zoom'}).click();
    await esperar(p, (l) => document.querySelector('.leitor canvas').clientWidth > l, larguraAntes);
    ok(true, `${vp}: zoom aumenta a página`);
    const rolagem = await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
    ok(rolagem, `${vp}: sem rolagem horizontal da página com zoom`);
    await p.screenshot({path: path.join(OUT, `pdf-pagina-3-zoom-${vp}.png`)});

    // Próximo material na lista (ordem: mais recente primeiro): imagem.
    await p.getByRole('link', {name: /Próximo material/}).click();
    const img = p.locator('.leitor img.leitor-imagem');
    await img.waitFor({timeout: 10000});
    await esperar(p, () => { const i = document.querySelector('.leitor img'); return i && i.complete && i.naturalWidth > 0; });
    ok(true, `${vp}: imagem aparece na página (próximo material)`);
    await p.getByRole('button', {name: 'Ampliar'}).click();
    ok(await p.locator('.leitor.leitor-ampliado').count() === 1, `${vp}: imagem ampliável`);
    await p.screenshot({path: path.join(OUT, `imagem-${vp}.png`), fullPage: true});

    await p.goBack(); await p.goBack();
    await p.goto(p.url());
    ok(downloads === 0, `${vp}: nenhum download durante o estudo`);

    // Vídeo na Biologia.
    await p.goto(B + '/estudos');
    await p.getByRole('link', {name: /Biologia/}).first().click();
    await p.getByRole('link', {name: 'Citologia'}).click();
    await p.getByRole('link', {name: 'Vídeo de exemplo do player'}).click();
    ok(await p.locator('.leitor-video iframe').count() === 1, `${vp}: vídeo já embutido ao abrir, sem clique extra`);
    const src = await p.locator('.course-player iframe').getAttribute('src');
    ok(src === 'https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ', `${vp}: player embutido sem cookies (${src})`);
    await p.waitForTimeout(2500);
    await p.screenshot({path: path.join(OUT, `video-${vp}.png`), fullPage: true});

    // Lista atualizada.
    await p.goto(B + '/estudos');
    await p.getByRole('link', {name: /Matemática/}).first().click();
    await p.getByRole('link', {name: 'Unidade 1 — Funções'}).click();
    const depois = await p.locator('main').innerText();
    ok(/✓ Visto/.test(depois), `${vp}: selo "✓ Visto" na lista (${(depois.match(/\d+ de \d+ vistos/) || [''])[0]})`);
    await p.screenshot({path: path.join(OUT, `lista-depois-${vp}.png`), fullPage: true});

    const relevantes = erros.filter((e) => !/youtube|ytimg|googlevideo|doubleclick|google|favicon.ico/i.test(e));
    ok(relevantes.length === 0, `${vp}: sem erros no console da plataforma ${relevantes.length ? JSON.stringify(relevantes.slice(0, 3)) : ''}`);
    await ctx.close();
  }
  // Recurso de aula do curso (imagem) abre dentro da aula.
  for (const [vp, w, h] of [['desktop', 1440, 1000], ['celular', 390, 844]]) {
    const ctx = await browser.newContext({viewport: {width: w, height: h}});
    const p = await ctx.newPage();
    let downloads = 0;
    p.on('download', () => downloads++);
    await ctx.request.post(B + '/login', {data: {email: `carla.souza@${D}`, senha: S}, headers: {Origin: B}});
    await p.goto(B + '/aprendizagem');
    await p.getByRole('button', {name: 'Continuar estudando'}).first().click();
    // Aula em vídeo: o player já está na página ao entrar.
    await p.getByRole('button', {name: /Videoaula de exemplo/}).first().click();
    await p.waitForLoadState('load');
    if (await p.getByRole('button', {name: 'Abrir aula'}).count()) await p.getByRole('button', {name: 'Abrir aula'}).click();
    await p.waitForLoadState('load');
    const player = await p.locator('.course-reading .leitor-video iframe').getAttribute('src').catch(() => null);
    ok(player === 'https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ', `${vp}: aula em vídeo já abre com o player (${player})`);
    await p.waitForTimeout(2500);
    await p.locator('.course-reading .leitor-video').scrollIntoViewIfNeeded();
    await p.screenshot({path: path.join(OUT, `curso-aula-video-${vp}.png`)});
    await p.getByRole('button', {name: /Leitura de gráficos e pontos/}).first().click();
    await p.waitForLoadState('load');
    if (await p.getByRole('button', {name: 'Abrir aula'}).count()) await p.getByRole('button', {name: 'Abrir aula'}).click();
    const img = p.locator('.leitor-recurso .leitor img.leitor-imagem');
    await img.waitFor({timeout: 10000});
    const fim = Date.now() + 10000;
    while (Date.now() < fim && !(await img.evaluate((i) => i.complete && i.naturalWidth > 0))) await p.waitForTimeout(100);
    ok(await img.evaluate((i) => i.naturalWidth > 0), `${vp}: gráfico da aula do curso aparece dentro da aula`);
    ok(await p.getByRole('link', {name: /Baixar uma cópia/}).count() === 1, `${vp}: baixar continua disponível como opção`);
    ok(downloads === 0, `${vp}: nenhum download no curso`);
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `${vp}: aula sem rolagem horizontal`);
    await img.scrollIntoViewIfNeeded();
    await p.screenshot({path: path.join(OUT, `curso-recurso-imagem-${vp}.png`)});
    await ctx.close();
  }
  await browser.close();
  console.log(log.join('\n'));
})().catch((e) => { console.error(log.join('\n')); console.error(e); process.exitCode = 2; });

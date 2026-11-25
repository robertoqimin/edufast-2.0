// U2b: jornada no Edge — a professora envia um vídeo (arquivo) pelo formulário, em partes, e o aluno
// assiste e avança no vídeo dentro da plataforma (material da disciplina e aula do curso).
// Uso: node Codigos/tests/verificar_video_u2b.cjs [pasta-das-capturas]
// Requer a demo completa recém-criada (node infra/demo-completa.cjs reset). Cria um rascunho de vídeo.
const path = require('node:path');
const fs = require('node:fs');
const ROOT = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(ROOT, '.ci-results/demo-video/node_modules/playwright'));
const B = 'http://localhost:5095', S = 'Demo-EduFast-2026!', D = 'demo.edufast.test';
const OUT = process.argv[2] || path.join(ROOT, '.ci-results/ux/u2b-video');
const VIDEO = path.join(ROOT, 'Codigos/demo/aula_funcao_afim.webm');
fs.mkdirSync(OUT, {recursive: true});
const log = [];
const ok = (c, m) => { log.push((c ? 'OK   ' : 'FALHA') + ' ' + m); if (!c) process.exitCode = 1; };

async function esperar(p, fn, arg, ms = 20000) {
  const fim = Date.now() + ms;
  while (Date.now() < fim) { if (await p.evaluate(fn, arg).catch(() => false)) return true; await p.waitForTimeout(150); }
  return false;
}

async function assistir(p, vp, rotulo) {
  const video = p.locator('.leitor-video-arquivo video').first();
  await video.scrollIntoViewIfNeeded();
  await p.evaluate(() => { const v = document.querySelector('.leitor-video-arquivo video'); v.muted = true; return v.play(); });
  ok(await esperar(p, () => document.querySelector('.leitor-video-arquivo video').currentTime > 1.5),
     `${vp}: ${rotulo} toca na página`);
  await p.evaluate(() => { document.querySelector('.leitor-video-arquivo video').currentTime = 12; });
  ok(await esperar(p, () => { const v = document.querySelector('.leitor-video-arquivo video'); return v.currentTime >= 12 && v.readyState >= 2; }),
     `${vp}: ${rotulo} avança para 0:12`);
}

(async () => {
  const browser = await chromium.launch({channel: 'msedge'});
  // 1. Professora envia vídeo pelo formulário (desktop).
  {
    const ctx = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const p = await ctx.newPage();
    const pedidos = [];
    p.on('request', (r) => { if (r.url().includes('/videos/envios')) pedidos.push(r.method()); });
    await ctx.request.post(B + '/login', {data: {email: `ana.ribeiro@${D}`, senha: S}, headers: {Origin: B}});
    await p.goto(B + '/estudos/disciplinas/1/novo');
    await p.selectOption('#conteudo-tipo', 'video');
    ok(await p.locator('fieldset.campo-video').isVisible(), 'desktop: opção "Vídeo" mostra o campo de envio');
    await p.fill('input[name=titulo]', 'Vídeo enviado no teste');
    await p.setInputFiles('[data-video-arquivo]', VIDEO);
    await p.screenshot({path: path.join(OUT, 'professora-formulario-video-desktop.png'), fullPage: true});
    await Promise.all([p.waitForURL(/\/estudos\/conteudos\/\d+$/, {timeout: 60000}), p.click('button:has-text("Salvar rascunho")')]);
    ok(pedidos.includes('POST') && pedidos.includes('PUT'), `desktop: vídeo subiu em partes (${pedidos.join(', ')})`);
    ok(/Rascunho salvo/.test(await p.locator('main').innerText()), 'desktop: rascunho salvo com aviso');
    await assistir(p, 'desktop', 'vídeo no rascunho da professora');
    await p.screenshot({path: path.join(OUT, 'professora-rascunho-video-desktop.png'), fullPage: true});
    await ctx.close();
  }
  // 2. Aluno assiste (material e aula do curso), desktop e celular.
  for (const [vp, w, h] of [['desktop', 1440, 1000], ['celular', 390, 844]]) {
    const ctx = await browser.newContext({viewport: {width: w, height: h}, acceptDownloads: true});
    const p = await ctx.newPage();
    let downloads = 0, erros = [];
    p.on('download', () => downloads++);
    p.on('console', (m) => { if (m.type() === 'error' && !/favicon|youtube|google/i.test(m.text() + (m.location().url || ''))) erros.push(m.text()); });
    await ctx.request.post(B + '/login', {data: {email: `bruno.lima@${D}`, senha: S}, headers: {Origin: B}});
    await p.goto(B + '/estudos');
    await p.getByRole('link', {name: /Matemática/}).first().click();
    await p.getByRole('link', {name: 'Unidade 1 — Funções'}).click();
    ok(/Vídeo/.test(await p.locator('main').innerText()), `${vp}: lista mostra o tipo "Vídeo"`);
    await p.getByRole('link', {name: 'Videoaula — função afim'}).click();
    await assistir(p, vp, 'vídeo enviado no Espaço da disciplina');
    await p.waitForTimeout(800);
    await p.screenshot({path: path.join(OUT, `aluno-material-video-${vp}.png`), fullPage: true});
    await p.goto(B + '/aprendizagem');
    await p.getByRole('button', {name: 'Continuar estudando'}).first().click();
    await p.getByRole('button', {name: /Leitura de gráficos e pontos/}).first().click();
    await p.waitForLoadState('load');
    if (await p.getByRole('button', {name: 'Abrir aula'}).count()) await p.getByRole('button', {name: 'Abrir aula'}).click();
    await p.waitForLoadState('load');
    ok(await p.locator('.course-reading .leitor-video-arquivo video').count() === 1, `${vp}: vídeo enviado no topo da aula do curso`);
    await assistir(p, vp, 'vídeo da aula do curso');
    await p.screenshot({path: path.join(OUT, `aluno-curso-video-${vp}.png`)});
    ok(downloads === 0, `${vp}: nenhum download`);
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `${vp}: sem rolagem horizontal`);
    ok(erros.length === 0, `${vp}: sem erros no console ${erros.length ? JSON.stringify(erros.slice(0, 2)) : ''}`);
    await ctx.close();
  }
  await browser.close();
  console.log(log.join('\n'));
})().catch((e) => { console.error(log.join('\n')); console.error(e); process.exitCode = 2; });

// Gera api/demo/aula_funcao_afim.webm: videoaula curta e original (animação em canvas gravada
// pelo próprio Edge com MediaRecorder), usada pela demo completa para mostrar vídeo enviado (U2b).
// Uso (raiz do projeto): node scripts/gerar-video-demo.cjs
const path = require('path');
const fs = require('fs');
const ROOT = path.resolve(__dirname, '..');
let playwright;
try { playwright = require('playwright'); } catch { playwright = require(path.join(ROOT, '.ci-results/demo-video/node_modules/playwright')); }
const SAIDA = path.join(ROOT, 'api/demo/aula_funcao_afim.webm');

(async () => {
  const browser = await playwright.chromium.launch({channel: 'msedge'});
  const page = await browser.newPage();
  await page.goto('about:blank');
  const base64 = await page.evaluate(async () => {
    const W = 640, H = 360, DURACAO = 18000;
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    document.body.append(c);
    const g = c.getContext('2d');
    const cenas = [
      [0, 'Videoaula: função afim', 'f(x) = a·x + b'],
      [4000, 'O coeficiente b', 'é onde a reta corta o eixo y'],
      [9000, 'O coeficiente a', 'a > 0: a reta sobe'],
      [14000, 'Exemplo', 'f(x) = 2x + 3  →  f(2) = 7'],
    ];
    const px = (x) => 80 + x * 50, py = (y) => 320 - y * 20;
    function quadro(t) {
      g.fillStyle = '#0b1726'; g.fillRect(0, 0, W, H);
      g.strokeStyle = '#5b7a93'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(80, 20); g.lineTo(80, 320); g.lineTo(620, 320); g.stroke();
      const ate = Math.min(1, t / 8000) * 10;
      g.strokeStyle = '#22d3ee'; g.lineWidth = 4; g.beginPath();
      g.moveTo(px(0), py(3)); g.lineTo(px(ate), py(2 * ate + 3)); g.stroke();
      if (t > 4000) { g.fillStyle = '#facc15'; g.beginPath(); g.arc(px(0), py(3), 7, 0, 7); g.fill(); }
      if (t > 14000) { g.fillStyle = '#facc15'; g.beginPath(); g.arc(px(2), py(7), 7, 0, 7); g.fill(); }
      const [, titulo, texto] = cenas.filter(([ini]) => t >= ini).pop();
      g.fillStyle = 'rgba(8,20,32,.85)'; g.fillRect(150, 24, 470, 78);
      g.fillStyle = '#ecf1f8'; g.font = 'bold 26px sans-serif'; g.fillText(titulo, 166, 56);
      g.fillStyle = '#a4bdce'; g.font = '20px sans-serif'; g.fillText(texto, 166, 88);
      g.fillStyle = '#5b7a93'; g.font = '14px sans-serif'; g.fillText('EduFast · demonstração', 480, 345);
    }
    const gravador = new MediaRecorder(c.captureStream(24), {mimeType: 'video/webm;codecs=vp8', videoBitsPerSecond: 600000});
    const pedacos = [];
    gravador.ondataavailable = (e) => pedacos.push(e.data);
    const fim = new Promise((ok) => { gravador.onstop = ok; });
    gravador.start(1000);
    const inicio = performance.now();
    await new Promise((ok) => {
      const passo = () => {
        const t = performance.now() - inicio;
        quadro(t);
        if (t < DURACAO) requestAnimationFrame(passo); else ok();
      };
      passo();
    });
    gravador.stop();
    await fim;
    const bytes = new Uint8Array(await new Blob(pedacos, {type: 'video/webm'}).arrayBuffer());
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  });
  await browser.close();
  fs.writeFileSync(SAIDA, Buffer.from(base64, 'base64'));
  console.log(`Gerado ${path.relative(ROOT, SAIDA)} (${(fs.statSync(SAIDA).size / 1024).toFixed(0)} KiB)`);
})().catch((e) => { console.error(e); process.exitCode = 1; });

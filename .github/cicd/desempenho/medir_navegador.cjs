// B3/MS05: tempo até o conteúdo no Edge com CPU 4x mais lenta e rede limitada (perfil
// "computador modesto + rede limitada" do DESEMPENHO.md). Cache frio a cada execução.
// Uso: node medir_navegador.cjs <base_url> <saida.json> [execucoes]
const {chromium} = require('playwright');
const fs = require('fs');
const BASE = process.argv[2];
const SAIDA = process.argv[3];
const EXECUCOES = Number(process.argv[4] || 5);
const SENHA = process.env.SENHA_MEDICAO || 'Teste-local-2026!';
const PAGINAS = [
  {perfil: 'professor@teste.local', pagina: '/professor/dashboard', shell: true},
  {perfil: 'professor@teste.local', pagina: '/academico', shell: false},
  {perfil: 'aluno@teste.local', pagina: '/aluno/dashboard', shell: true},
  {perfil: 'aluno@teste.local', pagina: '/boletim', shell: false},
  {perfil: 'admin@teste.local', pagina: '/admin/dashboard', shell: true},
  {perfil: 'admin@teste.local', pagina: '/solicitacoes', shell: false},
];
const REDE = {offline: false, latency: 150, downloadThroughput: 5e6 / 8, uploadThroughput: 1e6 / 8};

function mediana(v) { const o = [...v].sort((a, b) => a - b); return o[Math.floor(o.length / 2)]; }

(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const resultado = {perfil: 'CPU 4x mais lenta; 5 Mbit/s down, 1 Mbit/s up, +150 ms; cache frio',
                     navegador: 'Microsoft Edge (Playwright)', execucoes: EXECUCOES, paginas: []};
  for (const item of PAGINAS) {
    const amostras = [];
    for (let i = 0; i < EXECUCOES; i++) {
      const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
      const page = await context.newPage();
      const login = await context.request.post(BASE + '/login', {data: {email: item.perfil, senha: SENHA}, headers: {Origin: BASE}});
      if (login.status() !== 200) throw new Error(`login ${item.perfil}: ${login.status()}`);
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.setCacheDisabled', {cacheDisabled: true});
      await cdp.send('Network.emulateNetworkConditions', REDE);
      await cdp.send('Emulation.setCPUThrottlingRate', {rate: 4});
      await page.addInitScript(() => {
        window.__lcp = 0;
        new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; })
          .observe({type: 'largest-contentful-paint', buffered: true});
      });
      await page.goto(BASE + item.pagina, {waitUntil: 'load'});
      await page.waitForTimeout(500);
      const m = await page.evaluate(() => {
        const nav = performance.getEntriesByType('navigation')[0];
        const recursos = performance.getEntriesByType('resource');
        const scripts = recursos.filter((r) => r.initiatorType === 'script');
        return {lcp: window.__lcp, dcl: nav.domContentLoadedEventEnd, load: nav.loadEventEnd,
                transferido: nav.transferSize + recursos.reduce((s, r) => s + (r.transferSize || 0), 0),
                scripts: scripts.length};
      });
      amostras.push(m);
      await context.close();
    }
    const linha = {pagina: item.pagina, perfil: item.perfil.split('@')[0], shell: item.shell,
      lcp_ms: Math.round(mediana(amostras.map((a) => a.lcp))), dcl_ms: Math.round(mediana(amostras.map((a) => a.dcl))),
      load_ms: Math.round(mediana(amostras.map((a) => a.load))),
      transferido_kib: Math.round(mediana(amostras.map((a) => a.transferido)) / 1024), amostras};
    resultado.paginas.push(linha);
    console.log(`${linha.perfil.padEnd(10)} ${linha.pagina.padEnd(22)} shell=${String(linha.shell).padEnd(5)} ` +
      `LCP=${String(linha.lcp_ms).padStart(5)}ms DCL=${String(linha.dcl_ms).padStart(5)}ms load=${String(linha.load_ms).padStart(5)}ms ` +
      `transferido=${linha.transferido_kib}KiB`);
  }
  await browser.close();
  fs.writeFileSync(SAIDA, JSON.stringify(resultado, null, 2));
})().catch((e) => { console.error(e); process.exitCode = 2; });

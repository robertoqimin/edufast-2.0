// U5: capturas das telas que saem do layout antigo (desktop 1440×1000 e celular 390×844), antes e
// depois da migração. Uso: node api/tests/capturar_telas_u5.cjs <pasta>   (demo completa no ar)
// Só navega (GET); não altera dados.
const path = require('node:path');
const fs = require('node:fs');
const ROOT = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(ROOT, '.ci-results/demo-video/node_modules/playwright'));
const B = 'http://localhost:5095', S = 'Demo-EduFast-2026!', D = 'demo.edufast.test';
const OUT = process.argv[2];
const TELAS = [
  ['secretaria', ['/admin/gestao-turmas', '/admin/disciplinas', '/admin/cadastro-alunos', '/admin/cadastro-professores',
    '/admin/banco-de-dados', '/admin/comunicados', '/admin/alunos/1', '/admin/professores/1', '/solicitacoes']],
  ['ana.ribeiro', ['/professor/dashboard']],
  ['bruno.lima', ['/aluno/dashboard', '/aluno/disciplinas/1']],
];
(async () => {
  fs.mkdirSync(OUT, {recursive: true});
  const browser = await chromium.launch({channel: 'msedge'});
  const feitas = [];
  for (const [conta, urls] of TELAS) {
    for (const [vp, w, h] of [['desktop', 1440, 1000], ['celular', 390, 844]]) {
      const ctx = await browser.newContext({viewport: {width: w, height: h}});
      await ctx.request.post(B + '/login', {data: {email: `${conta}@${D}`, senha: S}, headers: {Origin: B}});
      const p = await ctx.newPage();
      for (const url of urls) {
        const r = await p.goto(B + url);
        await p.waitForLoadState('networkidle').catch(() => {});
        const nome = (conta + url).replace(/[^a-z0-9]+/gi, '-').replace(/-+$/, '') + '-' + vp + '.png';
        await p.screenshot({path: path.join(OUT, nome), fullPage: true});
        feitas.push(`${r.status()} ${new URL(p.url()).pathname.padEnd(28)} ${nome}`);
      }
      await ctx.close();
    }
  }
  await browser.close();
  console.log(feitas.join('\n'));
})().catch((e) => { console.error(e); process.exitCode = 2; });

// UX: auditoria automática de acessibilidade (axe-core, WCAG 2.0/2.1 A e AA) na demonstração completa.
// Uso: node api/tests/auditar_acessibilidade.cjs [saida.json]
// Requer a demo no ar (node infra/demo-completa.cjs start). Não altera dados: só navega (GET).
const path = require('node:path');
const fs = require('node:fs');
const ROOT = path.resolve(__dirname, '..', '..');
const LOCAL = path.join(ROOT, '.ci-results/demo-video/node_modules');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(LOCAL, 'playwright'));
const AXE = fs.readFileSync(process.env.AXE_MODULE || path.join(LOCAL, 'axe-core/axe.min.js'), 'utf8');
// No CI não há Edge: AUDIT_CHANNEL=chromium usa o Chromium do Playwright.
const CANAL = process.env.AUDIT_CHANNEL === 'chromium' ? {} : {channel: 'msedge'};
const ESCOLA = 'http://localhost:5095';
const SENHA = 'Demo-EduFast-2026!';
const D = 'demo.edufast.test';
const SAIDA = process.argv[2] || path.join(ROOT, '.ci-results/ux/acessibilidade.json');
const PERFIS = [
  ['login', null, ['/']],
  ['super-admin', `diretoria@${D}`, ['/admin/dashboard', '/super/usuarios', '/super/escola', '/super/layout', '/calendario-escolar']],
  ['secretaria', `secretaria@${D}`, ['/admin/dashboard', '/admin/cadastro-alunos', '/admin/cadastro-professores', '/admin/comunicados', '/admin/professores/1', '/admin/disciplinas',
    '/admin/alunos/1', '/academico', '/academico/alunos/1/boletim', '/frequencia', '/solicitacoes', '/aprendizagem', '/admin/gestao-turmas']],
  ['professora', `ana.ribeiro@${D}`, ['/professor/dashboard', '/academico', '/academico/avaliacoes/1', '/frequencia',
    '/frequencia/turmas/1/chamada', '/estudos/disciplinas/1', '/estudos/disciplinas/1/novo', '/aprendizagem', '/mensagens',
    '/estudos/conteudos/4',
    // U3: diário da avaliação inteira (com envio aguardando aprovação durante a auditoria)
    '/academico/avaliacoes/13']],
  ['aluno', `bruno.lima@${D}`, ['/aluno/dashboard', '/boletim', '/estudos', '/estudos/disciplinas/1', '/aprendizagem', '/frequencia', '/minha-privacidade',
    // U2: leitor de PDF (slides), imagem, vídeo e aula do curso com recurso
    '/estudos/conteudos/4', '/estudos/conteudos/3', '/estudos/conteudos/9', '/aprendizagem/ofertas/1',
    // U2b: vídeo enviado pela professora
    '/estudos/conteudos/10']],
];

(async () => {
  const browser = await chromium.launch({...CANAL, headless: true});
  const paginas = [];
  for (const [perfil, email, urls] of PERFIS) {
    for (const [vp, w, h] of [['desktop', 1440, 1000], ['celular', 390, 844]]) {
      const context = await browser.newContext({viewport: {width: w, height: h}, bypassCSP: true});
      const page = await context.newPage();
      if (email) {
        const r = await context.request.post(ESCOLA + '/login', {data: {email, senha: SENHA}, headers: {Origin: ESCOLA}});
        if (r.status() !== 200) throw new Error(`login ${perfil}: ${r.status()}`);
      }
      for (const url of urls) {
        await page.goto(ESCOLA + url);
        await page.waitForLoadState('networkidle').catch(() => {});
        // U2: espera o leitor terminar de desenhar o material antes de auditar.
        for (let i = 0; i < 100 && await page.evaluate(() => [...document.querySelectorAll('[data-leitor]')]
          .some((h) => !h.closest('details:not([open])') && !h.dataset.estado)); i++) await page.waitForTimeout(100);
        await page.evaluate(AXE);
        const r = await page.evaluate(async () => {
          const res = await window.axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}});
          return res.violations.map((v) => ({id: v.id, impacto: v.impact, ajuda: v.help, nos: v.nodes.length,
            exemplo: (v.nodes[0] && v.nodes[0].target.join(' ')) || ''}));
        });
        paginas.push({perfil, url, viewport: vp, violacoes: r});
      }
      await context.close();
    }
  }
  await browser.close();
  const regras = {};
  for (const p of paginas) for (const v of p.violacoes) {
    const r = regras[v.id] ||= {id: v.id, impacto: v.impacto, ajuda: v.ajuda, paginas: new Set(), nos: 0, exemplo: v.exemplo};
    r.paginas.add(`${p.perfil} ${p.url}`); r.nos += v.nos;
  }
  const resumo = Object.values(regras).map((r) => ({...r, paginas: r.paginas.size}))
    .sort((a, b) => ['critical', 'serious', 'moderate', 'minor'].indexOf(a.impacto) - ['critical', 'serious', 'moderate', 'minor'].indexOf(b.impacto) || b.paginas - a.paginas);
  fs.mkdirSync(path.dirname(SAIDA), {recursive: true});
  fs.writeFileSync(SAIDA, JSON.stringify({total_paginas: paginas.length, resumo, paginas}, null, 2));
  const semFalha = paginas.filter((p) => !p.violacoes.length).length;
  console.log(`${paginas.length} páginas auditadas (${semFalha} sem violações).`);
  process.exitCode = resumo.length ? 1 : 0;  // qualquer violação reprova (meta O5: todas as páginas)
  for (const r of resumo) console.log(`${r.impacto.padEnd(8)} ${r.id.padEnd(28)} ${String(r.paginas).padStart(3)} pág. ${String(r.nos).padStart(4)} elem.  ${r.ajuda}  [ex.: ${r.exemplo.slice(0, 70)}]`);
})().catch((e) => { console.error(e); process.exitCode = 2; });

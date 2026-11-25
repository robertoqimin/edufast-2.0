// U3: jornada no Edge — a professora lança a avaliação inteira num envio (1 solicitação) e a
// secretaria vê o resumo e aprova várias solicitações de uma vez.
// Uso: node Codigos/tests/verificar_lote_u3.cjs [pasta-das-capturas]
// Requer a demo completa recém-criada (node infra/demo-completa.cjs reset). Grava notas no "Simulado".
const path = require('node:path');
const fs = require('node:fs');
const ROOT = path.resolve(__dirname, '..', '..');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.join(ROOT, '.ci-results/demo-video/node_modules/playwright'));
const B = 'http://localhost:5095', S = 'Demo-EduFast-2026!', D = 'demo.edufast.test';
const OUT = process.argv[2] || path.join(ROOT, '.ci-results/ux/u3-lote');
fs.mkdirSync(OUT, {recursive: true});
const log = [];
const ok = (c, m) => { log.push((c ? 'OK   ' : 'FALHA') + ' ' + m); if (!c) process.exitCode = 1; };

(async () => {
  const browser = await chromium.launch({channel: 'msedge'});
  const entrar = async (ctx, conta) => {
    await ctx.clearCookies();
    await ctx.request.post(B + '/login', {data: {email: `${conta}@${D}`, senha: S}, headers: {Origin: B}});
  };

  // 1. Professora lança a turma inteira (desktop).
  const ctx = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const p = await ctx.newPage();
  await entrar(ctx, 'ana.ribeiro');
  await p.goto(B + '/academico');
  await p.getByRole('link', {name: /Simulado/}).first().click();
  const campos = p.locator('input[name^="valor_"]');
  const total = await campos.count();
  ok(total >= 2, `desktop: diário com um campo de nota por aluno (${total})`);
  ok(await p.locator('form[action$="/lancamentos"]').count() === 1, 'desktop: um único formulário para a turma');
  const notas = ['8.5', '7'];
  for (let i = 0; i < total; i++) await campos.nth(i).fill(notas[i % notas.length]);
  await p.locator('input[name^="observacao_"]').first().fill('Ótima evolução');
  await p.screenshot({path: path.join(OUT, 'professora-diario-preenchido-desktop.png'), fullPage: true});
  await Promise.all([p.waitForURL(/\/solicitacoes/), p.getByRole('button', {name: 'Enviar notas para aprovação'}).click()]);
  ok(/Solicitação enviada para aprovação/.test(await p.locator('main').innerText()), 'desktop: envio confirma "Solicitação enviada para aprovação"');
  await p.goto(B + '/academico');
  await p.getByRole('link', {name: /Simulado/}).first().click();
  const texto = await p.locator('main').innerText();
  ok(new RegExp(`aguardam aprovação da secretaria \\(${total} notas\\)`).test(texto), `desktop: diário mostra o envio aguardando (${total} notas)`);
  ok(/Aguardando aprovação: 8,5/.test(texto), 'desktop: cada aluno mostra a nota aguardando');
  await p.screenshot({path: path.join(OUT, 'professora-diario-aguardando-desktop.png'), fullPage: true});

  // Um segundo envio pendente (material) para a aprovação em lote.
  await p.goto(B + '/estudos/disciplinas/1/novo');
  await p.fill('input[name=titulo]', 'Aviso da semana de provas');
  await p.fill('textarea[name=texto]', 'Revisão na quinta-feira.');
  await Promise.all([p.waitForURL(/\/estudos\/conteudos\/\d+$/), p.getByRole('button', {name: 'Salvar rascunho'}).click()]);
  await Promise.all([p.waitForLoadState('load'), p.getByRole('button', {name: 'Enviar para publicação'}).click()]);

  // 2. Secretaria vê o resumo e aprova as duas de uma vez (desktop e celular).
  for (const [vp, w, h] of [['celular', 390, 844], ['desktop', 1440, 1000]]) {
    const c2 = await browser.newContext({viewport: {width: w, height: h}});
    const s = await c2.newPage();
    await entrar(c2, 'secretaria');
    await s.goto(B + '/solicitacoes');
    const html = await s.locator('main').innerText();
    ok(/Lançar notas da avaliação/.test(html) && /Simulado/.test(html), `${vp}: secretaria vê "Lançar notas da avaliação" do Simulado`);
    ok(new RegExp(`${total} \\(${total} novas, 0 alteradas\\)`).test(html), `${vp}: resumo com ${total} notas novas`);
    ok(/Bruno Lima\s+—\s+8,5\s*·\s*Ótima evolução\s+Nova/i.test(html), `${vp}: tabela com aluno, nota atual, nota enviada e situação`);
    ok(await s.getByRole('button', {name: 'Aprovar selecionadas'}).count() === 1, `${vp}: botão "Aprovar selecionadas"`);
    ok(await s.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `${vp}: sem rolagem horizontal`);
    await s.screenshot({path: path.join(OUT, `secretaria-resumo-${vp}.png`), fullPage: true});
    if (vp === 'desktop') {
      await s.locator('[data-marcar-todas]').check();
      const marcadas = await s.locator('input[name=ids][form=lote-form]:checked').count();
      ok(marcadas >= 2, `desktop: "Marcar todas" seleciona ${marcadas} solicitações`);
      await Promise.all([s.waitForLoadState('load'), s.getByRole('button', {name: 'Aprovar selecionadas'}).click()]);
      const depois = await s.locator('main').innerText();
      ok(new RegExp(`${marcadas} solicitações aprovadas`).test(depois), `desktop: aviso "${marcadas} solicitações aprovadas"`);
      await s.screenshot({path: path.join(OUT, 'secretaria-aprovadas-desktop.png'), fullPage: true});
    }
    await c2.close();
  }

  // 3. Diário da professora com as notas aplicadas.
  await p.goto(B + '/academico');
  await p.getByRole('link', {name: /Simulado/}).first().click();
  const valores = await p.locator('input[name^="valor_"]').evaluateAll((els) => els.map((e) => e.value));
  ok(valores.length === total && valores.every((v) => v === '8.50' || v === '7.00'), `desktop: notas aplicadas no diário (${valores.join(', ')})`);
  await p.screenshot({path: path.join(OUT, 'professora-diario-aplicado-desktop.png'), fullPage: true});
  await ctx.close();
  await browser.close();
  console.log(log.join('\n'));
})().catch((e) => { console.error(log.join('\n')); console.error(e); process.exitCode = 2; });

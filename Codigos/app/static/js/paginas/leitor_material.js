// U2/O7: estudar sem baixar. Leitor de PDF (PDF.js local), imagem ampliável e vídeo do YouTube.
// O arquivo vem da mesma rota protegida (?modo=ler) e é desenhado em canvas: nenhuma página é
// enquadrada e a CSP não muda. Elementos: [data-leitor="pdf|imagem"][data-src], [data-video].
const PDFJS = new URL('../../vendor/pdfjs/pdf.min.mjs', import.meta.url).href;
const WORKER = new URL('../../vendor/pdfjs/pdf.worker.min.mjs', import.meta.url).href;
let biblioteca;

function carregarPdfjs() {
  biblioteca ||= import(PDFJS).then((pdfjs) => {
    pdfjs.GlobalWorkerOptions.workerSrc = WORKER;
    return pdfjs;
  });
  return biblioteca;
}

function botao(texto, rotulo, acao) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'button button-secondary';
  b.textContent = texto;
  if (rotulo) b.setAttribute('aria-label', rotulo);
  b.addEventListener('click', acao);
  return b;
}

function telaCheia(alvo) {
  if (!alvo.requestFullscreen) return null;
  return botao('Tela cheia', 'Abrir o material em tela cheia', () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else alvo.requestFullscreen().catch(() => {});
  });
}

function falha(host, mensagem) {
  host.dataset.estado = 'erro';
  const p = host.querySelector('.leitor-estado') || document.createElement('p');
  p.className = 'leitor-estado notice notice-error';
  p.setAttribute('role', 'alert');
  p.textContent = mensagem;
  host.replaceChildren(p);
}

async function abrirPdf(host) {
  const titulo = host.dataset.titulo || 'Material';
  const estado = host.querySelector('.leitor-estado');
  let documento;
  try {
    const pdfjs = await carregarPdfjs();
    // Uma única busca (sem pedaços): cada leitura gera um registro de auditoria.
    documento = await pdfjs.getDocument({url: host.dataset.src, isEvalSupported: false,
      disableRange: true, disableStream: true, disableAutoFetch: true}).promise;
    host.pdfjs = pdfjs;
  } catch (erro) {
    falha(host, 'Não foi possível abrir o material aqui. Use "Baixar uma cópia" ou avise o professor.');
    return;
  }
  const total = documento.numPages;
  let pagina = Number(host.dataset.pagina) || 1;
  let zoom = 1;
  let tarefa = null;

  const barra = document.createElement('div');
  barra.className = 'leitor-barra';
  barra.setAttribute('role', 'toolbar');
  barra.setAttribute('aria-label', 'Controles do leitor');
  const anterior = botao('‹ Anterior', 'Página anterior', () => ir(pagina - 1));
  const proxima = botao('Próxima ›', 'Próxima página', () => ir(pagina + 1));
  const indicador = document.createElement('span');
  indicador.className = 'leitor-pagina';
  indicador.setAttribute('aria-live', 'polite');
  const menos = botao('−', 'Diminuir zoom', () => { zoom = Math.max(0.5, zoom - 0.25); desenhar(); });
  const mais = botao('+', 'Aumentar zoom', () => { zoom = Math.min(3, zoom + 0.25); desenhar(); });
  const ajustar = botao('Página inteira', 'Ver a página inteira', () => { zoom = 1; desenhar(); });
  barra.append(anterior, indicador, proxima, menos, ajustar, mais);
  const cheia = telaCheia(host);
  if (cheia) barra.append(cheia);

  const folha = document.createElement('div');
  folha.className = 'leitor-folha';
  folha.tabIndex = 0;
  folha.setAttribute('role', 'region');
  const pagina_ = document.createElement('div');
  pagina_.className = 'leitor-pagina-pdf';
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  const texto = document.createElement('div');
  texto.className = 'textLayer';
  pagina_.append(canvas, texto);
  folha.append(pagina_);
  folha.addEventListener('keydown', (e) => {
    if (['ArrowRight', 'PageDown'].includes(e.key)) { e.preventDefault(); ir(pagina + 1); }
    if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); ir(pagina - 1); }
  });
  host.replaceChildren(barra, folha);
  host.dataset.estado = 'pronto';
  host.dataset.paginas = String(total);

  function ir(n) {
    if (n < 1 || n > total || n === pagina) return;
    pagina = n;
    desenhar();
  }

  async function desenhar() {
    const atual = pagina;
    const p = await documento.getPage(atual);
    const largura = Math.max(200, folha.clientWidth - 2);
    const base = p.getViewport({scale: 1});
    // Página inteira à vista (como um slide); o zoom amplia a partir daí.
    const alturaMax = document.fullscreenElement === host ? folha.clientHeight - 24 : window.innerHeight * 0.75;
    const escala = Math.min(largura / base.width, Math.max(240, alturaMax) / base.height) * zoom;
    const vista = p.getViewport({scale: escala});
    const densidade = window.devicePixelRatio || 1;
    if (tarefa) { tarefa.cancel(); tarefa = null; }
    canvas.width = Math.floor(vista.width * densidade);
    canvas.height = Math.floor(vista.height * densidade);
    canvas.style.width = Math.floor(vista.width) + 'px';
    canvas.style.height = Math.floor(vista.height) + 'px';
    pagina_.style.width = canvas.style.width;
    pagina_.style.height = canvas.style.height;
    pagina_.style.setProperty('--scale-factor', String(escala));
    tarefa = p.render({canvasContext: canvas.getContext('2d'), viewport: vista,
      transform: densidade !== 1 ? [densidade, 0, 0, densidade, 0, 0] : null});
    try { await tarefa.promise; } catch (e) { return; }
    tarefa = null;
    if (atual !== pagina) return;
    // Camada de texto: leitores de tela e seleção de texto (transparente sobre o desenho).
    texto.replaceChildren();
    try {
      const camada = new host.pdfjs.TextLayer({textContentSource: p.streamTextContent(), container: texto, viewport: vista});
      await camada.render();
    } catch (e) { /* sem texto: a página continua visível */ }
    indicador.textContent = `Página ${atual} de ${total}`;
    folha.setAttribute('aria-label', `${titulo}, página ${atual} de ${total}`);
    anterior.disabled = atual <= 1;
    proxima.disabled = atual >= total;
    host.dataset.paginaAtual = String(atual);
  }

  let espera;
  new ResizeObserver(() => { clearTimeout(espera); espera = setTimeout(desenhar, 150); }).observe(folha);
  if (estado) estado.remove();
  await desenhar();
}

function abrirImagem(host) {
  const img = document.createElement('img');
  img.src = host.dataset.src;
  img.alt = host.dataset.titulo || 'Imagem do material';
  img.className = 'leitor-imagem';
  img.addEventListener('error', () => falha(host, 'Não foi possível abrir a imagem aqui. Use "Baixar uma cópia".'));
  img.addEventListener('load', () => { host.dataset.estado = 'pronto'; });
  const barra = document.createElement('div');
  barra.className = 'leitor-barra';
  barra.setAttribute('role', 'toolbar');
  barra.setAttribute('aria-label', 'Controles da imagem');
  const ampliar = botao('Ampliar', null, () => {
    const ampliada = host.classList.toggle('leitor-ampliado');
    ampliar.textContent = ampliada ? 'Reduzir' : 'Ampliar';
    ampliar.setAttribute('aria-pressed', String(ampliada));
  });
  ampliar.setAttribute('aria-pressed', 'false');
  barra.append(ampliar);
  const cheia = telaCheia(host);
  if (cheia) barra.append(cheia);
  const folha = document.createElement('div');
  folha.className = 'leitor-folha';
  folha.append(img);
  host.replaceChildren(barra, folha);
}

function abrir(host) {
  if (host.dataset.iniciado) return;
  host.dataset.iniciado = '1';
  if (host.dataset.leitor === 'pdf') abrirPdf(host);
  else if (host.dataset.leitor === 'imagem') abrirImagem(host);
}

// Materiais dentro de <details> (aulas com vários recursos) só carregam ao abrir.
document.querySelectorAll('[data-leitor]').forEach((host) => {
  const caixa = host.closest('details');
  if (caixa && !caixa.open) caixa.addEventListener('toggle', () => caixa.open && abrir(host));
  else abrir(host);
});

// Vídeo: carrega o player do YouTube (sem cookies) só depois do clique.
document.querySelectorAll('[data-load-video]').forEach((button) => {
  button.addEventListener('click', () => {
    const host = button.closest('[data-video]');
    if (!/^[A-Za-z0-9_-]{11}$/.test(host.dataset.video)) return;
    const frame = document.createElement('iframe');
    frame.src = 'https://www.youtube-nocookie.com/embed/' + host.dataset.video;
    frame.title = host.dataset.titulo ? 'Vídeo: ' + host.dataset.titulo : 'Vídeo da aula';
    frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    host.replaceChildren(frame);
  });
});

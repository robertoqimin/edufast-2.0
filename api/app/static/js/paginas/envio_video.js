'use strict';
// U2b: envia o vídeo em partes de 8 MiB (o servidor recebe no máximo 16 MB por pedido) e só então
// envia o formulário, que cita o envio. Retoma do ponto em que parou se uma parte falhar.
// Tudo é validado de novo no servidor (tipo pelo conteúdo, tamanho, dono do envio).
const LIMITE = 300 * 1024 * 1024;

function aviso(form, texto, erro) {
  const status = form.querySelector('[data-video-status]');
  if (!status) return;
  status.textContent = texto;
  status.classList.toggle('notice-error', !!erro);
  status.setAttribute('role', erro ? 'alert' : 'status');
}

async function pedido(url, opcoes, tentativas = 3) {
  for (let i = 1; ; i++) {
    try {
      const r = await fetch(url, {credentials: 'same-origin', ...opcoes});
      if (r.status < 500 || i >= tentativas) return r;
    } catch (e) {
      if (i >= tentativas) throw e;
    }
    await new Promise((ok) => setTimeout(ok, 1000 * i));
  }
}

async function mensagem(r) {
  try { return (await r.json()).erro || `Erro ${r.status}`; } catch (e) { return `Erro ${r.status}`; }
}

async function enviar(form, arquivo) {
  const csrf = form.querySelector('[name=csrf_token]').value;
  const base = form.dataset.envioVideo;
  const barra = form.querySelector('[data-video-progresso]');
  let r = await pedido(base, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
    body: JSON.stringify({tamanho: arquivo.size})});
  if (r.status !== 201) throw new Error(await mensagem(r));
  const envio = await r.json();
  barra.hidden = false;
  let inicio = 0;
  while (inicio < arquivo.size) {
    const fim = Math.min(inicio + envio.parte, arquivo.size);
    r = await pedido(`${base}/${envio.id}/partes?inicio=${inicio}`, {method: 'PUT',
      headers: {'Content-Type': 'application/octet-stream', 'X-CSRF-Token': csrf}, body: arquivo.slice(inicio, fim)});
    if (r.status === 409) {                       // fora de ordem: pergunta onde o servidor está
      const estado = await pedido(`${base}/${envio.id}`, {method: 'GET'});
      if (!estado.ok) throw new Error(await mensagem(estado));
      inicio = (await estado.json()).recebido;
      continue;
    }
    if (!r.ok) throw new Error(await mensagem(r));
    inicio = (await r.json()).recebido;
    barra.value = Math.round((inicio / arquivo.size) * 100);
    aviso(form, `Enviando o vídeo: ${barra.value}%`);
  }
  return envio.id;
}

document.querySelectorAll('form[data-envio-video]').forEach((form) => {
  const arquivo = form.querySelector('[data-video-arquivo]');
  const campo = form.querySelector('[name=envio_video]');
  const tipo = form.querySelector('select[name=tipo]');
  if (tipo && !tipo.querySelector('option[value=video]')) {
    // Sem JavaScript o grupo de vídeo fica desativado (não bloqueia o formulário); aqui ele é liberado
    // e o script do formulário mostra/esconde conforme o tipo escolhido.
    form.querySelectorAll('fieldset.campo-video').forEach((grupo) => { grupo.disabled = false; });
    const opcao = new Option('Vídeo (arquivo MP4 ou WebM)', 'video');
    tipo.add(opcao);
    tipo.dispatchEvent(new Event('change'));
  }
  form.addEventListener('submit', async (evento) => {
    if (!arquivo || arquivo.disabled || !arquivo.files.length || campo.value) return;
    evento.preventDefault();
    const video = arquivo.files[0];
    if (video.size > LIMITE) { aviso(form, 'O vídeo pode ter até 300 MB. Reduza a resolução ou divida em partes.', true); return; }
    if (!/^video\/(mp4|webm)$/.test(video.type)) { aviso(form, 'Envie vídeo MP4 ou WebM.', true); return; }
    const botoes = [...form.querySelectorAll('button')];
    botoes.forEach((b) => { b.disabled = true; });
    try {
      campo.value = await enviar(form, video);
      aviso(form, 'Vídeo enviado. Salvando…');
      if (tipo && tipo.value === 'video') {           // no servidor, vídeo é um arquivo de estudo
        const fixo = document.createElement('input');
        fixo.type = 'hidden'; fixo.name = 'tipo'; fixo.value = 'arquivo';
        form.append(fixo);
        tipo.disabled = true;
      }
      form.submit();
    } catch (erro) {
      campo.value = '';
      aviso(form, `Não foi possível enviar o vídeo: ${erro.message}. Tente de novo.`, true);
      botoes.forEach((b) => { b.disabled = false; });
    }
  });
});

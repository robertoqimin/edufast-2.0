'use strict';
document.querySelectorAll('[data-load-video]').forEach(button => {
  button.addEventListener('click', () => {
    const host = button.closest('[data-video]');
    if (!/^[A-Za-z0-9_-]{11}$/.test(host.dataset.video)) return;
    const frame = document.createElement('iframe');
    frame.src = 'https://www.youtube-nocookie.com/embed/' + host.dataset.video;
    frame.title = 'Vídeo da aula';
    frame.allow = 'encrypted-media; picture-in-picture';
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    host.replaceChildren(frame);
  });
});

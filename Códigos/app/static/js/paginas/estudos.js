// Progressive enhancement only; all content and permissions are validated server-side.
document.querySelectorAll('[data-study-form]').forEach(form => {
  const type = form.querySelector('[name=tipo]');
  if (!type) return;
  const update = () => {
    form.querySelectorAll('[data-study-field]').forEach(group => {
      const active = group.dataset.studyField === type.value;
      group.hidden = !active;
      group.querySelectorAll('input').forEach(input => {
        input.disabled = !active;
        input.required = active;
      });
    });
    form.querySelector('[name=texto]').required = type.value === 'aviso';
  };
  type.addEventListener('change', update);
  update();
});

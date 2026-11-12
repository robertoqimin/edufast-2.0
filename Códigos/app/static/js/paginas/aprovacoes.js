document.addEventListener('DOMContentLoaded', function () {
const permissionsForm=document.getElementById('permissoes-form');
if(permissionsForm){const refresh=()=>{permissionsForm.revisor.checked=permissionsForm.usuario_id.selectedOptions[0]?.dataset.revisor==='true';};permissionsForm.usuario_id.addEventListener('change',refresh);refresh();}
const studentForm=document.getElementById('aluno-proposta');
if(studentForm){ studentForm.aluno_id.addEventListener('change',function(){ const option=this.selectedOptions[0],form=this.form;if(!option)return;form.nome.value=option.dataset.nome;form.curso_serie.value=option.dataset.curso;form.versao.value=option.dataset.versao;});}

document.getElementById('permissoes-form')?.addEventListener('submit',async function(e){e.preventDefault();const form=e.currentTarget;if(form.dataset.sending==='true')return;form.dataset.sending='true';const button=form.querySelector('button');button.disabled=true;try{const result=await fetch('/admin/usuarios/'+Number(form.usuario_id.value)+'/permissoes',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({revisor_materiais:form.revisor.checked})});const data=await result.json();document.getElementById('resultado').textContent=result.ok?'Permissão atualizada. O professor precisa entrar novamente.':data.erro;}catch(error){document.getElementById('resultado').textContent='Falha ao salvar; confira o estado antes de repetir.';}finally{delete form.dataset.sending;button.disabled=false;}});

});

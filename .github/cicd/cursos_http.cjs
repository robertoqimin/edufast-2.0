// Executar somente na fixture sintética criada pelo runner, sem URL de produção.
const assert=require('node:assert/strict');
const {randomUUID}=require('node:crypto');

async function run(base){
  const checks=[];
  async function req(name,path,status,{token,method='GET',body,key,form}={}){
    const response=await fetch(base+path,{method,signal:AbortSignal.timeout(15000),
      headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body!==undefined?{'Content-Type':'application/json'}:{}),
        ...(key?{'Idempotency-Key':key}:{})},body:form || (body!==undefined?JSON.stringify(body):undefined)});
    const text=await response.text();assert.equal(response.status,status,name+': '+text.slice(0,200));
    checks.push({name:'cursos: '+name,status:response.status});
    return {body:response.headers.get('content-type')?.includes('application/json')?JSON.parse(text):text,headers:response.headers};
  }
  async function login(account){return (await req('login '+account,'/login',200,{method:'POST',
    body:{email:account+'@teste01.local',senha:'Teste-escolas-2026!'}})).body.token;}
  const teacher=await login('professor01'),admin=await login('admin'),other=await login('professor04'),student=await login('aluno02');
  await req('nao autenticado','/api/cursos',403);
  await req('JWT invalido','/api/cursos',401,{token:'invalid'});
  const initial={disciplina_id:1,titulo:'Curso modular HTTP',descricao:'Dados ficticios'};
  const createKey=randomUUID();
  const created=(await req('rascunho direto','/api/cursos',201,{token:teacher,method:'POST',body:initial,key:createKey})).body;
  assert.deepEqual((await req('repetir criacao','/api/cursos',201,{token:teacher,method:'POST',body:initial,key:createKey})).body,created);
  const path='/api/cursos/'+created.curso_id;let version=created.versao;
  await req('aluno nao acessa editor',path,403,{token:student});
  await req('outro autor nao acessa editor',path,403,{token:other});
  await req('sem chave de envio',path+'/estrutura',428,{token:teacher,method:'POST',body:{acao:'curso',titulo:'X',versao:version}});
  async function edit(name,body){const result=(await req(name,path+'/estrutura',200,{token:teacher,method:'POST',key:randomUUID(),body:{versao:version,...body}})).body;version=result.versao;return result.item_id;}
  const module=await edit('criar modulo',{acao:'adicionar',tipo:'capitulo',titulo:'Modulo HTTP'});
  const chapter=await edit('criar capitulo',{acao:'adicionar',tipo:'tema',pai_id:module,titulo:'Capitulo HTTP'});
  const video=await edit('aula YouTube legada',{acao:'adicionar',tipo:'aula',pai_id:chapter,titulo:'Video HTTP',video:'abcdefghijk'});
  const text=await edit('aula sem video',{acao:'adicionar',tipo:'aula',pai_id:chapter,titulo:'Texto HTTP',tipo_aula:'texto',corpo:'Texto <script>ficticio</script>'});
  const outline=(await req('indice de quatro niveis',path,200,{token:teacher})).body;
  assert.equal(outline.modulos[0].capitulos[0].aulas[1].id,text);
  assert.equal('corpo' in outline.modulos[0].capitulos[0].aulas[1],false);
  await req('versao antiga',path+'/estrutura',409,{token:teacher,method:'POST',key:randomUUID(),body:{acao:'curso',titulo:'Antigo',versao:1}});
  await req('video invalido',path+'/estrutura',400,{token:teacher,method:'POST',key:randomUUID(),body:{acao:'adicionar',tipo:'aula',pai_id:chapter,titulo:'Invalida',video:'http://invalid.test',versao:version}});
  function fileForm(){const form=new FormData();form.set('tipo','arquivo');form.set('titulo','Apoio PDF');form.set('versao',String(version));
    form.set('arquivo',new Blob(['%PDF-1.4\nFicticio MS04\n%%EOF'],{type:'application/pdf'}),'apoio.pdf');return form;}
  const uploadKey=randomUUID();
  const uploaded=(await req('upload privado',path+`/aulas/${text}/recursos`,201,{token:teacher,method:'POST',key:uploadKey,form:fileForm()})).body;
  assert.deepEqual((await req('repetir upload',path+`/aulas/${text}/recursos`,201,{token:teacher,method:'POST',key:uploadKey,form:fileForm()})).body,uploaded);
  version=uploaded.versao;
  const rid=uploaded.recurso.id,authorFile=path+`/aulas/${text}/recursos/${rid}/arquivo`;
  assert.ok((await req('autor confere arquivo',authorFile,200,{token:teacher})).body.startsWith('%PDF'));
  await req('admin confere arquivo',authorFile,200,{token:admin});
  await req('aluno nao baixa pelo editor',authorFile,403,{token:student});
  const proposal=(await req('pedido de publicacao',path+'/solicitar-publicacao',202,{token:teacher,method:'POST',key:randomUUID(),body:{versao:version}})).body;
  await req('pedido pendente duplicado',path+'/solicitar-publicacao',409,{token:teacher,method:'POST',key:randomUUID(),body:{versao:version}});
  await edit('editar invalida revisao',{acao:'curso',titulo:'Curso HTTP revisado',descricao:''});
  const decision='/solicitacoes/alteracoes/'+proposal.id+'/decidir';
  await req('revisao obsoleta recusada',decision,409,{token:admin,method:'POST',key:randomUUID(),body:{decisao:'aprovar'}});
  await req('rejeitar pedido antigo',decision,200,{token:admin,method:'POST',key:randomUUID(),body:{decisao:'rejeitar'}});
  const revised=(await req('nova versao para revisao',path+'/solicitar-publicacao',202,{token:teacher,method:'POST',key:randomUUID(),body:{versao:version}})).body;
  await req('professor nao aprova','/solicitacoes/alteracoes/'+revised.id+'/decidir',403,{token:other,method:'POST',key:randomUUID(),body:{decisao:'aprovar'}});
  await req('aprovacao administrativa','/solicitacoes/alteracoes/'+revised.id+'/decidir',200,{token:admin,method:'POST',key:randomUUID(),body:{decisao:'aprovar'}});
  version=(await req('versao publicada',path,200,{token:teacher})).body.curso.versao;
  const offered=(await req('liberar oferta',path+'/ofertas',200,{token:admin,method:'POST',key:randomUUID(),body:{versao:version,turma_disciplina_id:1}})).body;
  version=offered.versao;
  const offer=offered.id,learn='/api/aprender/'+offer;
  assert.ok((await req('biblioteca do aluno','/api/cursos',200,{token:student})).body.ofertas.some(row=>row.id===offer));
  assert.ok((await req('cursos da disciplina','/api/estudos/disciplinas/1/cursos',200,{token:student})).body.ofertas.some(row=>row.id===offer));
  await req('disciplina alheia','/api/estudos/disciplinas/999/cursos',404,{token:student});
  assert.equal((await req('YouTube preservado',learn,200,{token:student})).body.aula.video_id,'abcdefghijk');
  const reading=(await req('texto sem video',learn+'?aula='+text,200,{token:student})).body;
  assert.equal(reading.aula.video_id,null);assert.equal(reading.aula.tipo,'texto');
  assert.equal(reading.anterior_id,video);assert.equal(reading.proxima_id,null);
  assert.equal((await req('cursor inicial',learn+'/retomada',200,{token:student})).body.versao,0);
  const openKey=randomUUID();
  const opened=(await req('registrar ultima aula',learn+`/aulas/${text}/abrir`,200,{token:student,method:'POST',key:openKey,body:{versao:0}})).body;
  assert.deepEqual((await req('repetir abertura',learn+`/aulas/${text}/abrir`,200,{token:student,method:'POST',key:openKey,body:{versao:0}})).body,opened);
  await req('cursor obsoleto',learn+`/aulas/${video}/abrir`,409,{token:student,method:'POST',key:randomUUID(),body:{versao:0}});
  assert.equal((await req('retomar sem concluir',learn,200,{token:student})).body.aula.id,text);
  await req('concluir explicitamente',learn+`/aulas/${text}/concluir`,200,{token:student,method:'POST',key:randomUUID(),body:{}});
  await req('conclusao repetida',learn+`/aulas/${text}/concluir`,200,{token:student,method:'POST',key:randomUUID(),body:{}});
  const progress=(await req('progresso sem duplicacao',learn,200,{token:student})).body;
  assert.equal(progress.progresso,50);assert.equal(progress.aula.id,text);
  const download=learn+`/aulas/${text}/recursos/${rid}/arquivo`;
  const response=await req('download pela oferta',download,200,{token:student});
  assert.equal(response.headers.get('cache-control'),'no-store');assert.equal(response.headers.get('x-content-type-options'),'nosniff');
  assert.ok(response.headers.get('content-disposition').includes('attachment'));assert.ok(response.body.startsWith('%PDF'));
  await req('publicado imutavel',path+'/estrutura',409,{token:teacher,method:'POST',key:randomUUID(),body:{acao:'curso',titulo:'X',versao:version}});
  await req('legacy nao ignora versao','/cursos/'+created.curso_id+'/estrutura',409,{token:admin,method:'POST',body:{acao:'curso',titulo:'Atalho'}});
  const duplicated=(await req('duplicar edicao',path+'/duplicar',201,{token:teacher,method:'POST',key:randomUUID(),body:{versao:version}})).body;
  assert.notEqual(duplicated.curso_id,created.curso_id);
  await req('arquivar curso',path+'/estado',200,{token:admin,method:'POST',key:randomUUID(),body:{estado:'arquivado',versao:version}});
  await req('acesso revogado',learn,404,{token:student});
  await req('download revogado',download,404,{token:student});
  await req('historico do autor preservado',path,200,{token:teacher});
  return checks;
}
module.exports={run};

// Contratos JWT/HTTP reais, somente na fixture sintética criada pelo runner.
const assert = require('node:assert/strict');
const {randomUUID} = require('node:crypto');

async function run(base) {
  const checks = [];
  async function request(name, route, expected, {token, json, method='GET', key, form}={}) {
    const response = await fetch(base+route, {method, signal:AbortSignal.timeout(15000),
      headers:{...(token?{Authorization:`Bearer ${token}`} : {}),
        ...(json!==undefined?{'Content-Type':'application/json'}:{}),
        ...(key?{'Idempotency-Key':key}:{})},
      body:form || (json!==undefined?JSON.stringify(json):undefined)});
    const text = await response.text();
    assert.equal(response.status,expected,`${name}: ${text.slice(0,200)}`);
    checks.push({name:'estudos: '+name,status:response.status});
    return {body:response.headers.get('content-type')?.includes('application/json')?JSON.parse(text):text,
      headers:response.headers};
  }
  async function login(account) {
    return (await request(`login ${account}`,'/login',200,{method:'POST',
      json:{email:account+'@teste01.local',senha:'Teste-escolas-2026!'}})).body.token;
  }
  const admin=await login('admin'),teacher=await login('professor01'),other=await login('professor04');
  const pupil=await login('aluno02');
  const discipline='/estudos/disciplinas/1',sections=discipline+'/abas';
  await request('sem autenticação','/estudos?formato=json',403);
  await request('token inválido','/estudos?formato=json',401,{token:'invalid'});
  await request('ofertas do professor','/estudos?formato=json',200,{token:teacher});
  await request('aluno não cria aba',sections,403,{token:pupil,method:'POST',key:randomUUID(),json:{nome:'Proibida',ordem:1}});
  const key=randomUUID(),sectionData={nome:'Unidade HTTP',ordem:10};
  const section=(await request('criar aba',sections,201,{token:teacher,method:'POST',key,json:sectionData})).body;
  assert.deepEqual((await request('repetir criação da aba',sections,201,{token:teacher,method:'POST',key,json:sectionData})).body,section);
  const sid=section.id,editSection=`/estudos/abas/${sid}/editar`;
  await request('outro autor não altera aba',editSection,403,{token:other,method:'POST',key:randomUUID(),json:{nome:'Intrusão',ordem:0,versao:1}});
  const edited=(await request('renomear e ordenar aba',editSection,200,{token:teacher,method:'POST',key:randomUUID(),json:{nome:'Revisão HTTP',ordem:2,versao:1}})).body;
  assert.equal(edited.versao,2);
  await request('versão antiga da aba',editSection,409,{token:teacher,method:'POST',key:randomUUID(),json:{nome:'Antigo',ordem:0,versao:1}});
  const tab=discipline+`?formato=json&aba=secao-${sid}`;
  assert.ok((await request('aba renomeada na lista',tab,200,{token:pupil})).body.abas.some(r=>r.id===sid&&r.nome==='Revisão HTTP'&&r.ordem===2));
  function material() {
    const form=new FormData();form.set('tipo','arquivo');form.set('titulo','Material HTTP');
    form.set('texto','Material fictício para testar compatibilidade.');form.set('secao_id',String(sid));
    form.set('arquivo',new Blob(['%PDF-1.4\nMaterial ficticio HTTP\n%%EOF'],{type:'application/pdf'}),'material.pdf');
    return form;
  }
  const uploadKey=randomUUID();
  const draft=(await request('upload multipart',discipline+'/novo?formato=json',201,{token:teacher,method:'POST',key:uploadKey,form:material()})).body;
  assert.deepEqual((await request('repetir upload sem duplicar',discipline+'/novo?formato=json',201,{token:teacher,method:'POST',key:uploadKey,form:material()})).body,draft);
  const content=`/estudos/conteudos/${draft.id}`,file=content+'/arquivo';
  await request('rascunho privado',content+'?formato=json',404,{token:pupil});
  await request('arquivo privado antes da aprovação',file,404,{token:pupil});
  assert.equal((await request('rascunho fora da lista do aluno',tab,200,{token:pupil})).body.total,0);
  await request('outro autor não publica',content+'/publicar',403,{token:other,method:'POST',key:randomUUID(),json:{versao:1}});
  const proposal=(await request('solicitar publicação',content+'/publicar',202,{token:teacher,method:'POST',key:randomUUID(),json:{versao:1}})).body;
  await request('arquivo privado durante revisão',file,404,{token:pupil});
  await request('aprovar pelo fluxo existente',`/solicitacoes/alteracoes/${proposal.id}/decidir`,200,{token:admin,method:'POST',key:randomUUID(),json:{decisao:'aprovar'}});
  assert.equal((await request('lista publicada',tab,200,{token:pupil})).body.conteudos[0].id,draft.id);
  const published=(await request('conteúdo publicado',content+'?formato=json',200,{token:pupil})).body;
  assert.equal(published.estado,'publicado');
  const downloaded=await request('download autorizado',file,200,{token:pupil});
  assert.ok(downloaded.body.startsWith('%PDF-1.4'));
  assert.equal(downloaded.headers.get('cache-control'),'no-store');
  assert.equal(downloaded.headers.get('x-content-type-options'),'nosniff');
  assert.ok(downloaded.headers.get('content-disposition').includes('attachment'));
  const archiveKey=randomUUID(),archive=`/estudos/abas/${sid}/arquivar`;
  const archived=(await request('arquivar aba',archive,200,{token:teacher,method:'POST',key:archiveKey,json:{versao:2}})).body;
  assert.deepEqual((await request('repetir arquivamento',archive,200,{token:teacher,method:'POST',key:archiveKey,json:{versao:2}})).body,archived);
  await request('aba arquivada indisponível ao aluno',tab,404,{token:pupil});
  await request('conteúdo direto revogado',content+'?formato=json',404,{token:pupil});
  await request('download revogado',file,404,{token:pupil});
  assert.equal((await request('histórico preservado ao autor',content+'?formato=json',200,{token:teacher})).body.estado,'publicado');
  await request('arquivo preservado ao autor',file,200,{token:teacher});
  return checks;
}
module.exports={run};

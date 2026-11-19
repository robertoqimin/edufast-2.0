// Usado somente pelo runner que cria seu próprio servidor descartável.
const assert = require('node:assert/strict');
const {randomUUID} = require('node:crypto');

async function run(base) {
  const checks = [];
  async function request(name, route, expected, {token, json, method='GET', key, form}={}) {
    const response = await fetch(base+route, {method, signal:AbortSignal.timeout(15000),
      headers:{...(token?{Authorization:`Bearer ${token}`} : {}), ...(json!==undefined?{'Content-Type':'application/json'}:{}),
        ...(key?{'Idempotency-Key':key}:{})}, body:form || (json!==undefined?JSON.stringify(json):undefined)});
    const text = await response.text();
    assert.equal(response.status,expected,`${name}: ${text.slice(0,200)}`);
    checks.push({name,status:response.status});
    return {body:response.headers.get('content-type')?.includes('application/json')?JSON.parse(text):text, headers:response.headers};
  }
  async function login(account) {
    return (await request(`login ${account}`,'/login',200,{method:'POST',json:{email:account+'@teste01.local',senha:'Teste-escolas-2026!'}})).body.token;
  }
  const admin=await login('admin'), teacher=await login('professor01'), other=await login('professor02');
  const pupil=await login('aluno02'), stranger=await login('aluno03');
  await request('nao autenticado','/frequencia?formato=json',403);
  await request('token adulterado','/frequencia?formato=json',401,{token:'invalid'});
  const html=(await request('formulario autorizado','/frequencia/turmas/1/chamada',200,{token:teacher})).body;
  const when=html.match(/name="dia" value="([^"]+)"/)[1];
  const body={turma_disciplina_id:1,dia:when,aula:1,presencas:Object.fromEntries(Array.from({length:20},(_,i)=>[String(i+1),i===1?'falta':'presente']))};
  await request('sem idempotencia','/frequencia/chamadas',428,{token:teacher,method:'POST',json:body});
  await request('professor sem vinculo','/frequencia/chamadas',403,{token:other,method:'POST',key:randomUUID(),json:body});
  const key=randomUUID();
  const first=(await request('chamada confirmada pelo professor','/frequencia/chamadas',201,{token:teacher,method:'POST',key,json:body})).body;
  assert.equal(first.estado,'aprovada');
  const replay=(await request('reenvio de chamada','/frequencia/chamadas',201,{token:teacher,method:'POST',key,json:body})).body;
  assert.equal(first.id,replay.id);
  await request('duplicacao de aula','/frequencia/chamadas',409,{token:teacher,method:'POST',key:randomUUID(),json:body});
  const query=`/frequencia/relatorio?inicio=${when}&fim=${when}&formato=json`;
  assert.equal((await request('confirmacao imediata no relatorio',query,200,{token:admin})).body.totais.length,20);
  const decision={decisao:'aprovar',versao:1,motivo:'Conferido no teste HTTP'};
  await request('professor nao decide',`/frequencia/chamada/${first.id}/decidir`,403,{token:teacher,method:'POST',key:randomUUID(),json:decision});
  await request('conflito de versao',`/frequencia/chamada/${first.id}/decidir`,409,{token:admin,method:'POST',key:randomUUID(),json:{...decision,versao:999}});
  await request('confirmacao nao exige nova aprovacao',`/frequencia/chamada/${first.id}/decidir`,409,{token:admin,method:'POST',key:randomUUID(),json:decision});
  const correction={...body,anterior_id:first.id,versao:first.versao,motivo:'Correção conferida no HTTP'};
  await request('correcao sem versao','/frequencia/chamadas',428,{token:teacher,method:'POST',key:randomUUID(),json:{...correction,versao:undefined}});
  const corrected=(await request('correcao direta','/frequencia/chamadas',201,{token:teacher,method:'POST',key:randomUUID(),json:correction})).body;
  assert.notEqual(corrected.id,first.id);
  await request('correcao obsoleta','/frequencia/chamadas',409,{token:teacher,method:'POST',key:randomUUID(),json:correction});
  function certificate() {const form=new FormData();form.set('aluno_id','2');form.set('inicio',when);form.set('fim',when);
    form.set('arquivo',new Blob(['%PDF-1.4\nDocumento ficticio\n%%EOF'],{type:'application/pdf'}),'teste.pdf');return form;}
  const certKey=randomUUID();
  const cert=(await request('envio multipart','/frequencia/atestados?formato=json',201,{token:pupil,method:'POST',key:certKey,form:certificate()})).body;
  const again=(await request('reenvio multipart','/frequencia/atestados?formato=json',201,{token:pupil,method:'POST',key:certKey,form:certificate()})).body;
  assert.equal(cert.id,again.id);
  const download=`/frequencia/atestados/${cert.id}/arquivo`;
  await request('professor sem acesso medico',download,404,{token:teacher});
  await request('outro aluno sem acesso',download,404,{token:stranger});
  const own=await request('download proprio',download,200,{token:pupil});
  assert.equal(own.headers.get('cache-control'),'no-store');
  assert.ok(own.headers.get('content-disposition').includes('attachment'));
  await request('aceite administrativo',`/frequencia/atestado/${cert.id}/decidir`,200,{token:admin,method:'POST',key:randomUUID(),json:decision});
  const result=(await request('relatorio confirmado',query,200,{token:admin})).body;
  const absence=result.totais.find(row=>row.aluno_id===2);
  assert.equal(absence.justificadas,1);assert.equal(absence.faltas_total,1);assert.equal(absence.percentual_presenca,'0.00');
  const ownReport=(await request('relatorio do aluno',query,200,{token:pupil})).body;
  assert.deepEqual(ownReport.totais.map(row=>row.aluno_id),[2]);
  const csv=await request('exportacao CSV',query.replace('formato=json','formato=csv'),200,{token:admin});
  assert.ok(csv.headers.get('content-type').includes('text/csv'));assert.ok(!csv.body.includes('.enc'));
  await request('professor nao exporta',query.replace('formato=json','formato=csv')+'&turma_disciplina_id=1',403,{token:teacher});
  checks.push(...await require('./estudos_http.cjs').run(base));
  return checks;
}
module.exports={run};

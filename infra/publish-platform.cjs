// Executado no host pelo operador SSH. Mantém a aplicação escolar sem egress público.
const fs = require('node:fs');
const {spawnSync} = require('node:child_process');
const {commands} = require('./manage.cjs');
function exportDirectory(revision, school, runner = spawnSync) {
  // Valida ID no inventário antes de compor argv; nenhum shell é utilizado.
  const base = commands(revision, 'status', school)[0].slice(0, -3);
  const result = runner('docker', [...base, 'exec', '-T', `app-${school}`, 'flask', '--app', 'app:create_app()', 'platform-directory'],
    {encoding:'utf8', shell:false, maxBuffer:8*1024*1024, timeout:30000});
  if (result.error || result.status !== 0) throw new Error('Nao foi possivel consultar a escola; nenhum dado enviado.');
  try { return JSON.parse(result.stdout); }
  catch { throw new Error('Resposta da escola invalida; nenhum dado enviado.'); }
}
async function publish(revision, school, origin, keyFile, runner=spawnSync, sender=fetch) {
  const url = new URL(origin);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash)
    throw new Error('Informe somente a origem HTTPS do painel central.');
  const token = fs.readFileSync(keyFile, 'utf8').trim();
  if (!/^[A-Za-z0-9_-]{64}$/.test(token)) throw new Error('Chave de integracao invalida.');
  const payload = exportDirectory(revision, school, runner);
  const response = await sender(url.origin + '/integracao/' + school + '/pessoas', {
    method:'POST', redirect:'error', signal:AbortSignal.timeout(20000),
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'}, body:JSON.stringify(payload),
  });
  if (response.status !== 200) throw new Error('Sincronizacao recusada ('+response.status+'); confira a chave, escola e horario.');
  return {school, synced:true};
}
if (require.main === module) {
  if (process.argv.length !== 6) {console.error('Uso: node infra/publish-platform.cjs revisao escola origem-https arquivo-chave');process.exitCode=1;}
  else publish(...process.argv.slice(2)).then(result=>console.log(JSON.stringify(result)))
    .catch(()=>{console.error('Sincronizacao nao concluida. Confira configuracao, escola, chave e disponibilidade central.');process.exitCode=1;});
}
module.exports = {publish, exportDirectory};

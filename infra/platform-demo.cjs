// Ambiente local descartável. Não usa os bancos persistentes Teste 01/02.
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const name = 'edufast-platform-demo';
const root = path.resolve(__dirname, '..');
const image = 'edufast-platform:test';
function run(args, capture = false) {
  const result = spawnSync('docker', args, {cwd: root, shell: false,
    ...(capture ? {encoding: 'utf8'} : {stdio: 'inherit'})});
  if (result.error || result.status !== 0) throw new Error('Docker falhou. Confira o Docker Desktop e repita.');
  return result.stdout;
}
function existing() {
  const result = run(['ps', '-a', '--filter', `name=^/${name}$`, '--format', '{{.Names}}'], true);
  if (!result.trim()) return false;
  const label = run(['inspect', '--format', '{{index .Config.Labels "edufast.platform.demo"}}', name], true).trim();
  if (label !== '1') throw new Error('Nome ocupado por outro container; nenhuma alteracao realizada.');
  return true;
}
(async () => {
  const action = process.argv[2];
  if (!['start', 'stop', 'status'].includes(action) || process.argv.length !== 3) throw new Error('Uso: node infra/platform-demo.cjs start|stop|status');
  const present = existing();
  if (action === 'stop') {
    if (present) run(['stop', name]);
    console.log('Demonstracao encerrada; dados sinteticos descartados.'); return;
  }
  if (action === 'status') {
    run(['ps', '-a', '--filter', `name=^/${name}$`, '--format', '{{.Names}} {{.Status}}']); return;
  }
  if (!present) {
    run(['build', '-f', '.github/cicd/Dockerfile', '-t', image, '.']);
    run(['run', '-d', '--rm', '--name', name, '--label', 'edufast.platform.demo=1',
      '-p', '127.0.0.1:5093:8000', '--mount', `type=bind,source=${path.join(root,'.github/cicd/tests')},target=/tests,readonly`,
      '-e', 'EDUFAST_PLATFORM_VISUAL=1', '-e', 'PYTHONPATH=/app', '-e', 'DB_URL=sqlite:///:memory:',
      '-e', 'SECRET_KEY=isolated-school-import-only-demo-2026', '--entrypoint', 'python', image, '/tests/platform_visual_fixture.py']);
  }
  let ready = false;
  for (let n = 0; n < 60; n++) {
    const probe = spawnSync('docker', ['exec', name, 'python', '-c',
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=1)"],
      {stdio:'ignore',shell:false,timeout:5000});
    if (!probe.error && probe.status === 0) {ready = true; break;}
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!ready) throw new Error('Demonstracao ainda indisponivel. Confira docker logs edufast-platform-demo.');
  console.log('DEMONSTRACAO DESCARTAVEL: http://127.0.0.1:5093/login\nEmail: dono@plataforma.local\nSenha publica somente de teste: Plataforma-teste-2026!\nDuas escolas ficticias, 52 contas e financeiro ficticio. Parar descarta os dados.');
})().catch(error => {console.error(error.message); process.exitCode=1;});

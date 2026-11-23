// Duas escolas locais persistentes. Não aceita destinos ou manifestos de produção.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
const assert = require('node:assert/strict');
const {render} = require('./generate.cjs');
const ROOT = path.resolve(__dirname, '..');
const DIRECTORY = path.join(ROOT, '.ci-results', 'duas-escolas');
const PROJECT = 'edufast-duas-escolas-teste';
const IMAGE = 'edufast-duas-escolas:local';
const SCHOOLS = [{id: 'teste01', host: 'teste01.localhost', port: 5081},
  {id: 'teste02', host: 'teste02.localhost', port: 5082}];

function configuration() {
  const result = render({image: 'ghcr.io/samucau1/edufast-2.0@sha256:' + 'a'.repeat(64), schools: SCHOOLS});
  delete result.compose.services.gateway;
  delete result.compose.networks.edge;
  result.compose.name = PROJECT;
  for (const {id, host, port} of SCHOOLS) {
    const app = result.compose.services[`app-${id}`], db = result.compose.services[`db-${id}`];
    app.image = IMAGE;
    app.ports = [`127.0.0.1:${port}:8000`];
    // Docker não publica portas de um app ligado apenas a redes internal.
    // Cada escola mantém sua rede de entrada exclusiva; o banco fica interno.
    delete result.compose.networks[`front-${id}`];
    result.compose.networks[`local-${id}`] = {};
    app.networks = [`local-${id}`, `back-${id}`];
    Object.assign(app.environment, {APP_ENV: 'development', PYTHON_DOTENV_DISABLED: '1',
      DB_URL: '', DB_NAME: `edufast_${id}`, EDUFAST_TWO_SCHOOLS_TEST: '1', EDUFAST_TEST_SCHOOL: id,
      TRUSTED_HOSTS: `${host},localhost,127.0.0.1`, RELEASE_ID: IMAGE});
    db.environment.POSTGRES_DB = `edufast_${id}`;
  }
  return result;
}

function prepare() {
  if (fs.existsSync(DIRECTORY)) {
    const expected = JSON.parse(fs.readFileSync(path.join(DIRECTORY, 'compose.json'), 'utf8'));
    if (expected.name !== PROJECT || !fs.existsSync(path.join(DIRECTORY, '.env')))
      throw new Error('Configuracao local incompleta; recuperar arquivos, sem regenerar segredos.');
    // Atualiza somente a descrição dos serviços; nunca substitui os segredos.
    const desired = JSON.stringify(configuration().compose, null, 2) + '\n';
    fs.writeFileSync(path.join(DIRECTORY, 'compose.json'), desired, {mode: 0o600});
    return;
  }
  const result = configuration();
  fs.mkdirSync(path.dirname(DIRECTORY), {recursive: true});
  fs.mkdirSync(DIRECTORY, {mode: 0o700});
  fs.writeFileSync(path.join(DIRECTORY, 'compose.json'), JSON.stringify(result.compose, null, 2) + '\n', {flag: 'wx', mode: 0o600});
  fs.writeFileSync(path.join(DIRECTORY, '.env'), result.env, {flag: 'wx', mode: 0o600});
}

function run(executable, args, capture = false) {
  const result = spawnSync(executable, args, {cwd: ROOT, shell: false,
    ...(capture ? {encoding: 'utf8'} : {stdio: 'inherit'})});
  if (result.error || result.status !== 0) throw new Error(`Comando ${executable} falhou. Nenhum volume foi apagado.`);
  return result.stdout;
}
const compose = (...args) => run('docker', ['compose', '-p', PROJECT,
  '--env-file', path.join(DIRECTORY, '.env'), '-f', path.join(DIRECTORY, 'compose.json'), ...args]);
function request(school, route, method = 'GET', body, headers = {}) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : undefined;
    const req = http.request({hostname: '127.0.0.1', port: school.port, path: route, method, timeout: 15000,
      headers: {Host: `${school.host}:${school.port}`, ...(data ? {'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)} : {}), ...headers}}, res => {
      let text = ''; res.on('data', chunk => text += chunk);
      res.on('end', () => resolve({status: res.statusCode, headers: res.headers, text}));
    });
    req.on('error', reject); req.on('timeout', () => req.destroy(new Error('Timeout HTTP'))); req.end(data);
  });
}

async function verify() {
  const sessions = [];
  for (const school of SCHOOLS) {
    compose('exec', '-T', `app-${school.id}`, 'python', 'two_school_test_data.py', '--verify');
    assert.equal((await request(school, '/healthz')).status, 200);
    for (const [prefix, count, route] of [['admin', 1, '/admin/dashboard'], ['professor', 5, '/professor/dashboard'], ['aluno', 20, '/aluno/dashboard']]) {
      for (let i = 1; i <= count; i++) {
        const email = `${prefix}${prefix === 'admin' ? '' : String(i).padStart(2, '0')}@${school.id}.local`;
        const login = await request(school, '/login', 'POST', {email, senha: 'Teste-escolas-2026!'});
        assert.equal(login.status, 200, `Login de ${email}`);
        const cookie = login.headers['set-cookie'].map(value => value.split(';')[0]).join('; ');
        assert.equal((await request(school, route, 'GET', null, {Cookie: cookie})).status, 200, `Painel de ${email}`);
        if (prefix === 'admin') sessions.push({cookie, token: JSON.parse(login.text).token});
      }
    }
  }
  for (let i = 0; i < 2; i++) {
    const other = SCHOOLS[1 - i];
    assert.ok([401, 403].includes((await request(other, '/admin/dashboard', 'GET', null, {Cookie: sessions[i].cookie})).status));
    assert.ok([401, 403].includes((await request(other, '/alunos/busca?q=Aluno', 'GET', null,
      {Authorization: `Bearer ${sessions[i].token}`})).status));
    const own = await request(SCHOOLS[i], '/alunos/busca?q=Aluno', 'GET', null, {Cookie: sessions[i].cookie});
    const students = JSON.parse(own.text).alunos;
    assert.equal(students.length, 20);
    assert.ok(students.every(s => s.nome.endsWith(`Teste ${SCHOOLS[i].id.slice(-2)}`)));
  }
  console.log('Verificado: 40 alunos, 10 professores, 6 materias; 52 logins/paineis e rejeicao cruzada de sessoes/tokens.');
}

async function main() {
  const action = process.argv[2] || 'start';
  if (!['prepare', 'start', 'verify', 'status', 'stop', 'logs'].includes(action)) throw new Error('Use prepare, start, verify, status, stop ou logs.');
  if (action !== 'prepare' && action !== 'start' && !fs.existsSync(DIRECTORY)) throw new Error('Execute start primeiro.');
  prepare();
  if (action === 'prepare') return;
  if (action === 'start') {
    compose('config', '--quiet');
    run('docker', ['build', '-f', '.github/cicd/Dockerfile', '-t', IMAGE, '.']);
    compose('up', '-d', '--wait', '--wait-timeout', '180', ...SCHOOLS.map(s => `db-${s.id}`));
    for (const {id} of SCHOOLS) compose('run', '--rm', '--no-deps', '-T', '--entrypoint', 'python', `app-${id}`, 'two_school_test_data.py');
    compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '180');
    // Reiniciar não exige que o usuário conserve as senhas públicas iniciais.
    for (const school of SCHOOLS) assert.equal((await request(school, '/healthz')).status, 200);
    for (const s of SCHOOLS) console.log(`Escola Teste ${s.id.slice(-2)}: http://127.0.0.1:${s.port} | admin@${s.id}.local`);
    console.log('Abra em uma aba do navegador externo; a previa do VS Code pode bloquear cookies.');
    console.log('Senha inicial de demonstracao: Teste-escolas-2026! | Somente loopback, sem publicacao na internet.');
  } else if (action === 'verify') await verify();
  else if (action === 'status') compose('ps');
  else if (action === 'stop') compose('stop');
  else if (action === 'logs') compose('logs', '--tail', '100');
}
if (require.main === module) main().catch(error => {console.error(error.message); process.exitCode = 1;});
module.exports = {configuration, SCHOOLS};

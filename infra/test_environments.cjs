const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {render, validate} = require('./generate.cjs');
const manifest = () => ({image: 'ghcr.io/samucau1/edufast-2.0@sha256:' + 'a'.repeat(64), schools: [
  {id: 'escola-a', host: 'a.example.test'}, {id: 'escola-b', host: 'b.example.test'},
]});

test('painel central opcional tem segredo, banco e dominio separados sem acesso as redes escolares', () => {
  const input = manifest(); input.platform = {host:'painel.example.test'};
  const {compose, env, nginx} = render(input);
  const app = compose.services['app-plataforma-central'];
  assert.equal(app.command.at(-1), 'control_plane:create_app()');
  assert.deepEqual(app.networks, ['front-plataforma-central','back-plataforma-central']);
  assert.equal(compose.services['db-plataforma-central'].environment.MYSQL_DATABASE, 'edufast_platform');
  assert.ok(app.environment.PLATFORM_DATABASE_URL.includes('@db-plataforma-central:3306/edufast_platform'));
  assert.equal(app.environment.SECRET_KEY, undefined);
  assert.ok(env.includes('PLATAFORMA_CENTRAL_SECRET_KEY='));
  assert.ok(nginx.includes('server_name painel.example.test;'));
  assert.equal(app.ports, undefined);
  input.platform.host = input.schools[0].host;
  assert.throws(() => render(input));
  input.platform.host = 'painel.example.test'; input.schools[0].id = 'plataforma-central';
  assert.throws(() => render(input));
});

test('isolamento de redes, volumes e credenciais; somente gateway publica porta', () => {
  const {compose, env} = render(manifest());
  assert.deepEqual(compose.services.gateway.ports, ['443:443']);
  for (const id of ['escola-a', 'escola-b']) {
    const app = compose.services[`app-${id}`], db = compose.services[`db-${id}`];
    assert.equal(app.ports, undefined); assert.equal(db.ports, undefined);
    assert.deepEqual(db.networks, [`back-${id}`]);
    assert.deepEqual(app.networks, [`front-${id}`, `back-${id}`]);
    assert.equal(compose.networks[`back-${id}`].internal, true);
    assert.equal(compose.networks[`front-${id}`].internal, true);
    assert.deepEqual(app.volumes, [`uploads-${id}:/app/uploads`]);
    assert.deepEqual(db.volumes, [`mysql-${id}:/var/lib/mysql`]);
    assert.ok(!app.command.join(' ').includes('migrat'));
    assert.equal(app.environment.DB_MAX_OVERFLOW, '0');
  }
  const secrets = env.trim().split('\n').map(line => line.split('=').slice(1).join('='));
  assert.equal(new Set(secrets).size, 8);
  for (const line of env.trim().split('\n').filter(s => s.includes('DATA_ENCRYPTION_KEY')))
    assert.equal(Buffer.from(line.substring(line.indexOf('=') + 1), 'base64url').length, 32);
});

test('rejeita injeção, duplicação e imagens não aprovadas por digest', () => {
  for (const mutate of [
    m => m.schools[0].host = 'x.test; return 200;',
    m => m.schools[0].id = '../outra-escola',
    m => m.schools[1].id = m.schools[0].id,
    m => m.schools[1].host = m.schools[0].host,
    m => m.image = 'edufast:latest',
    m => m.schools = [],
  ]) { const m = manifest(); mutate(m); assert.throws(() => validate(m)); }
});

test('proxy controla rajadas, tamanho, buffering e headers sem cache privado', () => {
  const {nginx} = render(manifest());
  for (const setting of ['limit_req_status 429', 'client_max_body_size 16m',
    'proxy_request_buffering on', 'proxy_max_temp_file_size 0',
    'proxy_next_upstream off', 'proxy_set_header X-Forwarded-For $remote_addr',
    'resolver 127.0.0.11', 'proxy_pass $backend', 'return 444']) assert.ok(nginx.includes(setting));
  assert.ok(!nginx.includes('proxy_cache'));
  assert.ok(!nginx.includes('$request_uri'));
});

test('CLI nunca substitui pasta existente ou seus segredos', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'edufast-env-test-'));
  try {
    const input = path.join(dir, 'manifest.json'), output = path.join(dir, 'generated');
    fs.writeFileSync(input, JSON.stringify(manifest()));
    const run = () => spawnSync(process.execPath, [path.join(__dirname, 'generate.cjs'), input, output], {encoding: 'utf8'});
    assert.equal(run().status, 0);
    const before = fs.readFileSync(path.join(output, '.env'), 'utf8');
    assert.notEqual(run().status, 0);
    assert.equal(fs.readFileSync(path.join(output, '.env'), 'utf8'), before);
    assert.equal(fs.existsSync(path.join(output, 'tls')), true);
  } finally { fs.rmSync(dir, {recursive: true, force: true}); }
});

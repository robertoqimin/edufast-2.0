const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {init, add, list, operation} = require('./platform.cjs');
const image = 'ghcr.io/samucau1/edufast-2.0@sha256:' + 'a'.repeat(64);
function fixture(t) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'edufast-operator-'));
  t.after(() => fs.rmSync(temp, {recursive: true, force: true}));
  const root = path.join(temp, 'private');
  init(root, 'edufast-nuvem', image);
  return {temp, root};
}

test('cadastro de duas escolas preserva segredos, servicos e volumes da primeira', t => {
  const {root} = fixture(t);
  assert.equal(list(root).schools.length, 0);
  const first = add(root, 'teste01', 'teste01.example.test');
  const env = fs.readFileSync(path.join(first.revision, '.env'), 'utf8');
  const before = JSON.parse(fs.readFileSync(path.join(first.revision, 'compose.json')));
  const second = add(root, 'teste02', 'teste02.example.test');
  assert.ok(fs.readFileSync(path.join(second.revision, '.env'), 'utf8').startsWith(env));
  const after = JSON.parse(fs.readFileSync(path.join(second.revision, 'compose.json')));
  for (const service of ['app-teste01', 'db-teste01']) assert.deepEqual(after.services[service], before.services[service]);
  for (const volume of Object.keys(before.volumes)) assert.deepEqual(after.volumes[volume], before.volumes[volume]);
  assert.equal(list(root).schools.length, 2);
  assert.equal(list(root).revision, second.revision);
  assert.equal(first.url, 'https://teste01.example.test/login');
  assert.ok(!JSON.stringify(list(root)).includes('PASSWORD'));
});

test('duplicatas e injecoes nao mudam a revisao nem criam arquivos', t => {
  const {root} = fixture(t);
  add(root, 'teste01', 'teste01.example.test');
  const before = fs.readFileSync(path.join(root, 'platform.json'), 'utf8');
  const files = fs.readdirSync(root);
  for (const [id, host] of [['teste01', 'outra.example.test'], ['teste02', 'teste01.example.test'],
    ['../escape', 'outra.example.test'], ['teste02', 'host;comando']]) {
    assert.throws(() => add(root, id, host));
    assert.equal(fs.readFileSync(path.join(root, 'platform.json'), 'utf8'), before);
    assert.deepEqual(fs.readdirSync(root), files);
  }
  assert.throws(() => init(root, 'edufast-nuvem', image));
});

test('lock impede cadastro e operacao concorrentes; falta de segredo preserva estado', t => {
  const {root} = fixture(t);
  const first = add(root, 'teste01', 'teste01.example.test');
  fs.writeFileSync(path.join(root, '.operator-lock'), 'operador');
  assert.throws(() => add(root, 'teste02', 'teste02.example.test'), /andamento/);
  assert.throws(() => operation(root, 'database', 'teste01'), /andamento/);
  fs.unlinkSync(path.join(root, '.operator-lock'));
  fs.writeFileSync(path.join(first.revision, '.env'), '');
  assert.throws(() => add(root, 'teste02', 'teste02.example.test'), /Segredo/);
  assert.equal(list(root).revision, first.revision);
  assert.equal(fs.existsSync(path.join(root, '.operator-lock')), false);
});

test('adota revisao existente sem regenerar segredos; rejeita projeto diferente', t => {
  const {root, temp} = fixture(t);
  const first = add(root, 'teste01', 'teste01.example.test');
  const before = fs.readFileSync(path.join(first.revision, '.env'), 'utf8');
  const adopted = path.join(temp, 'adopted');
  assert.throws(() => init(adopted, 'edufast-outro', image, first.revision));
  assert.equal(fs.existsSync(adopted), false);
  init(adopted, 'edufast-nuvem', image, first.revision);
  assert.equal(list(adopted).schools.length, 1);
  const next = add(adopted, 'teste02', 'teste02.example.test');
  assert.ok(fs.readFileSync(path.join(next.revision, '.env'), 'utf8').startsWith(before));
});

test('primeiro admin usa CLI interativa e somente o container escolhido, sem SQL', t => {
  const {root} = fixture(t);
  assert.throws(() => operation(root, 'create-admin', 'teste01'));
  add(root, 'teste01', 'teste01.example.test');
  add(root, 'teste02', 'teste02.example.test');
  const plan = operation(root, 'create-admin', 'teste01');
  assert.deepEqual(plan[0].argv.slice(-6), ['exec', 'app-teste01', 'flask', '--app', 'app:create_app()', 'create-admin']);
  const calls = [];
  operation(root, 'create-admin', 'teste01', true, (exe, argv, options) => {
    assert.equal(exe, 'docker'); assert.equal(options.shell, false);
    calls.push(argv); return {status: 0};
  });
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[0].slice(-2), ['config', '--quiet']);
  assert.ok(!JSON.stringify(calls).includes('app-teste02'));
  for (const action of ['migrate', 'destroy', 'shell']) assert.throws(() => operation(root, action, 'teste01'));
  assert.throws(() => operation(root, 'create-admin', 'inexistente'));
  let executed = 0;
  assert.throws(() => operation(root, 'start', 'teste01', true, () => {executed++; return {status: 1};}));
  assert.equal(executed, 1);
});

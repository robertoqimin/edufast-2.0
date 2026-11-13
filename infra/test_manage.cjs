const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {prepare, commands, execute, backup} = require('./manage.cjs');
const image = n => 'ghcr.io/samucau1/edufast-2.0@sha256:' + n.repeat(64);
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'edufast-fleet-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const input = path.join(root, 'manifest.json');
  const manifest = {project: 'edufast-piloto', image: image('a'), schools: [
    {id: 'cliente-a', host: 'a.example.test'}, {id: 'cliente-b', host: 'b.example.test'},
  ]};
  const write = () => fs.writeFileSync(input, JSON.stringify(manifest));
  write();
  const first = prepare(input, path.join(root, 'r1'));
  return {root, first, input, manifest, write};
}

test('adicionar painel central preserva escolas e revisoes seguintes preservam a chave central', t => {
  const f = fixture(t);
  f.manifest.platform = {host:'painel.example.test'}; f.write();
  const second = prepare(f.input,path.join(f.root,'r2'),f.first);
  const before = fs.readFileSync(path.join(second,'.env'),'utf8');
  f.manifest.image = image('b'); f.write();
  const third = prepare(f.input,path.join(f.root,'r3'),second);
  assert.equal(fs.readFileSync(path.join(third,'.env'),'utf8'),before);
  assert.equal(read(path.join(third,'inventory.json')).platform.image,image('a'));
  assert.deepEqual(commands(third,'start','plataforma-central')[0].slice(-5),['up','-d','--no-deps','--wait','app-plataforma-central']);
  delete f.manifest.platform; f.write();
  assert.throws(()=>prepare(f.input,path.join(f.root,'r4'),third));
});

test('adicionar cliente preserva todos os segredos, volumes, TLS e projeto anteriores', t => {
  const f = fixture(t);
  const before = fs.readFileSync(path.join(f.first, '.env'), 'utf8');
  f.manifest.schools.push({id: 'cliente-c', host: 'c.example.test'}); f.write();
  const next = prepare(f.input, path.join(f.root, 'r2'), f.first);
  assert.ok(fs.readFileSync(path.join(next, '.env'), 'utf8').startsWith(before));
  const old = read(path.join(f.first, 'compose.json')), current = read(path.join(next, 'compose.json'));
  for (const id of ['cliente-a', 'cliente-b']) {
    assert.deepEqual(current.services[`app-${id}`], old.services[`app-${id}`]);
    assert.deepEqual(current.services[`db-${id}`], old.services[`db-${id}`]);
  }
  assert.equal(current.name, old.name);
  assert.deepEqual(current.services.gateway.volumes, old.services.gateway.volumes);
  assert.equal(Object.keys(current.volumes).length, 6);
  assert.throws(() => prepare(f.input, next, f.first));
  assert.equal(fs.readFileSync(path.join(f.first, '.env'), 'utf8'), before);
});

test('release explicita atualiza so A; novo default nao atualiza B', t => {
  const f = fixture(t);
  f.manifest.image = image('b');
  f.manifest.schools[0].image = image('c'); f.write();
  const next = prepare(f.input, path.join(f.root, 'r2'), f.first);
  const current = read(path.join(next, 'compose.json'));
  assert.equal(current.services['app-cliente-a'].image, image('c'));
  assert.equal(current.services['app-cliente-b'].image, image('a'));
  const list = commands(next, 'update', 'cliente-a');
  assert.deepEqual(list.map(c => c.slice(7)), [
    ['pull', 'app-cliente-a'], ['up', '-d', '--no-deps', '--wait', 'app-cliente-a'],
  ]);
  assert.ok(!JSON.stringify(list).includes('db-cliente'));
});

test('recusa remocao, troca de dominio/projeto e perda de chave sem escrever nova revisao', t => {
  for (const mutation of [
    f => f.manifest.schools.pop(), f => f.manifest.schools[0].host = 'outro.example.test',
    f => f.manifest.project = 'edufast-outro',
    f => fs.writeFileSync(path.join(f.first, '.env'), ''),
    f => f.manifest.schools[0].image = 'malicioso:latest',
  ]) {
    const f = fixture(t); mutation(f); f.write();
    const destination = path.join(f.root, 'r2');
    assert.throws(() => prepare(f.input, destination, f.first));
    assert.equal(fs.existsSync(destination), false);
  }
});

test('operacao rejeita cliente/acao invalidos, gateway sem TLS e interrompe ao falhar', t => {
  const f = fixture(t);
  assert.throws(() => commands(f.first, 'update', '../outro'));
  assert.throws(() => commands(f.first, 'destroy', 'cliente-a'));
  assert.throws(() => commands(f.first, 'gateway'));
  for (const name of ['fullchain.pem', 'privkey.pem']) fs.writeFileSync(path.join(f.first, 'tls', name), 'fixture');
  const gateway = commands(f.first, 'gateway');
  assert.deepEqual(gateway[0].slice(-2), ['nginx', '-t']);
  let calls = 0;
  assert.throws(() => execute(gateway, () => { calls++; return {status: 1}; }));
  assert.equal(calls, 1);
});

test('backup pausa somente A, captura dados e chave local, retoma e marca conclusao', t => {
  const f = fixture(t), calls = [];
  const runner = (exe, args, options) => {
    assert.equal(exe, 'docker'); assert.equal(options.shell, false); calls.push(args);
    if (options.encoding) return {status: 0, stdout: 'app-cliente-a\n'};
    if (Array.isArray(options.stdio)) fs.writeSync(options.stdio[1], 'conteudo-de-teste');
    return {status: 0};
  };
  const destination = path.join(f.root, 'backup');
  backup(f.first, 'cliente-a', destination, runner);
  assert.ok(fs.existsSync(path.join(destination, 'COMPLETE')));
  const env = fs.readFileSync(path.join(destination, '.env'), 'utf8');
  assert.equal(env.trim().split('\n').length, 4);
  assert.ok(!env.includes('CLIENTE_B'));
  assert.deepEqual(calls[1].slice(-2), ['stop', 'app-cliente-a']);
  assert.deepEqual(calls.at(-1).slice(-2), ['start', 'app-cliente-a']);
  assert.ok(!JSON.stringify(calls).includes('cliente-b'));
});

test('backup que falha retoma app e nao produz marcador de conclusao', t => {
  const f = fixture(t), calls = [];
  const runner = (exe, args, options) => {
    calls.push(args);
    return {status: args.includes('mysqldump') || args.includes('exec') ? 1 : 0, stdout: options.encoding ? 'app-cliente-a\n' : ''};
  };
  const destination = path.join(f.root, 'backup');
  assert.throws(() => backup(f.first, 'cliente-a', destination, runner));
  assert.deepEqual(calls.at(-1).slice(-2), ['start', 'app-cliente-a']);
  assert.equal(fs.existsSync(path.join(destination, 'COMPLETE')), false);
});

test('backup de A nao inclui segredos de cliente com prefixo A-B e nao religa app parado', t => {
  const f = fixture(t);
  f.manifest.schools.push({id: 'cliente-a-extra', host: 'extra.example.test'}); f.write();
  const next = prepare(f.input, path.join(f.root, 'r2'), f.first), calls = [];
  const runner = (exe, args, options) => {
    calls.push(args);
    if (Array.isArray(options.stdio)) fs.writeSync(options.stdio[1], 'fixture');
    return {status: 0, stdout: ''};
  };
  const destination = path.join(f.root, 'backup');
  backup(next, 'cliente-a', destination, runner);
  assert.ok(!fs.readFileSync(path.join(destination, '.env'), 'utf8').includes('EXTRA'));
  assert.equal(calls.some(c => c.includes('stop') || c.includes('start')), false);
});

// Somente recursos descartáveis com UUID; nunca usar configuração de produção.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const https = require('node:https');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {prepare, backup} = require('./manage.cjs');

async function main() {
  const image = fs.readFileSync('.ci-results/image.txt', 'utf8').trim();
  if (!/^edufast-ci-[a-f0-9]{10}:tested$/.test(image)) throw new Error('Use somente a imagem local aprovada pelo executor CI.');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'edufast-cloud-smoke-'));
  const project = 'edufast-smoke-' + crypto.randomBytes(6).toString('hex');
  const manifest = path.join(root, 'manifest.json'), dir = path.join(root, 'revision');
  fs.writeFileSync(manifest, JSON.stringify({project,
    image: 'ghcr.io/samucau1/edufast-2.0@sha256:' + 'a'.repeat(64),
    schools: [{id: 'cliente-a', host: 'a.example.test'}, {id: 'cliente-b', host: 'b.example.test'}],
  }));
  prepare(manifest, dir);
  const composeFile = path.join(dir, 'compose.json');
  const config = JSON.parse(fs.readFileSync(composeFile, 'utf8'));
  // Override exclusivamente neste diretório temporário, sem fingir digest publicado.
  for (const id of ['cliente-a', 'cliente-b']) config.services[`app-${id}`].image = image;
  config.services.gateway.ports = ['127.0.0.1::443'];
  fs.writeFileSync(composeFile, JSON.stringify(config));
  const base = ['compose', '-p', project, '--env-file', path.join(dir, '.env'), '-f', composeFile];
  function run(exe, args, options = {}) {
    const result = spawnSync(exe, args, {encoding: 'utf8', timeout: 240000, maxBuffer: 4 * 1024 * 1024, ...options});
    if (result.error || result.status !== 0) throw new Error(`Falha em ${exe} ${args.slice(0, 2).join(' ')}: ${result.stderr || result.error || result.status}`);
    return result.stdout;
  }
  const docker = (...args) => run('docker', [...base, ...args]);
  try {
    run('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=a.example.test',
      '-addext', 'subjectAltName=DNS:a.example.test,DNS:b.example.test',
      '-keyout', path.join(dir, 'tls/privkey.pem'), '-out', path.join(dir, 'tls/fullchain.pem')]);
    docker('up', '-d', '--wait', '--wait-timeout', '180', 'db-cliente-a', 'db-cliente-b');
    for (const id of ['cliente-a', 'cliente-b']) {
      // Metadata cria apenas os bancos novos descartáveis deste teste; não é migration.
      docker('run', '--rm', '--no-deps', '-T', '--entrypoint', 'python', `app-${id}`, '-c',
        "from app.database import Base,engine,get_session; from app import models; from app.models import UsuarioModel; from werkzeug.security import generate_password_hash; Base.metadata.create_all(engine); s=get_session(); s.add(UsuarioModel(email='admin@example.test',senha=generate_password_hash('synthetic-password-123'),tipo='admin')); s.commit(); s.close()");
    }
    docker('up', '-d', '--wait', '--wait-timeout', '180');
    const port = Number(docker('port', 'gateway', '443').trim().split(':').at(-1));
    const ca = fs.readFileSync(path.join(dir, 'tls/fullchain.pem'));
    const request = (host, route, method = 'GET', body, headers = {}) => new Promise((resolve, reject) => {
      const data = body ? JSON.stringify(body) : undefined;
      const req = https.request({hostname: host, port, servername: host, ca,
        lookup: (hostname, options, callback) => options.all
          ? callback(null, [{address: '127.0.0.1', family: 4}]) : callback(null, '127.0.0.1', 4),
        path: route, method, timeout: 15000,
        headers: {...(data ? {'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data)} : {}), ...headers}}, res => {
        let text = ''; res.on('data', chunk => text += chunk);
        res.on('end', () => resolve({status: res.statusCode, headers: res.headers, text}));
      });
      req.on('error', reject); req.on('timeout', () => req.destroy(new Error('Timeout HTTPS')));
      req.end(data);
    });
    for (const host of ['a.example.test', 'b.example.test']) assert.equal((await request(host, '/healthz')).status, 200);
    const login = await request('a.example.test', '/login', 'POST', {email: 'admin@example.test', senha: 'synthetic-password-123'});
    assert.equal(login.status, 200);
    const token = JSON.parse(login.text).token;
    assert.equal((await request('a.example.test', '/alunos/busca?q=teste', 'GET', null, {Authorization: `Bearer ${token}`})).status, 200);
    assert.ok([401, 403].includes((await request('b.example.test', '/alunos/busca?q=teste', 'GET', null, {Authorization: `Bearer ${token}`})).status));
    const cookie = login.headers['set-cookie'].map(value => value.split(';')[0]).join('; ');
    assert.equal((await request('a.example.test', '/admin/dashboard', 'GET', null, {Cookie: cookie})).status, 200);
    assert.ok([401, 403].includes((await request('b.example.test', '/admin/dashboard', 'GET', null, {Cookie: cookie})).status));
    docker('exec', '-T', 'app-cliente-a', 'python', '-c',
      "import socket; blocked=False\ntry:\n socket.create_connection(('db-cliente-b',3306),timeout=3).close()\nexcept OSError:\n blocked=True\nassert blocked, 'MySQL B acessivel por A'");
    docker('exec', '-T', 'app-cliente-a', 'python', '-c', "from pathlib import Path; Path('/app/uploads/probe.txt').write_text('cliente-a')");
    const beforeB = docker('ps', '-q', 'app-cliente-b').trim();
    backup(dir, 'cliente-a', path.join(root, 'backup'));
    assert.ok(fs.existsSync(path.join(root, 'backup/COMPLETE')));
    assert.ok(fs.readFileSync(path.join(root, 'backup/database.sql'), 'utf8').includes('admin@example.test'));
    assert.equal((await request('b.example.test', '/healthz')).status, 200);
    docker('up', '-d', '--no-deps', '--force-recreate', '--wait', 'app-cliente-a');
    assert.equal(docker('exec', '-T', 'app-cliente-a', 'cat', '/app/uploads/probe.txt').trim(), 'cliente-a');
    assert.equal(docker('ps', '-q', 'app-cliente-b').trim(), beforeB);
    assert.equal((await request('b.example.test', '/healthz')).status, 200);
    console.log('Piloto sintetico: HTTPS, login, rejeicao cruzada de JWT/cookie, rede MySQL, backup e persistencia aprovados.');
  } finally {
    // UUID criado acima; nunca recebe nome de projeto ou diretório externo.
    docker('down', '-v', '--remove-orphans');
    fs.rmSync(root, {recursive: true, force: true});
  }
}
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });

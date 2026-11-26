// C1 — demonstração única: escola fictícia completa (porta 5095) + painel Supremo (5093).
// Uso: node infra/demo-completa.cjs start | stop | status | reset   [--sem-supremo]
// Projeto, banco e volumes próprios (edufast-demo-completa); nunca toca nos bancos persistentes.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const PROJECT = 'edufast-demo-completa';
const DIR = path.join(ROOT, '.ci-results', 'demo-completa');
const ENV = path.join(DIR, '.env');
const PORTA = 5095;
const URL = `http://localhost:${PORTA}`;
const COMPOSE = ['compose', '--project-name', PROJECT, '--env-file', ENV,
  '-f', 'api/docker-compose.yml', '-f', 'scripts/compose.manual.yml'];

function docker(args, {captura = false, permitirFalha = false, entrada} = {}) {
  const r = spawnSync('docker', args, {cwd: ROOT, encoding: 'utf8', input: entrada,
    env: {...process.env, EDUFAST_MANUAL_PORT: String(PORTA)}, stdio: captura ? 'pipe' : ['pipe', 'inherit', 'inherit']});
  if (r.error) throw new Error('Docker indisponível. Abra o Docker Desktop e repita.');
  if (r.status !== 0 && !permitirFalha) throw new Error(`Falhou: docker ${args.slice(-4).join(' ')}`);
  return r;
}

function configurar() {
  fs.mkdirSync(DIR, {recursive: true});
  if (fs.existsSync(ENV)) return;
  const segredo = () => crypto.randomBytes(24).toString('base64url');
  fs.writeFileSync(ENV, [`SECRET_KEY=${segredo()}${segredo()}`, `DB_PASSWORD=${segredo()}`, `POSTGRES_ADMIN_PASSWORD=${segredo()}`,
    `DATA_ENCRYPTION_KEY=${crypto.randomBytes(32).toString('base64url')}=`, 'DB_NAME=edufast_demo_completa',
    'DB_USER=edufast_demo', 'DB_PORT=5432', ''].join('\n'), {flag: 'wx', mode: 0o600});
}

async function pronto() {
  for (let i = 0; i < 60; i++) {
    try { if ((await fetch(URL + '/healthz')).ok) return; } catch { /* aguardando */ }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`A escola não respondeu em ${URL}. Veja: docker ${COMPOSE.slice(0, 4).join(' ')} logs app`);
}

async function start(semSupremo) {
  configurar();
  docker([...COMPOSE, 'build', 'app'], {captura: true});
  docker([...COMPOSE, 'up', '-d', '--wait', '--wait-timeout', '180', 'db'], {captura: true});
  console.log('Preparando a escola de demonstração (só na primeira vez)...');
  const seed = docker([...COMPOSE, 'run', '--rm', '--no-deps', '-T', '-e', 'EDUFAST_DEMO_COMPLETA=1',
    '--entrypoint', 'python', 'app', 'demo_completa.py'], {captura: true, permitirFalha: true});
  const saida = (seed.stdout || '') + (seed.stderr || '');
  if (seed.status !== 0 && !saida.includes('já tem dados')) {
    console.error(saida.slice(-2000));
    throw new Error('Não foi possível preparar a escola de demonstração.');
  }
  docker([...COMPOSE, 'up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'app'], {captura: true});
  await pronto();
  if (!semSupremo) {
    const r = spawnSync(process.execPath, [path.join(__dirname, 'platform-demo.cjs'), 'start'], {cwd: ROOT, encoding: 'utf8'});
    if (r.status !== 0) console.warn('Aviso: o painel Supremo não subiu. Rode: node infra/platform-demo.cjs start');
  }
  console.log(`
DEMONSTRAÇÃO EDUFAST — somente dados fictícios
  Escola (Colégio Horizonte): ${URL}
  Painel Supremo:            ${semSupremo ? '(não iniciado)' : 'http://127.0.0.1:5093/login'}

  Perfil                         E-mail                                  Senha
  Supremo (dono da plataforma)   dono@plataforma.local                   Plataforma-teste-2026!
  Super admin (direção)          diretoria@demo.edufast.test             Demo-EduFast-2026!
  Admin (secretaria)             secretaria@demo.edufast.test            Demo-EduFast-2026!
  Professora de Matemática       ana.ribeiro@demo.edufast.test           Demo-EduFast-2026!
  Professor de Língua Portuguesa carlos.mendes@demo.edufast.test         Demo-EduFast-2026!
  Professora de Biologia         beatriz.lopes@demo.edufast.test         Demo-EduFast-2026!
  Aluno / Aluna                  bruno.lima@demo.edufast.test            Demo-EduFast-2026!
                                 carla.souza@demo.edufast.test           Demo-EduFast-2026!

  Parar mantém os dados; "reset" recria a escola do zero.`);
}

function stop() {
  if (fs.existsSync(ENV)) docker([...COMPOSE, 'stop'], {captura: true, permitirFalha: true});
  spawnSync(process.execPath, [path.join(__dirname, 'platform-demo.cjs'), 'stop'], {cwd: ROOT, stdio: 'ignore'});
  console.log('Demonstração parada. Os dados da escola foram mantidos.');
}

(async () => {
  const [acao, ...opcoes] = process.argv.slice(2);
  const semSupremo = opcoes.includes('--sem-supremo');
  if (!['start', 'stop', 'status', 'reset'].includes(acao)) throw new Error('Uso: node infra/demo-completa.cjs start|stop|status|reset [--sem-supremo]');
  if (acao === 'stop') return stop();
  if (acao === 'status') { configurar(); docker([...COMPOSE, 'ps']); return; }
  if (acao === 'reset') {
    if (fs.existsSync(ENV)) docker([...COMPOSE, 'down', '-v'], {captura: true, permitirFalha: true});
    console.log('Escola de demonstração apagada; recriando do zero.');
  }
  await start(semSupremo);
})().catch((e) => { console.error(e.message); process.exitCode = 1; });

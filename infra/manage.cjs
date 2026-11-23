// Operação explícita por cliente. Nunca cria esquema, executa SQL ou apaga volumes.
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {render, validate, clients} = require('./generate.cjs');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));

function load(directory) {
  const dir = path.resolve(directory);
  const inventory = read(path.join(dir, 'inventory.json'));
  validate(inventory);
  if (!/^edufast-[a-z][a-z0-9-]{1,40}$/.test(inventory.project)) throw new Error('Projeto deve usar edufast- seguido de ID estavel.');
  return {dir, inventory};
}

function prepare(manifestFile, output, previous) {
  const inventory = read(manifestFile);
  validate(inventory);
  if (!/^edufast-[a-z][a-z0-9-]{1,40}$/.test(inventory.project)) throw new Error('Informe project estavel: edufast-<instalacao>.');
  let saved = '';
  let tls = path.join(path.resolve(output), 'tls');
  if (previous) {
    const old = load(previous);
    if (old.inventory.project !== inventory.project) throw new Error('Nao alterar projeto: isso troca os volumes.');
    if (old.inventory.platform) {
      if (!inventory.platform || inventory.platform.host !== old.inventory.platform.host)
        throw new Error('Nao remover ou trocar dominio da plataforma sem plano de transferencia.');
      inventory.platform.image ??= old.inventory.platform.image ?? old.inventory.image;
    }
    for (const school of old.inventory.schools) {
      const next = inventory.schools.find(s => s.id === school.id);
      if (!next || next.host !== school.host) throw new Error('Remocao, troca de ID ou dominio exige plano de transferencia separado.');
      // Alterar o default so afeta novos clientes; existentes mudam explicitamente.
      next.image ??= school.image ?? old.inventory.image;
    }
    saved = fs.readFileSync(path.join(old.dir, '.env'), 'utf8');
    for (const {id} of clients(old.inventory)) {
      for (const name of ['SECRET_KEY', 'DATA_ENCRYPTION_KEY', 'DB_PASSWORD', 'ROOT_PASSWORD']) {
        const key = `${id.toUpperCase().replaceAll('-', '_')}_${name}=`;
        if (!saved.split(/\r?\n/).some(line => line.startsWith(key))) throw new Error('Segredo anterior ausente; recuperacao necessaria.');
      }
    }
    tls = old.inventory.tls;
  }
  for (const school of inventory.schools) school.image ??= inventory.image;
  if (inventory.platform) inventory.platform.image ??= inventory.image;
  const generated = render(inventory, saved);
  generated.compose.name = inventory.project;
  generated.compose.services.gateway.volumes[1] = {type: 'bind', source: tls, target: '/etc/nginx/tls', read_only: true};
  const dir = path.resolve(output);
  // Diretório imutável: nenhuma substituição de configuração ou segredos em uso.
  fs.mkdirSync(dir, {mode: 0o700});
  if (!previous) fs.mkdirSync(tls, {mode: 0o700});
  for (const [name, data] of Object.entries({
    'compose.json': JSON.stringify(generated.compose, null, 2) + '\n',
    'nginx.conf': generated.nginx,
    '.env': generated.env,
    'inventory.json': JSON.stringify({...inventory, tls}, null, 2) + '\n',
  })) fs.writeFileSync(path.join(dir, name), data, {flag: 'wx', mode: 0o600});
  return dir;
}

function commands(directory, action, client) {
  const {dir, inventory} = load(directory);
  const base = ['compose', '-p', inventory.project, '--env-file', path.join(dir, '.env'), '-f', path.join(dir, 'compose.json')];
  if (action === 'validate') return [[...base, 'config', '--quiet']];
  if (action === 'gateway') {
    for (const file of ['fullchain.pem', 'privkey.pem']) {
      if (!fs.existsSync(path.join(inventory.tls, file))) throw new Error('Instale certificado e chave TLS antes de iniciar gateway.');
    }
    return [[...base, 'run', '--rm', '--no-deps', 'gateway', 'nginx', '-t'],
      [...base, 'up', '-d', '--no-deps', '--force-recreate', 'gateway']];
  }
  if (!clients(inventory).some(s => s.id === client)) throw new Error('Cliente ausente do inventario.');
  const app = `app-${client}`, db = `db-${client}`;
  const actions = {
    database: [['up', '-d', '--wait', db]],
    start: [['up', '-d', '--no-deps', '--wait', app]],
    update: [['pull', app], ['up', '-d', '--no-deps', '--wait', app]],
    stop: [['stop', app]],
    status: [['ps', app, db]],
    logs: [['logs', '--tail', '100', app]],
  };
  if (!actions[action]) throw new Error('Acao invalida. Use validate, database, start, update, stop, status, logs ou gateway.');
  return actions[action].map(args => [...base, ...args]);
}

function execute(list, runner = spawnSync) {
  for (const args of list) {
    const result = runner('docker', args, {stdio: 'inherit', shell: false});
    if (result.error || result.status !== 0) throw new Error('Docker falhou; operacao interrompida. Verifique saude e esquema; nenhum rollback de banco foi executado.');
  }
}

function backup(directory, client, output, runner = spawnSync) {
  const {dir, inventory} = load(directory);
  const school = clients(inventory).find(s => s.id === client);
  if (!school) throw new Error('Cliente ausente do inventario.');
  const base = commands(directory, 'validate')[0].slice(0, -2);
  const app = `app-${client}`, db = `db-${client}`;
  const destination = path.resolve(output);
  fs.mkdirSync(destination, {mode: 0o700});
  const check = runner('docker', [...base, 'ps', '--status', 'running', '--services', app], {encoding: 'utf8', shell: false});
  if (check.error || check.status !== 0) throw new Error('Nao foi possivel verificar estado da aplicacao.');
  const running = check.stdout.trim().split(/\r?\n/).includes(app);
  let stopped = false;
  const capture = (filename, argv) => {
    const fd = fs.openSync(path.join(destination, filename), 'wx', 0o600);
    try {
      const result = runner('docker', argv, {stdio: ['ignore', fd, 'inherit'], shell: false});
      if (result.error || result.status !== 0) throw new Error('Backup incompleto; nao usar para recuperacao.');
    } finally { fs.closeSync(fd); }
  };
  try {
    if (running) { execute([[...base, 'stop', app]], runner); stopped = true; }
    capture('database.sql', [...base, 'exec', '-T', db, 'sh', '-c',
      'PGPASSWORD="$APP_DB_PASSWORD" exec pg_dump -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges']);
    capture('uploads.tar.gz', [...base, 'run', '--rm', '--no-deps', '-T', '--entrypoint', 'tar', app,
      '-C', '/app/uploads', '-czf', '-', '.']);
    const prefix = client.toUpperCase().replaceAll('-', '_') + '_';
    const keys = new Set(['SECRET_KEY', 'DATA_ENCRYPTION_KEY', 'DB_PASSWORD', 'ROOT_PASSWORD'].map(name => prefix + name));
    const lines = fs.readFileSync(path.join(dir, '.env'), 'utf8').split(/\r?\n/).filter(line => keys.has(line.slice(0, line.indexOf('='))));
    if (lines.length !== 4) throw new Error('Backup incompleto: segredos do cliente ausentes.');
    const env = lines.join('\n') + '\n';
    fs.writeFileSync(path.join(destination, '.env'), env, {flag: 'wx', mode: 0o600});
    fs.writeFileSync(path.join(destination, 'metadata.json'), JSON.stringify({
      project: inventory.project, school, createdAt: new Date().toISOString(),
      note: 'Restaurar somente em destino isolado apos revisao. Segredos em texto: criptografar e transferir para armazenamento privado fora do host.',
    }, null, 2) + '\n', {flag: 'wx', mode: 0o600});
  } finally {
    // start reutiliza o container existente, sem aplicar outra imagem/configuracao.
    if (stopped) execute([[...base, 'start', app]], runner);
  }
  // Marcador so existe se captura E retomada terminaram sem falha.
  fs.writeFileSync(path.join(destination, 'COMPLETE'), 'Backup local concluido; criptografar, copiar para fora do host e ensaiar restauracao.\n', {flag: 'wx', mode: 0o600});
}

if (require.main === module) {
  try {
    const [mode, ...args] = process.argv.slice(2);
    if (mode === 'prepare' && (args.length === 2 || args.length === 3)) {
      prepare(...args);
      console.log('Configuracao preparada. Revise release, TLS e esquema antes de executar.');
    } else if (mode === 'backup' && args.length === 3) {
      backup(...args);
      console.log('Backup local concluido. Proteja os segredos e transfira para fora do host.');
    } else if (['plan', 'run'].includes(mode) && args.length >= 2 && args.length <= 3) {
      const list = commands(...args);
      if (mode === 'plan') console.log(JSON.stringify(list.map(argv => ({executable: 'docker', argv})), null, 2));
      else {
        if (args[1] !== 'validate') execute(commands(args[0], 'validate'));
        execute(list);
      }
    } else throw new Error('Uso: prepare manifesto saida [anterior] | plan/run diretorio acao [cliente] | backup diretorio cliente saida-nova');
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
module.exports = {prepare, commands, execute, backup};

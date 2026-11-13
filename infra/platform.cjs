// Administração exclusiva pelo acesso SSH do operador. Sem servidor HTTP ou SQL.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {validate} = require('./generate.cjs');
const {prepare, commands, execute} = require('./manage.cjs');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const write = (file, data) => fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', {flag: 'wx', mode: 0o600});

function settings(project, image) {
  if (!/^edufast-[a-z][a-z0-9-]{1,40}$/.test(project)) throw new Error('Projeto invalido.');
  validate({image, schools: [{id: 'validacao', host: 'validacao.example.test'}]});
}

function init(root, project, image, previous) {
  settings(project, image);
  let current = null;
  if (previous) {
    current = path.resolve(previous);
    const inventory = read(path.join(current, 'inventory.json'));
    validate(inventory);
    if (inventory.project !== project) throw new Error('Projeto anterior diferente.');
    // Verificar a presença dos segredos antes de adotar; nunca regenerar aqui.
    fs.accessSync(path.join(current, '.env'), fs.constants.R_OK);
  }
  fs.mkdirSync(root, {mode: 0o700});
  write(path.join(root, 'platform.json'), {version: 1, project, image, current});
}

function load(root) {
  const state = read(path.join(root, 'platform.json'));
  if (state.version !== 1) throw new Error('Versao de cadastro desconhecida.');
  settings(state.project, state.image);
  const inventory = state.current ? read(path.join(state.current, 'inventory.json')) : null;
  if (inventory) {
    validate(inventory);
    if (inventory.project !== state.project) throw new Error('Inventario pertence a outro projeto.');
  }
  return {state, schools: inventory?.schools ?? []};
}

function locked(root, callback) {
  const file = path.join(root, '.operator-lock');
  let fd;
  try { fd = fs.openSync(file, 'wx', 0o600); }
  catch (error) {
    if (error.code === 'EEXIST') throw new Error('Outra operacao esta em andamento. Se houve interrupcao, revise antes de remover .operator-lock.');
    throw error;
  }
  try { fs.writeSync(fd, String(process.pid)); return callback(); }
  finally { fs.closeSync(fd); fs.unlinkSync(file); }
}

function add(root, id, host) {
  return locked(root, () => {
    const {state, schools} = load(root);
    const manifest = {project: state.project, image: state.image, schools: [...schools, {id, host}]};
    validate(manifest); // Duplicatas e entradas inválidas não criam revisão nem segredos.
    const revision = crypto.randomUUID();
    const input = path.join(root, `request-${revision}.json`);
    const output = path.resolve(root, `revision-${revision}`);
    const pending = path.join(root, `state-${revision}.json`);
    write(input, manifest);
    try {
      prepare(input, output, state.current || undefined);
      write(pending, {...state, current: output});
      // Só promover após preparar tudo. Em falha, a revisão anterior continua vigente.
      fs.renameSync(pending, path.join(root, 'platform.json'));
    } finally {
      fs.unlinkSync(input);
    }
    return {id, url: `https://${host}/login`, revision: output, status: 'preparada; banco, administrador, DNS e TLS pendentes'};
  });
}

function list(root) {
  const {state, schools} = load(root);
  return {project: state.project, revision: state.current, schools: schools.map(({id, host}) => ({
    id, url: `https://${host}/login`, status: 'configurada; disponibilidade nao verificada',
  }))};
}

function operation(root, action, id, run = false, runner) {
  return locked(root, () => {
    const {state, schools} = load(root);
    if (!state.current) throw new Error('Cadastre uma escola primeiro.');
    const allowed = ['validate', 'database', 'start', 'status', 'logs', 'gateway', 'create-admin'];
    if (!allowed.includes(action)) throw new Error('Acao invalida.');
    let plan;
    if (action === 'create-admin') {
      if (!schools.some(school => school.id === id)) throw new Error('Escola nao cadastrada.');
      const base = commands(state.current, 'validate')[0].slice(0, -2);
      // Credenciais são solicitadas pelo Flask, nunca por argumentos/arquivos do cadastro.
      plan = [[...base, 'exec', `app-${id}`, 'flask', '--app', 'app:create_app()', 'create-admin']];
    } else plan = commands(state.current, action, id);
    if (run) {
      execute(commands(state.current, 'validate'), runner);
      execute(plan, runner);
    }
    return plan.map(argv => ({executable: 'docker', argv}));
  });
}

if (require.main === module) {
  try {
    const [mode, ...args] = process.argv.slice(2);
    let result;
    if (mode === 'init' && [3, 4].includes(args.length)) {
      init(...args); result = {status: 'Administracao preparada; acesso restrito pela conta SSH e permissoes do servidor.'};
    } else if (mode === 'add' && args.length === 3) result = add(...args);
    else if (mode === 'list' && args.length === 1) result = list(...args);
    else if (['plan', 'run'].includes(mode) && [2, 3].includes(args.length)) {
      result = operation(args[0], args[1], args[2], mode === 'run');
    } else throw new Error('Uso: init pasta projeto imagem [revisao-existente] | add pasta id dominio | list pasta | plan/run pasta acao [id]');
    console.log(JSON.stringify(result, null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
module.exports = {init, add, list, operation};

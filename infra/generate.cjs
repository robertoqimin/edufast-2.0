// Gera arquivos revisáveis. Nunca inicia containers ou modifica bancos.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const imagePattern = /^ghcr\.io\/samucau1\/edufast-2\.0@sha256:[a-f0-9]{64}$/;

function validate(input) {
  if (!input || !imagePattern.test(input.image))
    throw new Error('Informe a imagem EduFast por digest aprovado pelo CI.');
  if (!Array.isArray(input.schools) || input.schools.length < 1 || input.schools.length > 50)
    throw new Error('Informe entre 1 e 50 escolas; isto não representa capacidade garantida.');
  const ids = new Set(), hosts = new Set();
  for (const school of input.schools) {
    if (school?.image !== undefined && !imagePattern.test(school.image))
      throw new Error('Imagem do cliente deve usar o repositorio EduFast e digest.');
    if (!school || !/^[a-z][a-z0-9-]{1,30}$/.test(school.id)) throw new Error('ID de escola invalido.');
    if (typeof school.host !== 'string' || school.host.length > 253 ||
        !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$/.test(school.host))
      throw new Error('Host DNS invalido.');
    if (ids.has(school.id) || hosts.has(school.host)) throw new Error('ID ou host duplicado.');
    ids.add(school.id); hosts.add(school.host);
  }
}

function render(input, previousEnv = '') {
  validate(input);
  const compose = {services: {}, networks: {}, volumes: {}};
  const servers = [];
  const env = [];
  const saved = new Map(previousEnv.trim().split(/\r?\n/).filter(Boolean).map(line => {
    const at = line.indexOf('=');
    if (at < 1) throw new Error('Arquivo de segredos invalido.');
    return [line.slice(0, at), line.slice(at + 1)];
  }));
  const gatewayNetworks = [];
  for (const {id, host, image = input.image} of input.schools) {
    const prefix = id.toUpperCase().replaceAll('-', '_');
    const app = `app-${id}`, db = `db-${id}`, front = `front-${id}`, back = `back-${id}`;
    const variable = name => '${' + prefix + '_' + name + ':?Segredo obrigatorio}';
    for (const name of ['SECRET_KEY', 'DATA_ENCRYPTION_KEY', 'DB_PASSWORD', 'ROOT_PASSWORD']) {
      const key = `${prefix}_${name}`;
      const value = saved.get(key) ?? (name === 'DATA_ENCRYPTION_KEY' ? crypto.randomBytes(32).toString('base64url') + '=' : crypto.randomBytes(32).toString('hex'));
      if (!/^[a-zA-Z0-9_=-]{32,128}$/.test(value)) throw new Error('Segredo invalido.');
      env.push(`${key}=${value}`);
    }
    compose.networks[front] = {internal: true};
    compose.networks[back] = {internal: true};
    gatewayNetworks.push(front);
    const uploads = `uploads-${id}`, data = `mysql-${id}`;
    compose.volumes[uploads] = {}; compose.volumes[data] = {};
    compose.services[app] = {
      image, restart: 'unless-stopped',
      command: ['gunicorn', '-c', '/app/gunicorn.conf.py', 'app:create_app()'],
      environment: {
        APP_ENV: 'production', SECRET_KEY: variable('SECRET_KEY'), DATA_ENCRYPTION_KEY: variable('DATA_ENCRYPTION_KEY'),
        TRUSTED_HOSTS: `${host},localhost`, RELEASE_ID: image,
        SESSION_COOKIE_NAME: `edufast_${id.replaceAll('-', '_')}`,
        DB_HOST: db, DB_NAME: 'edufast', DB_USER: 'edufast', DB_PASSWORD: variable('DB_PASSWORD'),
        UPLOAD_FOLDER: '/app/uploads', WEB_WORKERS: '1', WEB_THREADS: '4',
        DB_POOL_SIZE: '4', DB_MAX_OVERFLOW: '0', DB_POOL_TIMEOUT: '5',
      },
      volumes: [`${uploads}:/app/uploads`], networks: [front, back],
      depends_on: {[db]: {condition: 'service_healthy'}},
      healthcheck: {test: ['CMD', 'python', '-c', "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5)"], interval: '15s', timeout: '6s', retries: 8, start_period: '30s'},
      mem_limit: '512m', cpus: '1.0', pids_limit: 128,
      security_opt: ['no-new-privileges:true'], cap_drop: ['ALL'],
      logging: {driver: 'json-file', options: {'max-size': '10m', 'max-file': '3'}},
    };
    compose.services[db] = {
      image: 'mysql:8.4', restart: 'unless-stopped',
      command: ['--max-connections=30', '--innodb-buffer-pool-size=134217728'],
      environment: {MYSQL_DATABASE: 'edufast', MYSQL_USER: 'edufast', MYSQL_PASSWORD: variable('DB_PASSWORD'), MYSQL_ROOT_PASSWORD: variable('ROOT_PASSWORD')},
      volumes: [`${data}:/var/lib/mysql`], networks: [back],
      healthcheck: {test: ['CMD-SHELL', 'MYSQL_PWD=$$MYSQL_PASSWORD mysql --protocol=tcp -h127.0.0.1 -u$$MYSQL_USER $$MYSQL_DATABASE -e "SELECT 1" >/dev/null'], interval: '10s', timeout: '5s', retries: 20, start_period: '30s'},
      mem_limit: '768m', cpus: '1.0', pids_limit: 256,
      security_opt: ['no-new-privileges:true'],
      logging: {driver: 'json-file', options: {'max-size': '10m', 'max-file': '3'}},
    };
    servers.push(`  server {
    listen 443 ssl;
    server_name ${host};
    location / {
      limit_req zone=school burst=100 nodelay;
      limit_req zone=client burst=40 nodelay;
      limit_conn clients 30;
      proxy_pass http://${app}:8000;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-Host $host;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header Connection "";
      proxy_http_version 1.1;
    }
  }`);
  }
  compose.networks.edge = {};
  compose.services.gateway = {
    image: 'nginx:1.30.6-alpine', restart: 'unless-stopped', ports: ['443:443'],
    volumes: ['./nginx.conf:/etc/nginx/nginx.conf:ro', './tls:/etc/nginx/tls:ro'],
    networks: ['edge', ...gatewayNetworks],
    depends_on: Object.fromEntries(input.schools.map(({id}) => [`app-${id}`, {condition: 'service_started'}])),
    mem_limit: '256m', cpus: '1.0', pids_limit: 128,
    tmpfs: ['/var/cache/nginx:size=128m,mode=1777'],
    security_opt: ['no-new-privileges:true'],
    logging: {driver: 'json-file', options: {'max-size': '10m', 'max-file': '3'}},
  };
  const nginx = `events { worker_connections 1024; }
http {
  # Sem URI/query nos logs. Sem cache compartilhado de conteúdo autenticado.
  log_format minimal '$host $request_method $status $request_time';
  access_log /dev/stdout minimal;
  error_log /dev/stderr warn;
  resolver 127.0.0.11 valid=10s ipv6=off;
  limit_req_zone $server_name zone=school:1m rate=100r/s;
  limit_req_zone "$server_name:$binary_remote_addr" zone=client:10m rate=20r/s;
  limit_conn_zone "$server_name:$binary_remote_addr" zone=clients:10m;
  limit_req_status 429;
  limit_conn_status 429;
  client_max_body_size 16m;
  client_body_buffer_size 128k;
  client_body_timeout 15s;
  client_header_timeout 10s;
  large_client_header_buffers 4 8k;
  keepalive_timeout 15s;
  send_timeout 30s;
  proxy_connect_timeout 3s;
  proxy_read_timeout 60s;
  proxy_send_timeout 30s;
  proxy_request_buffering on;
  proxy_buffering on;
  proxy_buffers 8 16k;
  proxy_buffer_size 8k;
  proxy_max_temp_file_size 0;
  proxy_next_upstream off;
  gzip on;
  gzip_min_length 1024;
  gzip_types text/css application/javascript;
  ssl_certificate /etc/nginx/tls/fullchain.pem;
  ssl_certificate_key /etc/nginx/tls/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  add_header Strict-Transport-Security "max-age=31536000" always;
  server { listen 443 ssl default_server; server_name _; return 444; }
${servers.join('\n')}
}
`;
  // Variável no upstream força nova resolução após recriação do container.
  const resolvedNginx = nginx.replace(/proxy_pass http:\/\/(app-[a-z0-9-]+):8000;/g,
    'set $backend http://$1:8000;\n      proxy_pass $backend;');
  return {compose, nginx: resolvedNginx, env: env.join('\n') + '\n'};
}

if (require.main === module) {
  try {
    const [manifest, output] = process.argv.slice(2);
    if (!manifest || !output) throw new Error('Uso: node infra/generate.cjs manifesto.json pasta-nova');
    const result = render(JSON.parse(fs.readFileSync(manifest, 'utf8').replace(/^\uFEFF/, '')));
    // Recusar pasta existente impede substituir segredos ou apontamentos ativos.
    fs.mkdirSync(output, {recursive: false, mode: 0o700});
    fs.mkdirSync(path.join(output, 'tls'), {mode: 0o700});
    fs.writeFileSync(path.join(output, 'compose.json'), JSON.stringify(result.compose, null, 2) + '\n', {flag: 'wx'});
    fs.writeFileSync(path.join(output, 'nginx.conf'), result.nginx, {flag: 'wx'});
    fs.writeFileSync(path.join(output, '.env'), result.env, {flag: 'wx', mode: 0o600});
    console.log('Arquivos gerados. Revise TLS, recursos e provisionamento; nenhum servico foi iniciado.');
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
module.exports = {render, validate};

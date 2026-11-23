// PostgreSQL novo, sem portas públicas; nunca recebe URL de banco externo.
const fs = require('node:fs'), os = require('node:os'), path = require('node:path'), crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname,'../..');
const image = process.argv[2];
if (process.argv.length !== 3 || !/^(?:edufast-platform:test|edufast-ci-[a-f0-9]{10}:tested)$/.test(image || '')) {
  console.error('Uso: node .github/cicd/run_platform_api.cjs imagem-local-de-teste'); process.exit(1);
}
const project = 'edufast-platform-test-' + crypto.randomBytes(5).toString('hex');
const directory = fs.mkdtempSync(path.join(os.tmpdir(),project+'-'));
const password = crypto.randomBytes(32).toString('hex');
const POSTGRES_APP_ROLE = ['psql -v ON_ERROR_STOP=1 --username "$$POSTGRES_USER" --dbname "$$POSTGRES_DB" -v app_user="$$APP_DB_USER" -v app_password="$$APP_DB_PASSWORD" -v app_db="$$POSTGRES_DB" <<\'SQL\'',
  'CREATE ROLE :"app_user" LOGIN PASSWORD :\'app_password\' NOSUPERUSER NOCREATEDB NOCREATEROLE;',
  'ALTER DATABASE :"app_db" OWNER TO :"app_user";',
  'REVOKE ALL ON DATABASE :"app_db" FROM PUBLIC;',
  'GRANT CONNECT, TEMPORARY ON DATABASE :"app_db" TO :"app_user";', 'SQL', ''].join('\n');
const compose = {services:{
  'db-platform-test':{image:'postgres:17-alpine', environment:{POSTGRES_DB:'edufast_platform_disposable',POSTGRES_USER:'postgres',
    POSTGRES_PASSWORD:crypto.randomBytes(32).toString('hex'),APP_DB_USER:'disposable',APP_DB_PASSWORD:password},
    configs:[{source:'postgres-app-role',target:'/docker-entrypoint-initdb.d/10-app-role.sh'}],
    networks:['isolated'],tmpfs:['/var/lib/postgresql/data'],healthcheck:{test:['CMD-SHELL','PGPASSWORD="$$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$$APP_DB_USER" -d "$$POSTGRES_DB" -tAc "SELECT 1" >/dev/null'],interval:'2s',timeout:'3s',retries:60}},
  tests:{image, working_dir:'/repo', entrypoint:['python'], command:['-m','unittest','discover','-s','/repo/.github/cicd/tests','-p','test_control_plane.py','-v'],
    networks:['isolated'], volumes:[{type:'bind',source:root,target:'/repo',read_only:true}],
    environment:{EDUFAST_TEST_DISPOSABLE:'1',PYTHONPATH:'/repo/Codigos',DB_URL:'sqlite:///:memory:',SECRET_KEY:'synthetic-school-import-only-test-2026',
      PLATFORM_TEST_DATABASE_URL:`postgresql+psycopg://disposable:${password}@db-platform-test:5432/edufast_platform_disposable`}},
},networks:{isolated:{internal:true}},configs:{'postgres-app-role':{content:POSTGRES_APP_ROLE}}};
const file = path.join(directory,'compose.json');
fs.writeFileSync(file,JSON.stringify(compose),{mode:0o600,flag:'wx'});
const base = ['compose','-p',project,'-f',file];
function run(args) {
  const result = spawnSync('docker',[...base,...args],{cwd:root,stdio:'inherit',shell:false});
  if (result.error || result.status !== 0) throw new Error('Executor de testes centrais falhou.');
}
try {
  run(['up','-d','--wait','db-platform-test']);
  run(['run','--rm','--no-deps','tests']);
} catch(error) {console.error(error.message);process.exitCode=1;}
finally {
  try {run(['down','-v','--remove-orphans']);}
  catch(error) {console.error(error.message);process.exitCode=1;}
  const resolved=path.resolve(directory);
  if(path.dirname(resolved)===path.resolve(os.tmpdir()) && path.basename(resolved).startsWith(project+'-')) fs.rmSync(resolved,{recursive:true,force:true});
}

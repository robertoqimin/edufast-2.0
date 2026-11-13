// MySQL novo, sem portas públicas; nunca recebe URL de banco externo.
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
const compose = {services:{
  'db-platform-test':{image:'mysql:8.4', environment:{MYSQL_DATABASE:'edufast_platform_disposable',MYSQL_USER:'disposable',
    MYSQL_PASSWORD:password,MYSQL_ROOT_PASSWORD:crypto.randomBytes(32).toString('hex')},
    networks:['isolated'],tmpfs:['/var/lib/mysql'],healthcheck:{test:['CMD-SHELL','MYSQL_PWD=$$MYSQL_PASSWORD mysql -h127.0.0.1 -u$$MYSQL_USER $$MYSQL_DATABASE -e "SELECT 1" >/dev/null'],interval:'2s',timeout:'3s',retries:60}},
  tests:{image, working_dir:'/repo', entrypoint:['python'], command:['-m','unittest','discover','-s','/repo/.github/cicd/tests','-p','test_control_plane.py','-v'],
    networks:['isolated'], volumes:[{type:'bind',source:root,target:'/repo',read_only:true}],
    environment:{EDUFAST_TEST_DISPOSABLE:'1',PYTHONPATH:'/repo/Códigos',DB_URL:'sqlite:///:memory:',SECRET_KEY:'synthetic-school-import-only-test-2026',
      PLATFORM_TEST_DATABASE_URL:`mysql+pymysql://disposable:${password}@db-platform-test:3306/edufast_platform_disposable`}},
},networks:{isolated:{internal:true}}};
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

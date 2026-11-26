// Demo local MS04: esquema novo em tmpfs; nunca aplica migrations em escolas.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'.ci-results','enem-demo');
const file=path.join(dir,'compose.json');
const args=process.argv.slice(2);
if(args.length>1 || (args[0] && !['start','status','stop'].includes(args[0]))) throw Error('Use start, status ou stop.');
const action=args[0]||'start';
fs.mkdirSync(dir,{recursive:true});
function docker(args){const r=spawnSync('docker',args,{stdio:'inherit',cwd:root});if(r.status!==0)process.exit(r.status||1);}
if(!fs.existsSync(file)){
 if(action!=='start')throw Error('Demonstração ainda não preparada.');
 const compose={services:{web:{image:'edufast-platform:test',working_dir:'/app',
  volumes:[{type:'bind',source:path.join(root,'api'),target:'/app',read_only:true}],
  ports:['127.0.0.1:5092:8000'],tmpfs:['/tmp'],
  environment:{PYTHON_DOTENV_DISABLED:'1',PYTHONDONTWRITEBYTECODE:'1',APP_ENV:'development',
   EDUFAST_ENEM_DEMO:'1',DB_URL:'sqlite:////tmp/edufast-enem-demo.sqlite',
   SECRET_KEY:crypto.randomBytes(48).toString('base64url'),DATA_ENCRYPTION_KEY:crypto.randomBytes(32).toString('base64'),
   SESSION_COOKIE_NAME:'edufast_enem_demo',UPLOAD_FOLDER:'/tmp/enem-uploads'},
  entrypoint:['python','enem_demo_server.py'],
  healthcheck:{test:['CMD','python','-c',"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"],interval:'5s',timeout:'3s',retries:20,start_period:'15s'}}}};
 fs.writeFileSync(file,JSON.stringify(compose,null,2),{mode:0o600});
}
const prefix=['compose','-p','edufast-enem-demo','-f',file];
if(action==='start'){
 docker([...prefix,'up','-d','--no-recreate','--wait']);
 console.log('Demonstração: http://127.0.0.1:5092 | cursos: /cursos');
}else if(action==='status')docker([...prefix,'ps']);
else docker([...prefix,'stop']);

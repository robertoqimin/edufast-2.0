// Testes isolados: não aceita URL, banco ou manifesto do usuário.
const fs=require('node:fs'), os=require('node:os'), path=require('node:path'), crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {render}=require('../../infra/generate.cjs');
const {run:runHttp}=require('./frequencia_http.cjs');
const root=path.resolve(__dirname,'../..');

async function main() {
  const args=process.argv.slice(2);
  if(args.length && (args.length!==2 || args[0]!=='--image' || !/^edufast-(?:ci-[a-f0-9]{10}:tested|frequencia:test)$/.test(args[1])))
    throw Error('Use sem argumentos ou --image com imagem local de teste EduFast.');
  const id=crypto.randomBytes(5).toString('hex'), project='edufast-freq-api-'+id;
  const image=args[1] || project+':tested', temp=fs.mkdtempSync(path.join(os.tmpdir(),'edufast-freq-api-'));
  const report=path.join(root,'.ci-results','frequencia-api',id);fs.mkdirSync(report,{recursive:true});
  const checks={passed:false,project,image,results:[],tests_sha256:crypto.createHash('sha256').update(
    fs.readFileSync(path.join(__dirname,'tests/test_frequencia.py'))).digest('hex')};
  function command(exe,argv,{name,capture=false}={}) {
    const result=spawnSync(exe,argv,{cwd:root,encoding:'utf8',shell:false,maxBuffer:16*1024*1024,timeout:600000});
    if(name)fs.writeFileSync(path.join(report,name+'.log'),(result.stdout||'')+'\n'+(result.stderr||''));
    if(result.error || result.status!==0)throw Error(`${name||exe} falhou. Consulte ${report}. ${result.error?.message||''}`);
    if(!capture && name)console.log(name+': aprovado');
    return result.stdout;
  }
  let compose, httpStarted=false;
  try {
    if(!args.length)command('docker',['build','-f','.github/cicd/Dockerfile','-t',image,'.'],{name:'build'});
    command('docker',['run','--rm','--network','none','--mount',`type=bind,source=${path.join(__dirname,'tests')},target=/tests,readonly`,
      '-e','EDUFAST_TEST_DISPOSABLE=1','-e','DB_URL=sqlite:///:memory:','-e','SECRET_KEY='+crypto.randomBytes(32).toString('hex'),
      '--entrypoint','python',image,'-m','unittest','discover','-s','/tests','-p','test_frequencia.py','-v'],{name:'sqlite'});
    checks.results.push('API Flask + SQLite');
    const generated=render({image:'ghcr.io/samucau1/edufast-2.0@sha256:'+'a'.repeat(64),schools:[{id:'api',host:'api.example.test'}]});
    delete generated.compose.services.gateway;delete generated.compose.networks.edge;
    const app=generated.compose.services['app-api'];app.image=image;
    Object.assign(app.environment,{APP_ENV:'development',EDUFAST_TEST_DISPOSABLE:'1'});
    app.entrypoint=['python','-m','unittest','discover','-s','/tests','-p','test_frequencia.py','-v'];app.command=[];
    app.volumes.push({type:'bind',source:path.join(__dirname,'tests'),target:'/tests',read_only:true});
    fs.writeFileSync(path.join(temp,'compose.json'),JSON.stringify(generated.compose));
    fs.writeFileSync(path.join(temp,'.env'),generated.env,{mode:0o600});
    compose=['compose','-p',project,'--env-file',path.join(temp,'.env'),'-f',path.join(temp,'compose.json')];
    command('docker',[...compose,'up','-d','--wait','--wait-timeout','180','db-api'],{name:'mysql-start'});
    command('docker',[...compose,'run','--rm','--no-deps','-T','app-api'],{name:'mysql'});
    checks.results.push('API Flask + MySQL, incluindo concorrencia real');
    command('docker',['run','--rm','-d','--name',project+'-http','-p','127.0.0.1::8000','--mount',
      `type=bind,source=${path.join(__dirname,'tests')},target=/tests,readonly`,
      '-e','PYTHONPATH=/app','-e','EDUFAST_FREQUENCIA_VISUAL=1','-e','DB_URL=sqlite:////tmp/frequencia-visual.db',
      '-e','SECRET_KEY='+crypto.randomBytes(32).toString('hex'),'-e','DATA_ENCRYPTION_KEY='+crypto.randomBytes(32).toString('base64url')+'=',
      '--entrypoint','python',image,'/tests/frequencia_visual_fixture.py'],{name:'http-start'});
    httpStarted=true;
    const port=command('docker',['port',project+'-http','8000'],{capture:true}).trim().split(':').at(-1);
    const base='http://127.0.0.1:'+port;
    let ready=false;
    for(let i=0;i<40;i++) {
      try {if((await fetch(base+'/healthz',{signal:AbortSignal.timeout(2000)})).status===200){ready=true;break;}}catch{}
      await new Promise(resolve=>setTimeout(resolve,500));
    }
    if(!ready)throw Error('Servidor HTTP descartavel nao ficou pronto.');
    checks.http=await runHttp(base);checks.results.push('HTTP real + SQLite: JSON, multipart, download e CSV');
    checks.passed=true;console.log(`HTTP: ${checks.http.length} verificacoes aprovadas.`);
  } finally {
    // Somente nomes derivados do UUID desta execução; nenhuma configuração externa.
    const stop=spawnSync('docker',['stop',project+'-http'],{encoding:'utf8',shell:false,timeout:30000});
    checks.cleanup=!httpStarted || stop.status===0;
    if(compose) {
      const down=spawnSync('docker',[...compose,'down','-v','--remove-orphans'],{encoding:'utf8',shell:false,timeout:60000});
      checks.cleanup=checks.cleanup && down.status===0;
    }
    if(!checks.cleanup)checks.passed=false;
    fs.writeFileSync(path.join(report,'summary.json'),JSON.stringify(checks,null,2)+'\n');
    const relative=path.relative(os.tmpdir(),temp);
    if(relative.startsWith('..') || path.isAbsolute(relative) || !path.basename(temp).startsWith('edufast-freq-api-'))
      throw Error('Diretorio temporario inesperado; limpeza recusada.');
    fs.rmSync(temp,{recursive:true,force:true});
  }
  if(!checks.passed)throw Error('Testes ou limpeza falharam. Consulte '+report);
  console.log('Relatorio: '+report);
}
if(require.main===module)main().catch(error=>{console.error(error.message);process.exitCode=1});

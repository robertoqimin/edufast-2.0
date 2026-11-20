"""Executa backend em SQLite/MySQL novos, sem URLs de banco externo."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import hashlib
import base64
import time
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',default='edufast-platform:test')
    parser.add_argument('--suite',choices=['ms04','regressao'],default='ms04')
    args = parser.parse_args()
    if not re.fullmatch(r'edufast-(?:platform:test|ms04:test|ci-[a-f0-9]{10}:tested)',args.image):
        parser.error('Use somente imagem local de teste EduFast com dependências instaladas.')
    project = 'edufast-ms04-'+uuid4().hex[:10]
    report = ROOT/'.ci-results'/'cursos-backend'/project
    report.mkdir(parents=True)
    pattern = 'test_cursos_ms04.py' if args.suite=='ms04' else 'test*.py'
    summary = {'passed':False,'project':project,'suite':args.suite,'image':args.image,
        'source':'Checkout atual montado somente para leitura; imagem fornece o runtime/dependencias.',
        'results':[]}
    def source_hash():
        digest = hashlib.sha256()
        for path in sorted([*(ROOT/'Códigos').rglob('*.py'),*(ROOT/'.github/cicd/tests').rglob('*.py'),
                            *(ROOT/'.github/cicd').glob('*.cjs'),Path(__file__).resolve()]):
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()
    summary['source_sha256'] = source_hash()
    with tempfile.TemporaryDirectory(prefix=project+'-') as temp:
        compose = {'services':{
            'db-ms04-test':{'image':'mysql:8.4','environment':{'MYSQL_DATABASE':'edufast_ms04_disposable',
                'MYSQL_USER':'disposable','MYSQL_PASSWORD':'synthetic-ms04-only','MYSQL_ROOT_PASSWORD':uuid4().hex},
                'networks':['isolated'],'tmpfs':['/var/lib/mysql'],
                'healthcheck':{'test':['CMD-SHELL','MYSQL_PWD=$$MYSQL_PASSWORD mysql -h127.0.0.1 -u$$MYSQL_USER $$MYSQL_DATABASE -e "SELECT 1" >/dev/null'],
                    'interval':'2s','timeout':'3s','retries':60}},
            'tests':{'image':args.image,'working_dir':'/repo','networks':['isolated'],
                'volumes':[{'type':'bind','source':str(ROOT),'target':'/repo','read_only':True}],
                'environment':{'DB_URL':'mysql+pymysql://disposable:synthetic-ms04-only@db-ms04-test:3306/edufast_ms04_disposable',
                    'EDUFAST_TEST_DISPOSABLE':'1','PYTHON_DOTENV_DISABLED':'1','APP_ENV':'development',
                    'PYTHONDONTWRITEBYTECODE':'1','SECRET_KEY':'synthetic-ms04-backend-only-key-2026-32chars',
                    'PYTHONPATH':'/repo/Códigos:/repo/.github/cicd/tests'},
                'entrypoint':['python','-m','unittest','discover','-s','/repo/.github/cicd/tests','-p',pattern,'-v']},
            'http':{'image':args.image,'working_dir':'/repo','networks':['http'],
                'volumes':[{'type':'bind','source':str(ROOT),'target':'/repo','read_only':True}],
                'ports':['127.0.0.1::8000'],'tmpfs':['/tmp'],
                'entrypoint':['python','/repo/.github/cicd/tests/frequencia_visual_fixture.py'],
                'environment':{'DB_URL':'sqlite:////tmp/frequencia-visual.db','APP_ENV':'development',
                    'PYTHONPATH':'/repo/Códigos:/repo/.github/cicd/tests','PYTHONDONTWRITEBYTECODE':'1',
                    'EDUFAST_FREQUENCIA_VISUAL':'1','PYTHON_DOTENV_DISABLED':'1','UPLOAD_FOLDER':'/tmp/uploads',
                    'SECRET_KEY':'synthetic-ms04-http-only-secret-32characters',
                    'DATA_ENCRYPTION_KEY':base64.urlsafe_b64encode(os.urandom(32)).decode()}}
        },'networks':{'isolated':{'internal':True},'http':{}}}
        config = Path(temp)/'compose.json'
        config.write_text(json.dumps(compose),encoding='utf-8')
        base = ['docker','compose','-p',project,'-f',str(config)]
        def command(arguments,name):
            result = subprocess.run(arguments,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1800)
            (report/(name+'.log')).write_bytes(result.stdout)
            if result.returncode:
                raise RuntimeError(f'{name} falhou; consulte {report}')
            print(name+': aprovado',flush=True)
        try:
            command(base+['run','--rm','--no-deps','-e','DB_URL=sqlite:///:memory:','tests'],'sqlite')
            summary['results'].append('SQLite')
            command(base+['up','-d','--wait','--wait-timeout','180','db-ms04-test'],'mysql-start')
            command(base+['run','--rm','--no-deps','tests'],'mysql')
            summary['results'].append('MySQL e concorrencia real')
            command(base+['up','-d','http'],'http-start')
            port_result = subprocess.run(base+['port','http','8000'],cwd=ROOT,capture_output=True,text=True,check=True)
            port = int(port_result.stdout.strip().rsplit(':',1)[1])
            target = 'http://127.0.0.1:'+str(port)
            for attempt in range(50):
                try:
                    with urllib.request.urlopen(target+'/healthz',timeout=2) as ready:
                        if ready.status==200:
                            break
                except OSError:
                    time.sleep(0.3)
            else:
                raise RuntimeError('Fixture HTTP descartável não ficou pronta.')
            script = "require('./.github/cicd/frequencia_http.cjs').run(process.argv[1]).then(checks=>{require('node:fs').writeFileSync(process.argv[2],JSON.stringify({passed:true,checks},null,2));console.log(checks.length+' verificacoes HTTP aprovadas')}).catch(error=>{console.error(error);process.exitCode=1})"
            command(['node','-e',script,target,str(report/'http.json')],'http')
            summary['results'].append('HTTP real JWT/multipart/download: frequencia, estudos e cursos')
            summary['passed'] = True
        finally:
            cleaned = subprocess.run(base+['down','-v','--remove-orphans'],cwd=ROOT,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
            (report/'cleanup.log').write_bytes(cleaned.stdout)
            summary['cleaned'] = cleaned.returncode==0
            summary['source_unchanged'] = summary['source_sha256']==source_hash()
            summary['passed'] = summary['passed'] and summary['cleaned'] and summary['source_unchanged']
            revision = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
            summary['base_commit'] = revision.stdout.strip()
            summary['dirty_worktree'] = bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True).stdout.strip())
            (report/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('Evidencias: '+str(report))
    return 0 if summary['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())

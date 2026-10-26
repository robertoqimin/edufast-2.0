"""Executa o Bash real com Docker/HTTPS simulados, sem rede ou volumes reais."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


DOCKER = r'''#!/usr/local/bin/python
import gzip,json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['MOCK_LOG'],'a') as log:
    log.write(json.dumps({'args':args,'image':os.environ.get('EDUFAST_IMAGE')})+'\n')
scenario=os.environ['MOCK_SCENARIO']
if args[0]=='inspect': print('ghcr.io/samucau1/edufast-2.0@sha256:'+'b'*64)
elif 'ps' in args: print('mock-app-container')
elif 'pull' in args and scenario=='pull-fail': sys.exit(1)
elif 'exec' in args:
    if scenario=='backup-fail': sys.exit(1)
    print('-- mock SQL backup')
elif 'run' in args: sys.stdout.buffer.write(gzip.compress(b'mock uploads'))
elif 'up' in args and scenario=='start-fail': sys.exit(1)
'''
CURL = r'''#!/usr/local/bin/python
import json,os
release='wrong' if os.environ['MOCK_SCENARIO']=='wrong-release' else os.environ['MOCK_IMAGE']
print(json.dumps({'status':'ok','release':release}))
'''


@unittest.skipUnless(os.name == 'posix', 'Bash de deploy validado no container Linux')
class DeployScriptTests(unittest.TestCase):
    def scenario(self, name):
        self.temp = tempfile.TemporaryDirectory(prefix='edufast-deploy-')
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        commit = 'a'*40
        release = directory/'releases'/commit
        release.mkdir(parents=True)
        (release/'compose.production.yml').write_text('mock: only')
        (directory/'.env.production').write_text('mock=true')
        (directory/'preserve.txt').write_text('existing data')
        binaries = directory/'bin'
        binaries.mkdir()
        for key, source in [('docker', DOCKER), ('curl', CURL), ('sleep', '#!/bin/sh\nexit 0\n')]:
            path = binaries/key
            path.write_text(source)
            path.chmod(0o700)
        image = 'ghcr.io/samucau1/edufast-2.0@sha256:'+'c'*64
        env = {**os.environ, 'PATH': str(binaries)+':'+os.environ['PATH'], 'MOCK_LOG': str(directory/'commands.jsonl'),
               'MOCK_SCENARIO': name, 'MOCK_IMAGE': image}
        result = subprocess.run(['bash', str(Path(__file__).with_name('deploy.sh')), str(directory), commit, image, 'https://school.example.test'], env=env, capture_output=True, timeout=30)
        calls = [json.loads(line) for line in (directory/'commands.jsonl').read_text().splitlines()]
        self.assertEqual((directory/'preserve.txt').read_text(), 'existing data')
        return directory, result, calls

    def test_success_saves_backups_and_marks_current_release(self):
        directory, result, calls = self.scenario('success')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertTrue((directory/'current').is_symlink())
        self.assertEqual(len(list((directory/'backups').glob('*.sql'))), 1)
        self.assertEqual(len(list((directory/'backups').glob('*.tar.gz'))), 1)
        stop = next(i for i, call in enumerate(calls) if 'stop' in call['args'])
        backup = next(i for i, call in enumerate(calls) if 'exec' in call['args'])
        self.assertLess(stop, backup)

    def test_download_failure_does_not_stop_application(self):
        _, result, calls = self.scenario('pull-fail')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('stop' in call['args'] for call in calls))

    def test_backup_failure_restarts_previous_image(self):
        directory, result, calls = self.scenario('backup-fail')
        self.assertNotEqual(result.returncode, 0)
        up = [call for call in calls if 'up' in call['args']]
        self.assertEqual(len(up), 1)
        self.assertEqual(up[0]['image'], 'ghcr.io/samucau1/edufast-2.0@sha256:'+'b'*64)
        self.assertFalse((directory/'current').exists())

    def test_start_failure_does_not_downgrade_schema(self):
        directory, result, calls = self.scenario('start-fail')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len([call for call in calls if 'up' in call['args']]), 1)
        self.assertEqual(len(list((directory/'backups').glob('*.sql'))), 1)
        self.assertFalse((directory/'current').exists())

    def test_wrong_release_is_not_reported_as_success(self):
        directory, result, _ = self.scenario('wrong-release')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((directory/'current').exists())

    def test_invalid_inputs_exit_before_docker(self):
        result = subprocess.run(['bash', str(Path(__file__).with_name('deploy.sh')), '/', 'main'], capture_output=True)
        self.assertEqual(result.returncode, 2)

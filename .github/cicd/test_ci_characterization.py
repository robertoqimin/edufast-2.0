"""Contracts of the CI entrypoint. No Docker/network side effects in these tests."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch


def load_ci():
    path = Path(__file__).with_name('ci.py')
    spec = importlib.util.spec_from_file_location('ci_characterized', path)
    module = importlib.util.module_from_spec(spec)
    with patch('sys.stdout') as stdout:
        module_stdout = stdout
        spec.loader.exec_module(module)
        module_stdout.reconfigure.assert_called_once_with(encoding='utf-8', errors='replace')
    return module


class CiCharacterization(unittest.TestCase):
    def setUp(self):
        self.ci = load_ci()

    def test_paths_and_project_are_created_once(self):
        ci = self.ci
        self.assertEqual(ci.ROOT, Path(__file__).resolve().parents[2])
        self.assertEqual(ci.PIPELINE, Path(__file__).resolve().parent)
        self.assertEqual(ci.REPORT, ci.ROOT / '.ci-results')
        self.assertRegex(ci.PROJECT, r'^edufast-ci-[a-f0-9]{10}$')
        self.assertEqual(ci.IMAGE, ci.PROJECT + ':tested')
        self.assertEqual(ci.ENV['EDUFAST_IMAGE'], ci.IMAGE)
        self.assertEqual(ci.COMPOSE[:4], ['docker', 'compose', '-p', ci.PROJECT])

    def test_run_returns_bytes_and_preserves_binary_input(self):
        for capture, payload in [(False, None), (True, b'\x00sql\xff')]:
            with self.subTest(capture=capture), patch.object(self.ci.subprocess, 'run', return_value=Mock(returncode=0, stdout=b'output')) as run:
                self.assertEqual(self.ci.run(['tool', Path('argument')], capture=capture, input=payload), b'output')
                run.assert_called_once_with(['tool', 'argument'], cwd=self.ci.ROOT, env=self.ci.ENV,
                    input=payload, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT if payload is None else subprocess.PIPE)

    def test_run_failure_and_compose_prefix(self):
        with patch.object(self.ci.subprocess, 'run', return_value=Mock(returncode=7, stdout=b'failed')):
            with self.assertRaisesRegex(RuntimeError, 'Command failed \\(7\\)'):
                self.ci.run(['tool'], capture=True)
        with patch.object(self.ci, 'run', return_value=b'ok') as run:
            self.assertEqual(self.ci.compose('logs', capture=True), b'ok')
            run.assert_called_once_with(self.ci.COMPOSE + ['logs'], capture=True)

    def test_http_contract_including_empty_payload(self):
        response = Mock(status=201, headers={'X-Test': 'value'})
        response.read.return_value = b'body'
        context = object()
        with patch.object(self.ci.urllib.request, 'urlopen') as opener:
            opener.return_value.__enter__.return_value = response
            self.assertEqual(self.ci.request('https://example.test', context, {'x': 1}), (201, {'X-Test': 'value'}, b'body'))
            args, kwargs = opener.call_args
            self.assertEqual(json.loads(args[0].data), {'x': 1})
            self.assertEqual(kwargs, {'context': context, 'timeout': 15})
            self.ci.request('https://example.test', context, {})
            self.assertIsNone(opener.call_args.args[0].data)

    def test_main_always_cleans_its_own_project_on_failure(self):
        with patch.object(self.ci, 'run', side_effect=RuntimeError('injected')), patch.object(self.ci, 'compose', return_value=b'logs') as compose, patch.object(Path, 'mkdir'), patch.object(Path, 'write_bytes'), patch.object(Path, 'write_text') as write:
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                self.ci.main()
            self.assertEqual(compose.call_args_list[-1].args, ('down', '-v', '--remove-orphans'))
            self.assertFalse(json.loads(write.call_args.args[0])['passed'])

    def test_main_success_sequence(self):
        config = {'services': {'app': {}, 'db': {}}, 'networks': {'backend': {'internal': True}}}
        def compose(*args, **kwargs):
            return json.dumps(config).encode() if args == ('config', '--format', 'json') else b'logs'
        with patch.object(self.ci, 'run'), patch.object(self.ci, 'compose', side_effect=compose) as calls, patch.object(self.ci, 'smoke') as smoke, patch.object(Path, 'mkdir'), patch.object(Path, 'write_bytes'), patch.object(Path, 'write_text') as write:
            self.assertEqual(self.ci.main(), 0)
            smoke.assert_called_once_with()
            sequence = [c.args for c in calls.call_args_list]
            self.assertLess(sequence.index(('run', '--rm', '--no-deps', '-e', 'DB_URL=sqlite:///:memory:', 'tests')), sequence.index(('run', '--rm', '--no-deps', 'tests')))
            self.assertEqual(sequence[-1], ('down', '-v', '--remove-orphans'))
            self.assertTrue(json.loads(write.call_args.args[0])['passed'])

    def test_smoke_retry_tls_backup_and_file_contracts(self):
        trusted, untrusted = object(), object()
        attempts = []
        def request(url, context, data=None):
            if context is untrusted:
                raise self.ci.urllib.error.URLError('untrusted test CA')
            if url.endswith('/healthz'):
                attempts.append(url)
                if len(attempts) == 1:
                    raise self.ci.urllib.error.URLError('starting')
                return 200, {'Strict-Transport-Security': 'max-age=1'}, json.dumps({'release': self.ci.IMAGE}).encode()
            if url.endswith('/login'):
                return 200, {'Set-Cookie': 'session=x; Secure; HttpOnly'}, b'{}'
            return 200, {}, b'page'
        def compose(*args, **kwargs):
            if args[:2] == ('port', 'proxy'): return b'127.0.0.1:12345'
            if args[:3] == ('ps', '-q', 'proxy'): return b'proxy-id'
            if args[-1] == '/app/uploads/ci.txt' and args[:3] == ('exec', '-T', 'app') and 'cat' in args: return b'persisted'
            if kwargs.get('capture') and any('SELECT id FROM ci_backup_probe' in a for a in args): return b'42\n'
            return b''
        with patch.object(self.ci, 'compose', side_effect=compose) as calls, patch.object(self.ci, 'run'), patch.object(self.ci, 'request', side_effect=request), patch.object(self.ci.ssl, 'create_default_context', side_effect=[trusted, untrusted]), patch.object(self.ci.time, 'sleep') as sleep, patch.object(self.ci.subprocess, 'run', return_value=Mock(stdout=b'x' * 200)):
            self.ci.smoke()
            sleep.assert_called_once_with(1)
            binary_calls = [c for c in calls.call_args_list if 'input' in c.kwargs]
            self.assertEqual(len(binary_calls), 2)
            self.assertTrue(all(c.kwargs['input'] == b'x' * 200 for c in binary_calls))


if __name__ == '__main__':
    unittest.main(verbosity=2)

import unittest

from check_deploy import validate
from verify_release import validate_run, validate_release
from deploy_scenarios import DeployScriptTests


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.values = {'DEPLOY_HOST': 'server.example.test', 'DEPLOY_USER': 'deploy',
                       'DEPLOY_PORT': '22', 'DEPLOY_DIR': '/srv/edufast',
                       'PUBLIC_URL': 'https://escola.example.test', 'IMAGE_DIGEST': 'sha256:'+'a'*64,
                       'RELEASE_SHA': 'b'*40, 'BACKUP_CONFIRMED': 'true',
                       'SSH_KEY': 'test-only', 'KNOWN_HOSTS': 'test-only'}

    def test_complete_config(self):
        validate(self.values)

    def test_missing_config_fails_before_network(self):
        for key in self.values:
            with self.subTest(key=key):
                values = {**self.values, key: ''}
                with self.assertRaises(ValueError):
                    validate(values)

    def test_injections_and_unsafe_paths_rejected(self):
        for key, value in [('DEPLOY_HOST', 'x;touch /tmp/x'), ('DEPLOY_USER', '-oProxyCommand=x'),
                           ('DEPLOY_DIR', '/'), ('DEPLOY_DIR', '/srv/../etc'),
                           ('DEPLOY_PORT', '65536'), ('PUBLIC_URL', 'http://example.test'),
                           ('PUBLIC_URL', 'https://user:pass@example.test'),
                           ('PUBLIC_URL', 'https://example.test/path'),
                           ('IMAGE_DIGEST', 'latest'), ('RELEASE_SHA', 'main')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate({**self.values, key: value})

    def test_only_successful_main_ci_can_deploy(self):
        valid = {'path': '.github/workflows/ci.yml', 'status': 'completed', 'conclusion': 'success',
                 'head_branch': 'main', 'event': 'push', 'head_sha': 'b'*40}
        validate_run(valid)
        for key, value in [('conclusion', 'failure'), ('event', 'pull_request'), ('head_branch', 'other'), ('path', '.github/workflows/other.yml')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_run({**valid, key: value})

    def test_release_matches_tested_commit(self):
        release = {'commit': 'b'*40, 'digest': 'sha256:'+'a'*64, 'image': 'ghcr.io/samucau1/edufast-2.0'}
        validate_release(release, 'b'*40)
        for key, value in [('commit', 'c'*40), ('digest', 'latest'), ('image', 'ghcr.io/other/image')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_release({**release, key: value}, 'b'*40)


if __name__ == '__main__':
    unittest.main(verbosity=2)

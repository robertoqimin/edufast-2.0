"""Mesmo CI em Windows/Linux: Docker Compose >=2.24.4 e Docker ativo."""
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid

from types import SimpleNamespace
from runner import http_client, processes, checks, backup_checks, pipeline

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from runner.config import create_config
ROOT, PIPELINE, REPORT, PROJECT, IMAGE, ENV, COMPOSE = create_config(__file__)


def run(args, *, capture=False, input=None):
    return processes.run(args, capture=capture, input=input, root=ROOT, env=ENV)


def compose(*args, **kwargs):
    return processes.compose(*args, command=COMPOSE, execute=run, **kwargs)


def request(url, context, data=None):
    return http_client.request(url, context, data)


def smoke():
    ci = SimpleNamespace(**globals())
    url, context = checks.https_login(ci)
    backup_checks.database(ci)
    backup_checks.uploads(ci, url, context)
    print('HTTPS, CA, HSTS, login, backup/restauração MySQL e persistência de uploads: OK', flush=True)


def main():
    return pipeline.main(SimpleNamespace(**globals()))


if __name__ == '__main__':
    sys.exit(main())

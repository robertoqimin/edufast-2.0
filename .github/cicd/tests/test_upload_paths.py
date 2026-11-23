"""Arquivos gravados e lidos na mesma pasta, independentemente de onde o processo inicia."""
import io
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from flask import Flask, send_from_directory
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound

import config
from config import BASE_DIR, Config, caminho_uploads
from app.services.arquivos_service import _save_profile_photo

PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 64


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class UploadPathTests(TestCase):
    def test_relative_folder_is_anchored_in_codigos_not_in_current_directory(self):
        expected = str((BASE_DIR / 'uploads').resolve())
        with tempfile.TemporaryDirectory() as elsewhere, working_directory(elsewhere):
            self.assertEqual(caminho_uploads('uploads'), expected)
            self.assertEqual(caminho_uploads(None), expected)
            self.assertEqual(caminho_uploads(''), expected)

    def test_absolute_folder_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(caminho_uploads(folder), folder)

    def test_configured_folder_is_always_absolute(self):
        self.assertTrue(Path(Config.UPLOAD_FOLDER).is_absolute())

    def test_saved_file_is_found_by_attachment_download(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as elsewhere, \
                patch.object(config, 'BASE_DIR', Path(base)), working_directory(elsewhere):
            app = Flask(__name__, root_path=str(Path(base) / 'app'))
            app.config['UPLOAD_FOLDER'] = 'uploads'
            with app.test_request_context():
                filename, error = _save_profile_photo({'foto_perfil': FileStorage(io.BytesIO(PNG), 'foto.png')})
                self.assertIsNone(error)
                self.assertTrue((Path(base) / 'uploads' / filename).is_file())
                response = send_from_directory(caminho_uploads(app.config['UPLOAD_FOLDER']), filename)
                response.direct_passthrough = False
                self.assertEqual(response.get_data(), PNG)
                response.close()
                # Comportamento anterior: o caminho relativo era procurado dentro de app/.
                with self.assertRaises(NotFound):
                    send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    def test_application_never_reads_upload_folder_without_anchor(self):
        raw = re.compile(r"""config\[['"]UPLOAD_FOLDER['"]\]""")
        offenders = []
        for path in (BASE_DIR / 'app').rglob('*.py'):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if raw.search(line) and 'caminho_uploads(' not in line:
                    offenders.append(f'{path.relative_to(BASE_DIR)}:{number}')
        self.assertEqual(offenders, [])

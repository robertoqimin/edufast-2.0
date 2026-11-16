"""Servidor local descartável; não aceita banco existente ou endereço de produção."""
import os
import sys
import tempfile
from sqlalchemy import inspect
from app.database import engine
from app.models import frequencia_model
from two_school_test_data import initialize

local = sys.argv[1:] == ['--local']
expected = 'sqlite:///:memory:' if local else 'sqlite:////tmp/frequencia-visual.db'
if (os.getenv('EDUFAST_FREQUENCIA_VISUAL') != '1' or str(engine.url) != expected
        or sys.argv[1:] not in ([], ['--local'])
        or inspect(engine).get_table_names()):
    raise RuntimeError('Use somente o container visual novo e descartável.')
initialize(engine, 'teste01')
from app import create_app
app = create_app()
if local:
    # Memory database and loopback only; files are private to this test process.
    with tempfile.TemporaryDirectory(prefix='edufast-frequencia-visual-') as folder:
        app.config['UPLOAD_FOLDER'] = folder
        app.run(host='127.0.0.1', port=5091, debug=False, threaded=False, use_reloader=False)
else:
    app.run(host='0.0.0.0', port=8000, debug=False)

"""Servidor local descartável; não aceita banco existente ou endereço de produção."""
import os
from sqlalchemy import inspect
from app.database import engine
from app.models import frequencia_model
from two_school_test_data import initialize

if (os.getenv('EDUFAST_FREQUENCIA_VISUAL') != '1' or str(engine.url) != 'sqlite:////tmp/frequencia-visual.db'
        or inspect(engine).get_table_names()):
    raise RuntimeError('Use somente o container visual novo e descartável.')
initialize(engine, 'teste01')
from app import create_app
create_app().run(host='0.0.0.0', port=8000, debug=False)

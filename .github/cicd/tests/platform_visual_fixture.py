"""Demonstração local descartável: nunca aponta para os bancos reais das escolas."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from control_plane import create_app, today
from control_plane.models import Base

if os.getenv('EDUFAST_PLATFORM_VISUAL') != '1':
    raise RuntimeError('Fixture exige opt-in explicito.')
target = Path('/tmp/edufast-platform-demo.db')
if target.exists():
    raise RuntimeError('Banco de demonstracao ja existe; nao sobrescrever.')

app = create_app(dict(TESTING=True, DATABASE_URL='sqlite:///' + str(target),
    PLATFORM_ENV='development', SESSION_COOKIE_SECURE=False,
    SECRET_KEY='isolated-platform-demo-only-2026-' + 'x' * 32))
Base.metadata.create_all(app.extensions['platform_engine'])
result = app.test_cli_runner().invoke(args=['create-owner', '--email', 'dono@plataforma.local'],
    input='Plataforma-teste-2026!\nPlataforma-teste-2026!\n')
if result.exit_code:
    raise RuntimeError('Falha ao preparar proprietario sintetico.')

from two_school_test_data import initialize
from app.platform_publish import directory
import hashlib
from control_plane.models import School
from uuid import uuid4

with app.test_client() as client:
    client.get('/login')
    with client.session_transaction() as session:
        csrf = session['csrf_token']
    client.post('/login', json=dict(email='dono@plataforma.local', password='Plataforma-teste-2026!'), headers={'X-CSRF-Token': csrf})
    with client.session_transaction() as session:
        csrf = session['csrf_token']
    for index, slug in enumerate(['teste01', 'teste02'], 1):
        response = client.post('/escolas', json=dict(name='Escola Teste ' + str(index).zfill(2), slug=slug,
            domain=slug + '.example.test', monthly='500,00'), headers={'X-CSRF-Token': csrf})
        if response.status_code != 200:
            raise RuntimeError('Cadastro de fixture falhou.')
        sid = response.json['id']
        with Session(app.extensions['platform_engine']) as db:
            db.get(School, sid).token_hash = hashlib.sha256(slug.encode()).hexdigest()
            db.commit()
        source = create_engine('sqlite:///:memory:')
        initialize(source, slug)
        with Session(source) as db:
            payload = directory(db)
        response = client.post('/integracao/' + slug + '/pessoas', json=payload, headers={'Authorization': 'Bearer ' + slug})
        if response.status_code != 200:
            raise RuntimeError('Sincronizacao sintetica falhou.')
        source.dispose()
        for kind, amount in [('receita', '500,00' if index == 1 else '700,00'), ('despesa', '120,00' if index == 1 else '180,00')]:
            response = client.post(f'/escolas/{sid}/movimentos', json=dict(kind=kind, amount=amount,
                day=today().isoformat(), description='Exemplo ficticio', request_key=str(uuid4())), headers={'X-CSRF-Token': csrf})
            if response.status_code != 200:
                raise RuntimeError('Financeiro sintetico falhou.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

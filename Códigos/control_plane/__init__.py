"""Painel do proprietário, executado em serviço/banco separados das escolas."""
import hashlib
import hmac
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import click
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine, delete, event, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from .models import Base, Owner, School, Person, Movement, Audit


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()


def money(value):
    try:
        text = str(value)
        if not re.fullmatch(r'\d{1,8}(?:[.,]\d{1,2})?', text):
            raise ValueError()
        return int(Decimal(text.replace(',', '.')) * 100)
    except (InvalidOperation, ValueError):
        abort(400, 'Informe um valor em reais com ate duas casas decimais.')


def clean(data, key, size, minimum=1):
    value = data.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= size:
        abort(400, f'Campo {key} invalido.')
    return value.strip()


def create_app(config=None):
    shared = Path(__file__).resolve().parents[1] / 'app'
    app = Flask(__name__, template_folder=str(shared / 'templates'), static_folder=str(shared / 'static'))
    app.config.update(
        SECRET_KEY=os.getenv('PLATFORM_SECRET_KEY', ''),
        DATABASE_URL=os.getenv('PLATFORM_DATABASE_URL', ''),
        PLATFORM_ENV=os.getenv('PLATFORM_ENV', 'production'),
        TRUSTED_HOSTS=[v.strip() for v in os.getenv('PLATFORM_TRUSTED_HOSTS', '').split(',') if v.strip()] or None,
        SESSION_COOKIE_NAME='edufast_platform_owner', SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=True,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=4), MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=50_000, MAX_FORM_PARTS=40,
    )
    if config:
        app.config.update(config)
    if not isinstance(app.secret_key, str) or len(app.secret_key) < 32:
        raise RuntimeError('PLATFORM_SECRET_KEY propria com pelo menos 32 caracteres obrigatoria.')
    if not app.config['DATABASE_URL']:
        raise RuntimeError('PLATFORM_DATABASE_URL do banco central obrigatoria.')
    if app.config['PLATFORM_ENV'] == 'production':
        if not app.config['TRUSTED_HOSTS'] or not app.config['SESSION_COOKIE_SECURE']:
            raise RuntimeError('Producao exige hosts autorizados e cookie seguro.')
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    options = {'pool_pre_ping': True}
    if app.config['DATABASE_URL'].startswith('mysql'):
        options.update(pool_size=4, max_overflow=0, pool_timeout=5)
    engine = create_engine(app.config['DATABASE_URL'], **options)
    if app.config['PLATFORM_ENV'] == 'production' and engine.dialect.name != 'mysql':
        raise RuntimeError('Banco central de producao exige MySQL com transacoes e locks.')
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    app.extensions['platform_engine'] = engine
    app.extensions['platform_session'] = sessionmaker(bind=engine, expire_on_commit=False)
    # Validação somente: DDL nunca é executado ao iniciar o painel.
    if not app.config.get('TESTING'):
        inspector = inspect(engine)
        for table in Base.metadata.sorted_tables:
            if table.name not in inspector.get_table_names() or set(table.columns.keys()) - {
                    column['name'] for column in inspector.get_columns(table.name)}:
                raise RuntimeError('Banco central pendente de revisao/provisionamento: ' + table.name)
            unique = inspector.get_unique_constraints(table.name)
            unique += [index for index in inspector.get_indexes(table.name) if index.get('unique')]
            for constraint in table.constraints:
                if constraint.__class__.__name__ == 'UniqueConstraint' and not any(
                        set(item['column_names']) == set(constraint.columns.keys()) for item in unique):
                    raise RuntimeError('Constraint central pendente de revisao: ' + table.name)

    fake_hash = generate_password_hash(secrets.token_urlsafe(32))

    def json_mode():
        return request.is_json or request.args.get('formato') == 'json' or request.accept_mimetypes.best == 'application/json'

    def audit(action, reference, actor='owner'):
        g.db.add(Audit(actor=actor, action=action, reference=str(reference)))

    def response(message, endpoint='dashboard', **values):
        if json_mode():
            return jsonify(message=message, **values)
        flash(message)
        return redirect(url_for(endpoint), code=303)

    @app.before_request
    def protect():
        g.db = app.extensions['platform_session']()
        if request.endpoint is None:
            abort(404)
        if request.endpoint == 'static':
            return
        if request.endpoint == 'snapshot':
            return  # Autenticação por chave da própria escola, abaixo; nunca aceita sessão.
        if request.headers.get('Authorization'):
            abort(401, 'Use o login exclusivo do proprietario.')
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            expected = session.get('csrf_token', '')
            if not expected or not hmac.compare_digest(str(expected), str(supplied)):
                abort(403, 'Sessao do formulario expirada. Recarregue a pagina.')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                abort(403)
            if request.headers.get('Origin') and request.headers['Origin'].rstrip('/') != request.host_url.rstrip('/'):
                abort(403)
        if request.endpoint in {'login', 'healthz'}:
            return
        owner = g.db.get(Owner, 1)
        if not owner or session.get('platform_owner') != owner.id or session.get('owner_version') != owner.auth_version:
            if session.get('platform_owner'):
                session.clear()
            if json_mode():
                abort(401, 'Login do proprietario obrigatorio.')
            return redirect(url_for('login'))

    @app.teardown_request
    def close(_):
        if getattr(g, 'db', None):
            g.db.close()

    @app.after_request
    def headers(result):
        result.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                               'X-Frame-Options': 'DENY', 'Referrer-Policy': 'same-origin',
                               'Content-Security-Policy': "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"})
        return result

    @app.errorhandler(IntegrityError)
    @app.errorhandler(StaleDataError)
    def conflict(error):
        g.db.rollback()
        return render_error(409, 'Registro existente ou alterado. Recarregue antes de enviar novamente.')

    def render_error(code, message):
        if json_mode():
            return jsonify(erro=message), code
        return render_template('platform_error.html', code=code, message=message), code

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_error(error.code, error.description)

    @app.context_processor
    def context():
        session.setdefault('csrf_token', secrets.token_urlsafe(32))
        logged = bool(session.get('platform_owner'))
        return dict(platform_workspace=True, workspace_role='platform_owner',
                    escola={'nome': 'EducaFast', 'sigla': 'ef', 'subtitulo': 'ADMINISTRAÇÃO DA PLATAFORMA'}, tema={},
                    csrf_token=session['csrf_token'], submission_key=lambda: str(uuid4()),
                    platform_logged=logged, current_day=today().isoformat())

    @app.template_filter('brl')
    def brl(cents):
        return 'R$ ' + f'{int(cents) / 100:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

    @app.template_filter('local_datetime')
    def local_datetime(value):
        return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M') if value else 'Ainda não sincronizada'

    @app.get('/healthz')
    def healthz():
        g.db.execute(select(Owner.id).limit(1))
        return jsonify(status='ok')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('platform_login.html')
        data = request.get_json(silent=True) if request.is_json else request.form
        if not isinstance(data, dict) and request.is_json:
            abort(400)
        email, password = str(data.get('email', ''))[:121], str(data.get('password', ''))[:257]
        owner = g.db.scalar(select(Owner).where(Owner.id == 1).with_for_update())
        if owner and owner.locked_until and owner.locked_until > utcnow():
            abort(429, 'Muitas tentativas. Aguarde 15 minutos.')
        valid = check_password_hash(owner.password_hash if owner else fake_hash, password)
        if not owner or not hmac.compare_digest(owner.email.encode(), email.encode()) or not valid:
            if owner:
                owner.failures += 1
                if owner.failures >= 5:
                    owner.locked_until = utcnow() + timedelta(minutes=15)
                    owner.failures = 0
                audit('login_recusado', 'owner')
                g.db.commit()
            abort(401, 'E-mail ou senha invalidos.')
        owner.failures, owner.locked_until = 0, None
        session.clear()
        session.update(platform_owner=owner.id, owner_version=owner.auth_version, csrf_token=secrets.token_urlsafe(32))
        session.permanent = True
        audit('login', 'owner')
        g.db.commit()
        return response('Acesso autorizado.')

    @app.post('/logout')
    def logout():
        audit('logout', 'owner')
        g.db.commit()
        session.clear()
        return redirect(url_for('login'), code=303)

    def month_range():
        value = request.args.get('mes', today().strftime('%Y-%m'))
        if not re.fullmatch(r'\d{4}-\d{2}', value):
            abort(400, 'Mes invalido.')
        try:
            start = date.fromisoformat(value + '-01')
            end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        except ValueError:
            abort(400, 'Mes invalido.')
        return value, start, end

    @app.get('/')
    def dashboard():
        month, start, end = month_range()
        schools = g.db.scalars(select(School).order_by(School.name)).all()
        amounts = g.db.execute(select(Movement.school_id, Movement.kind, func.sum(Movement.cents)).where(
            Movement.day >= start, Movement.day < end, Movement.cancelled_at.is_(None)
        ).group_by(Movement.school_id, Movement.kind)).all()
        sums = {(sid, kind): int(cents) for sid, kind, cents in amounts}
        counts = dict(g.db.execute(select(Person.school_id, func.count()).group_by(Person.school_id)).all())
        rows = [dict(id=s.id, slug=s.slug, name=s.name, domain=s.domain, url='https://' + s.domain + '/login', state=s.state,
                     monthly_cents=s.monthly_cents, people=counts.get(s.id, 0), synced_at=s.synced_at,
                     receita=sums.get((s.id, 'receita'), 0), despesa=sums.get((s.id, 'despesa'), 0)) for s in schools]
        for row in rows:
            row['lucro'] = row['receita'] - row['despesa']
        totals = {key: sum(row[key] for row in rows) for key in ('receita', 'despesa', 'lucro', 'people')}
        if json_mode():
            return jsonify(schools=rows, totals=totals, month=month, currency='BRL', values='centavos')
        return render_template('platform_dashboard.html', rows=rows, totals=totals, month=month)

    @app.post('/escolas')
    def create_school():
        data = request.get_json(silent=True) if request.is_json else request.form
        if request.is_json and not isinstance(data, dict):
            abort(400)
        name, slug, domain = clean(data, 'name', 120), clean(data, 'slug', 31), clean(data, 'domain', 253)
        if slug == 'plataforma-central' or not re.fullmatch(r'[a-z][a-z0-9-]{1,30}', slug) or not re.fullmatch(
                r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]', domain):
            abort(400, 'Identificador ou dominio invalido.')
        school = School(name=name, slug=slug, domain=domain, monthly_cents=money(data.get('monthly', '0')))
        g.db.add(school)
        g.db.flush()
        audit('escola_cadastrada', school.id)
        g.db.commit()
        return response('Escola cadastrada. A ativacao ainda precisa ser concluida.', id=school.id)

    @app.route('/escolas/<int:school_id>', methods=['GET', 'POST'])
    def school_detail(school_id):
        school = g.db.get(School, school_id) or abort(404)
        if request.method == 'POST':
            data = request.get_json(silent=True) if request.is_json else request.form
            if request.is_json and not isinstance(data, dict):
                abort(400)
            if str(school.version) != str(data.get('version')):
                abort(409, 'Escola alterada. Recarregue antes de salvar.')
            state = data.get('state')
            if not isinstance(state, str) or state not in {'pendente', 'ativa', 'suspensa'}:
                abort(400)
            school.name = clean(data, 'name', 120)
            school.monthly_cents = money(data.get('monthly'))
            school.state = state
            audit('escola_atualizada', school.id)
            g.db.commit()
            return response('Cadastro atualizado. O estado comercial nao inicia ou para containers.')
        month, start, end = month_range()
        movements = g.db.scalars(select(Movement).where(Movement.school_id == school.id,
            Movement.day >= start, Movement.day < end).order_by(Movement.day.desc(), Movement.id.desc())).all()
        return render_template('platform_school.html', school=school, movements=movements, month=month)

    @app.get('/pessoas')
    def people():
        try:
            page = int(request.args.get('pagina', '1'))
            sid = int(request.args['escola']) if request.args.get('escola') else None
        except ValueError:
            abort(400)
        if not 1 <= page <= 100000:
            abort(400)
        term = request.args.get('busca', '').strip()[:120]
        query = select(Person, School.name).join(School, Person.school_id == School.id)
        if sid is not None:
            query = query.where(Person.school_id == sid)
        if term:
            escaped = term.replace('!', '!!').replace('%', '!%').replace('_', '!_')
            query = query.where(Person.name.ilike('%' + escaped + '%', escape='!') | Person.email.ilike('%' + escaped + '%', escape='!'))
        total = g.db.scalar(select(func.count()).select_from(query.subquery()))
        result = g.db.execute(query.order_by(School.name, Person.name, Person.id).limit(50).offset((page - 1) * 50)).all()
        audit('pessoas_consultadas', sid or 'todas')
        g.db.commit()
        if json_mode():
            return jsonify(total=total, page=page, people=[dict(school_id=p.school_id, school=name,
                local_id=p.local_id, name=p.name, email=p.email, role=p.role, state=p.state) for p, name in result])
        return render_template('platform_people.html', rows=result, total=total, page=page, term=term,
                               selected=sid, schools=g.db.scalars(select(School).order_by(School.name)).all())

    @app.post('/escolas/<int:school_id>/movimentos')
    def movement(school_id):
        g.db.get(School, school_id) or abort(404)
        data = request.get_json(silent=True) if request.is_json else request.form
        if request.is_json and not isinstance(data, dict):
            abort(400)
        try:
            key = str(UUID(str(data.get('request_key'))))
            day = date.fromisoformat(str(data.get('day')))
        except (ValueError, TypeError):
            abort(400, 'Chave de envio ou data invalida.')
        kind, cents = data.get('kind'), money(data.get('amount'))
        description = clean(data, 'description', 200)
        if not isinstance(kind, str) or kind not in {'receita', 'despesa'} or cents <= 0 or day > today():
            abort(400, 'Informe um recebimento ou despesa ja realizado, com valor positivo.')
        previous = g.db.scalar(select(Movement).where(Movement.request_key == key))
        if previous:
            if (previous.school_id, previous.day, previous.kind, previous.cents, previous.description) != (
                    school_id, day, kind, cents, description):
                abort(409, 'Chave de envio ja utilizada para outro lancamento.')
            return response('Lancamento ja registrado.', id=previous.id)
        item = Movement(school_id=school_id, request_key=key, kind=kind, cents=cents, day=day, description=description)
        g.db.add(item)
        g.db.flush()
        audit('movimento_registrado', item.id)
        g.db.commit()
        return response('Lancamento registrado.', id=item.id)

    @app.post('/movimentos/<int:movement_id>/cancelar')
    def cancel(movement_id):
        item = g.db.scalar(select(Movement).where(Movement.id == movement_id).with_for_update()) or abort(404)
        data = request.get_json(silent=True) if request.is_json else request.form
        if request.is_json and not isinstance(data, dict):
            abort(400)
        reason = clean(data, 'reason', 200, 5)
        if item.cancelled_at:
            abort(409, 'Lancamento ja cancelado.')
        item.cancelled_at, item.cancellation_reason = utcnow(), reason
        audit('movimento_cancelado', item.id)
        g.db.commit()
        return response('Lancamento cancelado; historico preservado.')

    @app.post('/integracao/<slug>/pessoas')
    def snapshot(slug):
        header = request.headers.get('Authorization', '')
        school = g.db.scalar(select(School).where(School.slug == slug).with_for_update())
        token = header[7:] if header.startswith('Bearer ') else ''
        if not school or not school.token_hash or not token or not hmac.compare_digest(
                school.token_hash, hashlib.sha256(token.encode()).hexdigest()):
            abort(401, 'Integracao nao autorizada.')
        if school.state == 'suspensa':
            abort(403, 'Integracao suspensa.')
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {'captured_at', 'people'}:
            abort(400, 'Formato de sincronizacao invalido.')
        try:
            captured = datetime.strptime(data['captured_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except (ValueError, TypeError):
            abort(400, 'Data de sincronizacao invalida.')
        if not utcnow() - timedelta(minutes=30) <= captured <= utcnow() + timedelta(minutes=1) or (school.captured_at and captured <= school.captured_at):
            abort(409, 'Sincronizacao repetida, antiga ou com horario futuro.')
        persons = data['people']
        if not isinstance(persons, list) or len(persons) > 10000:
            abort(400, 'O envio completo deve conter ate 10000 contas.')
        ids, prepared = set(), []
        for person in persons:
            if not isinstance(person, dict) or set(person) != {'local_id', 'name', 'email', 'role', 'state'}:
                abort(400, 'Pessoa invalida; nenhum dado foi substituido.')
            local_id = person['local_id']
            if type(local_id) is not int or not 1 <= local_id <= 2147483647 or local_id in ids:
                abort(400, 'ID local invalido ou duplicado.')
            ids.add(local_id)
            if not isinstance(person['role'], str) or not isinstance(person['state'], str) or person['role'] not in {'admin', 'super_admin', 'professor', 'aluno'} or person['state'] not in {'ativo', 'inativo', 'pendente', 'bloqueado'}:
                abort(400, 'Papel ou estado invalido.')
            prepared.append(Person(school_id=school.id, local_id=local_id, name=clean(person, 'name', 120),
                email=clean(person, 'email', 120), role=person['role'], state=person['state']))
        g.db.execute(delete(Person).where(Person.school_id == school.id))
        g.db.add_all(prepared)
        school.captured_at, school.synced_at = captured, utcnow()
        audit('pessoas_sincronizadas', len(prepared), actor='school:' + school.slug)
        g.db.commit()
        return jsonify(received=len(prepared))

    from .commands import register
    register(app)
    return app

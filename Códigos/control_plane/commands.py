import hashlib
import json
import os
import re
import secrets
from pathlib import Path
import click
from sqlalchemy import select
from werkzeug.security import generate_password_hash
from .models import Owner, School, Audit


def private_file(destination, value):
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(value)


def register(app):
    @app.cli.command('create-owner')
    @click.option('--email', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_owner(email, password):
        """Cria o unico proprietario; nunca promove usuarios de escolas."""
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 120 or not 12 <= len(password) <= 256:
            raise click.ClickException('Informe e-mail valido e senha entre 12 e 256 caracteres.')
        with app.extensions['platform_session']() as db:
            if db.get(Owner, 1):
                raise click.ClickException('Proprietario ja cadastrado; nenhuma alteracao realizada.')
            db.add(Owner(id=1, email=email, password_hash=generate_password_hash(password)))
            db.add(Audit(actor='operator', action='proprietario_criado', reference='1'))
            db.commit()
        click.echo('Proprietario criado. Entre no endereco exclusivo da plataforma.')

    @app.cli.command('reset-owner-password')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def reset_owner_password(password):
        """Recuperacao pelo operador SSH; revoga todas as sessoes anteriores."""
        if not 12 <= len(password) <= 256:
            raise click.ClickException('Senha deve conter entre 12 e 256 caracteres.')
        with app.extensions['platform_session']() as db:
            owner = db.scalar(select(Owner).where(Owner.id == 1).with_for_update())
            if not owner:
                raise click.ClickException('Cadastre o proprietario primeiro.')
            owner.password_hash = generate_password_hash(password)
            owner.auth_version += 1
            owner.failures, owner.locked_until = 0, None
            db.add(Audit(actor='operator', action='senha_proprietario_alterada', reference='1'))
            db.commit()
        click.echo('Senha alterada e sessoes anteriores revogadas.')

    @app.cli.command('integration-key')
    @click.argument('slug')
    @click.option('--output', required=True, type=click.Path(path_type=Path))
    @click.option('--rotate', is_flag=True, help='Revoga a chave anterior desta escola.')
    def integration_key(slug, output, rotate):
        """Salva chave de envio em arquivo privado novo; banco guarda somente hash."""
        with app.extensions['platform_session']() as db:
            school = db.scalar(select(School).where(School.slug == slug).with_for_update())
            if not school or (school.token_hash and not rotate):
                raise click.ClickException('Escola ausente ou chave existente. Para revogar a anterior, use --rotate.')
            token = secrets.token_urlsafe(48)
            private_file(output, token + '\n')
            school.token_hash = hashlib.sha256(token.encode()).hexdigest()
            db.add(Audit(actor='operator', action='chave_integracao_rotacionada' if rotate else 'chave_integracao_criada', reference=slug))
            try:
                db.commit()
            except Exception:
                output.unlink()
                raise
        click.echo('Chave salva no arquivo privado. Configure apenas na escola correspondente; nao enviar ao Git.')

    @app.cli.command('export-schools')
    @click.option('--project', required=True)
    @click.option('--image', required=True)
    @click.option('--platform-host', required=True)
    @click.option('--output', required=True, type=click.Path(path_type=Path))
    def export_schools(project, image, platform_host, output):
        """Exporta cadastro para revisao pelo operador; nao provisiona infraestrutura."""
        if not re.fullmatch(r'edufast-[a-z][a-z0-9-]{1,40}', project) or not re.fullmatch(
                r'ghcr\.io/samucau1/edufast-2\.0@sha256:[a-f0-9]{64}', image):
            raise click.ClickException('Projeto ou imagem por digest invalido.')
        with app.extensions['platform_session']() as db:
            schools = db.scalars(select(School).order_by(School.id)).all()
            if not 1 <= len(schools) <= 50:
                raise click.ClickException('A frota deve conter entre 1 e 50 escolas.')
            if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]', platform_host) or len(platform_host) > 253 or any(s.domain == platform_host for s in schools):
                raise click.ClickException('Dominio exclusivo da plataforma invalido ou duplicado.')
            private_file(output, json.dumps(dict(project=project, image=image,
                platform=dict(host=platform_host),
                schools=[dict(id=s.slug, host=s.domain) for s in schools]), indent=2) + '\n')
        click.echo('Manifesto exportado. Revisar antes de usar manage.cjs prepare; incluir sempre a revisao anterior.')

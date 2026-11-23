"""Envio explicito do diretorio de contas para o painel do proprietario."""
import json
from datetime import datetime, timezone
from sqlalchemy import select
import click


def directory(db):
    from app.models import UsuarioModel, AlunoModel, ProfessorModel
    users = db.scalars(select(UsuarioModel).order_by(UsuarioModel.id).limit(10001)).all()
    if len(users) > 10000:
        raise ValueError('Mais de 10000 contas: envio interrompido sem truncar o cadastro.')
    pupils = dict(db.execute(select(AlunoModel.usuario_id, AlunoModel.nome)).all())
    teachers = dict(db.execute(select(ProfessorModel.usuario_id, ProfessorModel.nome)).all())
    return dict(captured_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'), people=[dict(
        local_id=user.id, name=pupils.get(user.id) or teachers.get(user.id) or user.email,
        email=user.email, role=user.tipo, state=user.estado) for user in users])


def register(app):
    @app.cli.command('platform-directory')
    def export():
        """Exportacao pelo operador SSH, sem alterar contas ou permissoes."""
        from app.database import get_session
        try:
            with get_session() as db:
                payload = directory(db)
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        click.echo(json.dumps(payload, ensure_ascii=False))

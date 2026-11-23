"""Provisionamento administrativo sem apagar usuários ou redefinir senhas."""
import click
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from .database import get_session
from .models import UsuarioModel
from .models.usuario_model import normalizar_email


def register_commands(app):
    from .platform_publish import register
    register(app)

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--super-admin", is_flag=True, help="Provisiona um superadmin novo; nunca promove conta existente.")
    def create_admin(email, password, super_admin=False):
        """Cria um administrador novo; recusa substituir uma conta existente."""
        from .services.senha_service import MINIMO_ADMIN, problema_senha
        erro_senha = problema_senha(password, MINIMO_ADMIN)
        if "@" not in email or erro_senha:
            raise click.ClickException(erro_senha or "Informe email válido.")
        db = get_session()
        try:
            if db.query(UsuarioModel).filter_by(email=normalizar_email(email)).first():
                raise click.ClickException("A conta já existe; nenhuma alteração realizada.")
            db.add(UsuarioModel(email=email, senha=generate_password_hash(password), tipo="super_admin" if super_admin else "admin", estado="ativo"))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise click.ClickException("A conta ja existe; nenhuma alteracao realizada.")
        finally:
            db.close()
        click.echo("Administrador criado; usuários existentes preservados.")

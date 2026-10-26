"""Provisionamento administrativo sem apagar usuários ou redefinir senhas."""
import click
from werkzeug.security import generate_password_hash

from .database import get_session
from .models import UsuarioModel


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(email, password):
        """Cria um administrador novo; recusa substituir uma conta existente."""
        if "@" not in email or len(password) < 12:
            raise click.ClickException("Informe email válido e senha com pelo menos 12 caracteres.")
        db = get_session()
        try:
            if db.query(UsuarioModel).filter_by(email=email).first():
                raise click.ClickException("A conta já existe; nenhuma alteração realizada.")
            db.add(UsuarioModel(email=email, senha=generate_password_hash(password), tipo="admin"))
            db.commit()
        finally:
            db.close()
        click.echo("Administrador criado; usuários existentes preservados.")

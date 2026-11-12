"""Original superprofile entry points using current database authorization."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from app.concurrency import MutationConflict, begin_submission, finish_submission
from app.controllers.auth_controller import cadastrar_usuario
from app.controllers.admin_controller import get_comunicados
from app.database import get_session
from app.models import UsuarioModel, ProfessorModel, AlunoModel
from app.services.identidade_service import require_role, current_identity
from app.services import escola

gestao_bp = Blueprint('gestao', __name__)


def _render(error=None, permission_error=None, edit_user_id=None, status=200):
    with get_session() as db:
        rows = []
        for user in db.query(UsuarioModel).order_by(UsuarioModel.email):
            teacher = db.query(ProfessorModel).filter_by(usuario_id=user.id).first()
            student = db.query(AlunoModel).filter_by(usuario_id=user.id).first()
            profile = teacher or student
            rows.append({'id': user.id, 'email': user.email, 'tipo': user.tipo,
                'nome': profile.nome if profile else user.email.split('@')[0],
                'tem_professor': bool(teacher), 'tem_aluno': bool(student), 'versao': user.auth_version})
    return render_template('super_usuarios.html', usuarios=rows, error=error,
        permission_error=permission_error, edit_user_id=edit_user_id), status


@gestao_bp.route('/super/usuarios', methods=['GET', 'POST'])
def usuarios():
    identity = require_role('super_admin')
    if request.method == 'GET':
        return _render()
    role = request.form.get('tipo')
    if role in {'aluno', 'professor'}:
        body, status = cadastrar_usuario(request.form, request.files, aprovado=True)
    elif role == 'admin':
        email, password = request.form.get('email', '').strip(), request.form.get('senha', '')
        if '@' not in email or len(email) > 120 or len(password) < 12:
            return _render(error='Informe e-mail valido e senha com pelo menos 12 caracteres.', status=400)
        with get_session() as db:
            entry, replay = begin_submission(db, 'super:criar_admin', actor=identity.id)
            if replay:
                return redirect(url_for('gestao.usuarios'))
            db.add(UsuarioModel(email=email, senha=generate_password_hash(password), tipo='admin', estado='ativo'))
            try:
                db.flush()
                body, status = finish_submission(db, entry, {'mensagem': 'Administrador criado'}, 201)
            except IntegrityError:
                db.rollback()
                return _render(error='E-mail ja cadastrado.', status=409)
    else:
        abort(403)
    if status not in {200, 201}:
        return _render(error=body.get('erro', 'Nao foi possivel criar a conta.'), status=status)
    flash('Usuario criado. O acesso esta disponivel.', 'success')
    return redirect(url_for('gestao.usuarios'))


@gestao_bp.post('/super/usuarios/<int:user_id>/perfil')
def perfil(user_id):
    identity = require_role('super_admin')
    role = request.form.get('tipo')
    if role not in {'admin', 'professor', 'aluno'} or user_id == identity.id:
        abort(403)
    with get_session() as db:
        user = db.query(UsuarioModel).filter_by(id=user_id).with_for_update().first()
        if user is None:
            abort(404)
        if user.tipo == 'super_admin' or user.estado != 'ativo':
            abort(403)
        if role == 'professor' and db.query(ProfessorModel).filter_by(usuario_id=user_id).first() is None:
            name, cpf = request.form.get('nome', '').strip(), request.form.get('cpf', '').strip()
            if not name or len(name) > 120 or not cpf or len(cpf) > 14:
                db.rollback()
                return _render(permission_error='Informe nome e CPF para o cadastro docente.', edit_user_id=user_id, status=400)
            db.add(ProfessorModel(usuario_id=user_id, nome=name, cpf=cpf))
        if role == 'aluno' and db.query(AlunoModel).filter_by(usuario_id=user_id).first() is None:
            name, number = request.form.get('nome', '').strip(), request.form.get('matricula', '').strip()
            if not name or len(name) > 120 or not number or len(number) > 30:
                db.rollback()
                return _render(permission_error='Informe nome e matricula para o aluno.', edit_user_id=user_id, status=400)
            db.add(AlunoModel(usuario_id=user_id, nome=name, matricula=number, status_matricula='Ativo'))
        if request.form.get('versao') != str(user.auth_version):
            raise MutationConflict('Permissoes alteradas em outra sessao; recarregue a pagina')
        user.tipo, user.revisor_materiais = role, False
        user.auth_version += 1
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return _render(permission_error='CPF ou matricula ja cadastrado.', edit_user_id=user_id, status=409)
    flash('Perfil atualizado. As sessoes anteriores foram revogadas.', 'success')
    return redirect(url_for('gestao.usuarios'))


@gestao_bp.route('/super/layout', methods=['GET', 'POST'])
def layout():
    identity = require_role('super_admin')
    if request.method == 'POST':
        with get_session() as db:
            values = escola.identidade_atual(db)
            values.update(cor_fundo=request.form.get('cor_fundo'), cor_destaque=request.form.get('cor_destaque'))
            values['fundo'], values['destaque'] = values.pop('cor_fundo'), values.pop('cor_destaque')
            values['versao'] = request.form.get('versao')
            escola.salvar_identidade(db, values, identity.id)
            db.commit()
        flash('Aparencia atualizada.', 'success')
        return redirect(url_for('gestao.layout'))
    return render_template('super_layout.html')


@gestao_bp.get('/mensagens')
def mensagens():
    current_identity()
    return render_template('mensagens.html', comunicados=get_comunicados(limit=100))

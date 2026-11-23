from app.services.arquivos_service import _save_profile_photo, _remove_saved_file
import json
import os
from datetime import datetime
from uuid import uuid4

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.auth import generate_token, normalize_role
from app.database import get_session
from app.models import AlunoModel, ProfessorModel, UsuarioModel, SolicitacaoAlteracaoModel
from app.models.usuario_model import normalizar_email
from app.services import limite_login_service as limite
from app.services.senha_service import problema_senha


PROFILE_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}
# Hash ficticio: e-mail inexistente passa pela mesma verificacao (mesmo tempo de resposta).
_HASH_FICTICIO = generate_password_hash("conta-inexistente-nunca-usada")
CREDENCIAIS_INVALIDAS = {"erro": "E-mail ou senha invalidos"}
MAX_PROFILE_PHOTO_BYTES = 2 * 1024 * 1024


def login_usuario(data):
    if not data:
        return {"erro": "Dados nao informados"}, 400

    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha or not isinstance(email, str) or not isinstance(senha, str):
        return {"erro": "E-mail e senha sao obrigatorios"}, 400
    email = normalizar_email(email)

    session = get_session()
    try:
        minutos = limite.minutos_bloqueado(session, email)
        if minutos:
            return {"erro": "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente.",
                    "retry_after": minutos * 60}, 429
        user = session.query(UsuarioModel).filter(UsuarioModel.email == email).first()
        # Mesma resposta e mesmo custo para conta inexistente e senha errada (S6).
        senha_ok = check_password_hash(user.senha if user else _HASH_FICTICIO, senha)
        if not user or not senha_ok:
            limite.registrar_falha(session, email)
            session.commit()
            return CREDENCIAIS_INVALIDAS, 401
        # Senha correta: so entao o estado da conta e revelado (pendente/inativa).
        if user.estado != "ativo":
            resposta = ({"erro": "Cadastro pendente de aprovacao ou acesso inativo"}, 403)
        else:
            role = normalize_role(user.tipo)
            resposta = ({
                "id": user.id,
                "email": user.email,
                "tipo": role.upper(),
                "role": role,
                "auth_version": user.auth_version,
                # O JWT tambem inclui a role para o front enviar nas proximas chamadas protegidas.
                "token": generate_token(user),
            }, 200)
        limite.limpar_conta(session, email)
        session.commit()
        return resposta
    finally:
        session.close()


def _parse_date(value):
    if not value:
        return None

    return datetime.strptime(value, "%Y-%m-%d").date()






def cadastrar_usuario(data, files=None, *, aprovado=False):
    if not data:
        return {"erro": "Dados nao informados"}, 400

    tipo = normalize_role(data.get("tipo") or data.get("role"))
    email = data.get("email")
    senha = data.get("senha")
    nome = data.get("nome")

    if tipo not in {"professor", "aluno"}:
        return {"erro": "Tipo de usuario deve ser professor ou aluno"}, 400

    if not email or not senha or not nome:
        return {"erro": "E-mail, senha e nome sao obrigatorios"}, 400

    erro_senha = problema_senha(senha)
    if erro_senha:
        return {"erro": erro_senha}, 400

    if aprovado:
        from app.services.identidade_service import ADMIN_ROLES, require_role
        require_role(*ADMIN_ROLES)

    foto_perfil, upload_error = _save_profile_photo(files)
    if upload_error:
        return upload_error

    session = get_session()
    try:
        if session.query(UsuarioModel).filter(UsuarioModel.email == normalizar_email(email)).first():
            _remove_saved_file(foto_perfil)
            return {"erro": "E-mail ja cadastrado"}, 409

        usuario = UsuarioModel(
            email=email,
            senha=generate_password_hash(senha),
            # O cadastro agora grava a role do usuario para refletir professor/aluno no JWT.
            tipo=tipo if aprovado else "pendente",
            estado="ativo" if aprovado else "pendente",
            revisor_materiais=False,
        )
        session.add(usuario)
        session.flush()

        if tipo == "professor":
            cpf = data.get("cpf")
            if not cpf:
                session.rollback()
                _remove_saved_file(foto_perfil)
                return {"erro": "CPF e obrigatorio para professor"}, 400

            session.add(
                ProfessorModel(
                    usuario_id=usuario.id,
                    nome=nome,
                    cpf=cpf,
                    telefone=data.get("telefone"),
                    foto_perfil=foto_perfil,
                    disciplina_principal=(
                        data.get("disciplina_principal") or data.get("disciplina")
                    ),
                    formacao_academica=data.get("formacao_academica") or data.get("formacao"),
                    regime_trabalho=data.get("regime_trabalho") or data.get("regime"),
                    data_admissao=_parse_date(data.get("data_admissao") or data.get("admissao")),
                )
            )
        else:
            cpf = data.get("cpf")
            matricula = data.get("matricula")
            if not matricula:
                session.rollback()
                _remove_saved_file(foto_perfil)
                return {"erro": "Matricula e obrigatoria para aluno"}, 400

            session.add(
                AlunoModel(
                    usuario_id=usuario.id,
                    nome=nome,
                    cpf=cpf,
                    matricula=matricula,
                    foto_perfil=foto_perfil,
                    curso_serie=data.get("curso_serie") or data.get("curso"),
                    status_matricula=(data.get("status_matricula") or data.get("status")) if aprovado else "Pendente",
                    data_nascimento=_parse_date(data.get("data_nascimento")),
                )
            )

        if not aprovado:
            session.add(SolicitacaoAlteracaoModel(
                solicitante_id=usuario.id, tipo="cadastro", estado="pendente",
                payload=json.dumps({"usuario_id": usuario.id, "papel_solicitado": tipo}),
                recurso_pendente=f"cadastro:{usuario.id}"))
        session.commit()
        return {
            "id": usuario.id,
            "email": usuario.email,
            "tipo": tipo.upper() if aprovado else "PENDENTE",
            "role": tipo if aprovado else "pendente",
            "estado": usuario.estado,
        }, 201 if aprovado else 202
    except ValueError:
        session.rollback()
        _remove_saved_file(foto_perfil)
        return {"erro": "Data de nascimento deve estar no formato YYYY-MM-DD"}, 400
    except IntegrityError:
        session.rollback()
        _remove_saved_file(foto_perfil)
        return {"erro": "Dados duplicados: verifique CPF, matricula ou e-mail"}, 409
    except Exception:
        session.rollback()
        _remove_saved_file(foto_perfil)
        raise
    finally:
        session.close()


def buscar_alunos(termo):
    from app.services.identidade_service import current_identity
    from app.repositories.pessoas_repository import search_students
    identity = current_identity()
    if identity.papel not in {"professor", "admin", "super_admin"}:
        return {"erro": "Acesso nao autorizado"}, 403
    termo = (termo or "").strip()
    if not termo:
        return {"erro": "Informe um termo de busca"}, 400
    with get_session() as db:
        rows = search_students(db, identity, termo)
        alunos = []
        for aluno in rows:
            data = {"id": aluno.id, "nome": aluno.nome, "matricula": aluno.matricula}
            if identity.admin:
                data["cpf"] = aluno.cpf
                data["data_nascimento"] = aluno.data_nascimento.isoformat() if aluno.data_nascimento else None
            alunos.append(data)
        return {"alunos": alunos}, 200

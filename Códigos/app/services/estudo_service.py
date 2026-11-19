"""Acesso, autoria e publicação de avisos e materiais por turma/disciplina."""
from urllib.parse import urlsplit
from sqlalchemy import and_, func, inspect, or_
from app.concurrency import MutationConflict, check_version
from app.models import (AlunoModel, AlunoTurmaModel, AlunoDisciplinaModel, ProfessorModel,
    ProfessorTurmaModel, ProfessorDisciplinaModel, TurmaModel, DisciplinaModel,
    TurmaDisciplinaModel, AtribuicaoDocenteModel, EstadoTurmaModel, UsuarioModel,
    ConteudoEstudoModel, AuditoriaEstudoModel, SecaoEstudoModel,
    ConteudoSecaoEstudoModel, AuditoriaSecaoEstudoModel)
from app.services.frequencia_service import integer
from app.services.identidade_service import Identidade

PAGE_SIZE = 25
SECTION_TABLES = {'estudo_secoes', 'estudo_conteudo_secao', 'estudo_secao_auditoria'}


def sections_enabled(db):
    tables = set(inspect(db.connection()).get_table_names())
    present = tables & SECTION_TABLES
    if present and present != SECTION_TABLES:
        raise MutationConflict('A organização das abas está temporariamente indisponível. Avise a administração.',503)
    return present == SECTION_TABLES


def sections(db, pair_id, *, archived=False):
    query = db.query(SecaoEstudoModel).filter_by(turma_disciplina_id=pair_id)
    if not archived:
        query = query.filter_by(estado='ativa')
    return query.order_by(SecaoEstudoModel.ordem, SecaoEstudoModel.id).all()


def section_access(db, identity, section_id, *, edit=False, active=False):
    if not sections_enabled(db):
        raise MutationConflict('A organização das abas ainda não foi habilitada nesta instalação.',503)
    query = db.query(SecaoEstudoModel).filter_by(id=integer(section_id))
    row = (query.with_for_update() if edit else query).first()
    if not row:
        raise MutationConflict('Aba não encontrada.',404)
    pair_access(db, identity, row.turma_disciplina_id)
    if edit and not (identity.admin or (identity.papel == 'professor' and row.autor_id == identity.id)):
        raise MutationConflict('Somente o autor ou a administração pode organizar esta aba.',403)
    if row.estado != 'ativa' and (active or identity.papel == 'aluno'):
        raise MutationConflict('Aba arquivada. Seu conteúdo e histórico foram preservados.',404)
    return row


def section_fields(payload):
    name = payload.get('nome')
    if not isinstance(name,str) or not 1 <= len(name.strip()) <= 80 or any(ord(c)<32 for c in name):
        raise MutationConflict('Informe um nome de até 80 caracteres para a aba.',400)
    raw = payload.get('ordem',0)
    if isinstance(raw,bool) or len(str(raw)) > 4 or not str(raw).isascii() or not str(raw).isdigit() or not 0 <= int(raw) <= 9999:
        raise MutationConflict('Informe uma ordem entre 0 e 9999. As menores aparecem primeiro.',400)
    return {'nome':name.strip(),'ordem':int(raw)}


def section_audit(db, row, actor, action):
    db.add(AuditoriaSecaoEstudoModel(secao_id=row.id,ator_id=actor,acao=action,
        nome=row.nome,ordem=row.ordem,estado=row.estado,versao=row.versao))


def content_section(db, identity, row, *, active=False):
    if not sections_enabled(db):
        return None
    mapping = db.get(ConteudoSecaoEstudoModel,row.id)
    if not mapping:
        return None
    section = section_access(db,identity,mapping.secao_id,active=active)
    if section.turma_disciplina_id != row.turma_disciplina_id:
        raise MutationConflict('Conteúdo não encontrado nesta disciplina.',404)
    return section


def assign_section(db, identity, row, section_id):
    if section_id in (None,''):
        return
    section = section_access(db,identity,section_id,edit=True,active=True)
    if section.turma_disciplina_id != row.turma_disciplina_id:
        raise MutationConflict('Escolha uma aba desta disciplina.',400)
    db.add(ConteudoSecaoEstudoModel(conteudo_id=row.id,secao_id=section.id))


def pairs(db, identity):
    query = db.query(TurmaDisciplinaModel, TurmaModel, DisciplinaModel).join(
        TurmaModel, TurmaModel.id == TurmaDisciplinaModel.turma_id).join(
        DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id)
    pair = TurmaDisciplinaModel
    archived = db.query(EstadoTurmaModel.turma_id).filter(
        EstadoTurmaModel.turma_id == pair.turma_id, EstadoTurmaModel.arquivada.is_(True)).exists()
    query = query.filter(~archived)
    if identity.admin:
        return query
    if identity.papel == 'professor':
        teacher = db.query(ProfessorModel).filter_by(usuario_id=identity.id).first()
        if not teacher:
            return query.filter(False)
        explicit = db.query(AtribuicaoDocenteModel.id).filter(
            AtribuicaoDocenteModel.turma_disciplina_id == pair.id,
            AtribuicaoDocenteModel.professor_id == teacher.id,
            AtribuicaoDocenteModel.ativo.is_(True)).exists()
        adopted = db.query(EstadoTurmaModel.turma_id).filter(EstadoTurmaModel.turma_id == pair.turma_id).exists()
        any_assignment = db.query(AtribuicaoDocenteModel.id).filter(AtribuicaoDocenteModel.turma_disciplina_id == pair.id).exists()
        legacy_class = db.query(ProfessorTurmaModel.id).filter(
            ProfessorTurmaModel.professor_id == teacher.id, ProfessorTurmaModel.turma_id == pair.turma_id).exists()
        legacy_subject = db.query(ProfessorDisciplinaModel.id).filter(
            ProfessorDisciplinaModel.professor_id == teacher.id, ProfessorDisciplinaModel.disciplina_id == pair.disciplina_id).exists()
        return query.filter(or_(explicit, and_(~adopted, ~any_assignment, legacy_class, legacy_subject)))
    if identity.papel == 'aluno':
        enrolled = db.query(AlunoModel.id).join(AlunoTurmaModel,
            AlunoTurmaModel.aluno_id == AlunoModel.id).join(AlunoDisciplinaModel,
            AlunoDisciplinaModel.aluno_id == AlunoModel.id).filter(
            AlunoModel.usuario_id == identity.id, AlunoTurmaModel.turma_id == pair.turma_id,
            AlunoDisciplinaModel.disciplina_id == pair.disciplina_id,
            ~func.lower(func.coalesce(AlunoModel.status_matricula, '')).in_(
                ['inativo','inativa','cancelado','cancelada','trancado','trancada'])).exists()
        return query.filter(enrolled)
    return query.filter(False)


def pair_access(db, identity, pair_id):
    row = pairs(db, identity).filter(TurmaDisciplinaModel.id == integer(pair_id)).first()
    if not row:
        raise MutationConflict('Disciplina não encontrada no seu acesso.', 404)
    return row


def content_access(db, identity, content_id, *, edit=False):
    row = db.query(ConteudoEstudoModel).filter_by(id=integer(content_id)).with_for_update().first() if edit else db.get(ConteudoEstudoModel, integer(content_id))
    if not row:
        raise MutationConflict('Conteúdo não encontrado.', 404)
    pair_access(db, identity, row.turma_disciplina_id)
    author = identity.papel == 'professor' and row.autor_id == identity.id
    if edit and not (identity.admin or author):
        raise MutationConflict('Somente o autor ou a administração pode organizar este conteúdo.', 403)
    if not (identity.admin or author) and row.estado != 'publicado':
        raise MutationConflict('Conteúdo não encontrado.', 404)
    content_section(db,identity,row)
    return row


def audit(db, row, actor, action):
    db.add(AuditoriaEstudoModel(conteudo_id=row.id, ator_id=actor, acao=action))


def fields(data, *, kind=None):
    kind = kind or data.get('tipo')
    title, text, link = data.get('titulo'), data.get('texto', ''), data.get('link', '')
    if kind not in {'aviso','link','arquivo'}:
        raise MutationConflict('Escolha aviso, link ou arquivo.', 400)
    if not isinstance(title,str) or not 1 <= len(title.strip()) <= 150:
        raise MutationConflict('Informe um título de até 150 caracteres.',400)
    if not isinstance(text,str) or len(text) > 10000 or (kind == 'aviso' and not text.strip()):
        raise MutationConflict('Informe o texto do aviso (até 10.000 caracteres).',400)
    if not isinstance(link,str) or len(link) > 2048:
        raise MutationConflict('Link inválido.',400)
    link = link.strip()
    if kind == 'link':
        try:
            parsed = urlsplit(link)
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                    or parsed.port not in (None,443) or '\\' in link
                    or any(c.isspace() or ord(c)<32 or ord(c)==127 for c in link)):
                raise ValueError()
        except ValueError:
            raise MutationConflict('Use um link HTTPS válido, sem credenciais.',400)
    elif link:
        raise MutationConflict('O link só pode ser usado no tipo Link.',400)
    return {'tipo':kind,'titulo':title.strip(),'texto':text.strip(),'link':link}


def prepare_publication(db, user_id, data, *, apply=False):
    schema = inspect(db.connection())
    if not all(schema.has_table(name) for name in ('estudo_conteudos','estudo_auditoria')):
        raise MutationConflict('O espaço da disciplina ainda não foi habilitado nesta instalação.',503)
    user = db.get(UsuarioModel,user_id)
    if not user or user.estado != 'ativo' or user.tipo != 'professor':
        raise MutationConflict('Autor sem acesso docente ativo.',403)
    identity = Identidade(user.id,user.tipo,user.revisor_materiais,user.auth_version)
    row = content_access(db,identity,data.get('conteudo_id'),edit=True)
    content_section(db,identity,row,active=True)
    if row.estado != 'rascunho':
        raise MutationConflict('Somente rascunhos podem ser enviados para publicação.')
    version = integer(data.get('versao'))
    if version != row.versao:
        raise MutationConflict('O conteúdo mudou. Reabra o rascunho antes de publicar.')
    if apply:
        check_version(row,data)
        row.estado = 'publicado'
        audit(db,row,user_id,'publicar')
    return {'conteudo_id':row.id,'versao':version}

"""Unidades (colégio e faculdade na mesma instalação): vínculos, unidade ativa e escopo.

Regras (estudo ESTUDO_UNIDADES_2026-11-25 e ficha PROPOSTA_010_UNIDADES_2026-11-25):
- o super admin vê todas as unidades; os demais, só as do vínculo (ativo ou concluído);
- a unidade ativa vem da sessão, mas é conferida no banco a cada requisição;
- recurso de outra unidade responde 404 (não confirma que existe).
"""
from contextlib import contextmanager

from flask import g
from sqlalchemy import func, select, text

from app.concurrency import MutationConflict
from app.models import UnidadeModel, UsuarioUnidadeModel
from app.models.unidade_model import NIVEIS, TODAS

COM_ACESSO = ('ativo', 'concluido')
ROTULOS = {'basico': {'rotulo_serie': 'Série', 'rotulo_periodo': 'Bimestre', 'rotulo_turma': 'Turma'},
           'superior': {'rotulo_serie': 'Semestre', 'rotulo_periodo': 'Semestre', 'rotulo_turma': 'Turma'}}


# ---------- cadastro de unidades e vínculos ----------
def criar_unidade(db, *, nome, nivel, **rotulos):
    if nivel not in NIVEIS:
        raise MutationConflict('Nível de unidade inválido', 400)
    nome = (nome or '').strip()
    if not nome:
        raise MutationConflict('Informe o nome da unidade', 400)
    if db.query(UnidadeModel.id).filter(func.lower(UnidadeModel.nome) == nome.lower()).first():
        raise MutationConflict('Já existe uma unidade com esse nome', 409)
    unidade = UnidadeModel(nome=nome, nivel=nivel, **{**ROTULOS[nivel], **rotulos})
    db.add(unidade)
    db.flush()
    return unidade


def vincular(db, usuario_id, unidade_id, situacao='ativo'):
    """Cria ou reativa o vínculo (idempotente)."""
    if not db.get(UnidadeModel, unidade_id):
        raise MutationConflict('Unidade não encontrada', 404)
    vinculo = db.get(UsuarioUnidadeModel, (usuario_id, unidade_id))
    if vinculo is None:
        vinculo = UsuarioUnidadeModel(usuario_id=usuario_id, unidade_id=unidade_id, situacao=situacao)
        db.add(vinculo)
    elif vinculo.situacao != situacao:
        vinculo.situacao = situacao
        vinculo.alterado_em = func.current_timestamp()
    db.flush()
    return vinculo


def desvincular(db, usuario_id, unidade_id):
    """Revoga o acesso àquela unidade; vale na requisição seguinte (o vínculo é conferido sempre)."""
    vinculo = db.get(UsuarioUnidadeModel, (usuario_id, unidade_id))
    if vinculo is not None and vinculo.situacao != 'revogado':
        vinculo.situacao = 'revogado'
        vinculo.alterado_em = func.current_timestamp()
        db.flush()
    return vinculo


def tem_vinculo(db, usuario_id, unidade_id):
    vinculo = db.get(UsuarioUnidadeModel, (usuario_id, unidade_id))
    return vinculo is not None and vinculo.situacao in COM_ACESSO


def unidades_ativas(db):
    return [u for u, in db.query(UnidadeModel.id).filter_by(estado='ativa').order_by(UnidadeModel.id)]


def unidades_da_conta(db, usuario):
    if str(usuario.tipo).lower() == 'super_admin':
        return unidades_ativas(db)
    return [u for u, in db.query(UsuarioUnidadeModel.unidade_id).join(
        UnidadeModel, UnidadeModel.id == UsuarioUnidadeModel.unidade_id).filter(
        UsuarioUnidadeModel.usuario_id == usuario.id, UsuarioUnidadeModel.situacao.in_(COM_ACESSO),
        UnidadeModel.estado == 'ativa').order_by(UsuarioUnidadeModel.unidade_id)]


def resolver_ativa(permitidas, pedida, super_admin):
    """Unidade ativa a partir do que a sessão pede. Recusa (403) o que não é permitido."""
    if not permitidas:
        raise MutationConflict('Sua conta não tem acesso a nenhuma unidade', 403)
    if pedida in (None, ''):
        return TODAS if super_admin and len(permitidas) > 1 else permitidas[0]
    if pedida == TODAS:
        if not super_admin:
            raise MutationConflict('Somente a direção geral vê todas as unidades', 403)
        return TODAS
    try:
        pedida = int(pedida)
    except (TypeError, ValueError):
        raise MutationConflict('Unidade inválida', 403)
    if pedida not in permitidas:
        raise MutationConflict('Você não tem acesso a esta unidade', 403)
    return pedida


# ---------- escopo da requisição ----------
def ativa():
    """Unidade ativa da requisição (int) ou 'todas' (super admin)."""
    return g.get('unidade_ativa')


def visiveis():
    """Unidades que a requisição pode ver: a ativa ou, na visão "Todas", as permitidas."""
    atual = g.get('unidade_ativa')
    if atual == TODAS:
        return list(g.get('unidades_permitidas') or [])
    return [atual] if isinstance(atual, int) else []


def unidade_para_criar(valor_enviado=None):
    """Unidade de um registro novo: a ativa; na visão "Todas", a escolhida no formulário."""
    atual = g.get('unidade_ativa')
    if isinstance(atual, int):
        return atual
    try:
        escolhida = int(valor_enviado)
    except (TypeError, ValueError):
        raise MutationConflict('Escolha a unidade antes de cadastrar', 422)
    if escolhida not in visiveis():
        raise MutationConflict('Unidade não encontrada', 404)
    return escolhida


def filtrar(query, coluna):
    """Restringe uma consulta às unidades visíveis."""
    return query.filter(coluna.in_(visiveis()))


def contas_visiveis():
    """Subconsulta de contas com vínculo (ativo ou concluído) numa unidade visível."""
    return select(UsuarioUnidadeModel.usuario_id).where(
        UsuarioUnidadeModel.unidade_id.in_(visiveis()), UsuarioUnidadeModel.situacao.in_(COM_ACESSO))


def exigir(condicao):
    """Recurso fora das unidades visíveis: 404, sem confirmar que existe."""
    if not condicao:
        raise MutationConflict('Registro não encontrado', 404)


@contextmanager
def escopo_banco(db, unidades):
    """Informa ao PostgreSQL as unidades da transação (usado pela Row-Level Security da 011)."""
    if db.bind.dialect.name == 'postgresql':
        valor = '*' if unidades == TODAS else ','.join(str(int(u)) for u in unidades)
        db.execute(text("SELECT set_config('edufast.unidades', :v, true)"), {'v': valor})
    yield


# ---------- filtro automático de toda consulta ORM dentro de uma requisição ----------
def _criterios(vis, extras):
    """Critérios por modelo. ``extras``: unidades de origem liberadas só para ler um histórico."""
    from sqlalchemy import or_
    from sqlalchemy.orm import with_loader_criteria
    from app.models import (AlunoModel, ComunicadoModel, DisciplinaModel, DocumentoModel, ProfessorModel,
                            SolicitacaoAlteracaoModel, SolicitacaoDocumentoModel, TransferenciaUnidadeModel,
                            TurmaDisciplinaModel, TurmaModel)
    from app.models.escola_model import CalendarioEscolaModel
    from app.models.frequencia_model import AtestadoModel
    leitura = sorted(set(vis) | set(extras))
    contas = select(UsuarioUnidadeModel.usuario_id).where(UsuarioUnidadeModel.unidade_id.in_(vis),
                                                          UsuarioUnidadeModel.situacao.in_(COM_ACESSO))
    # Regra do usuário: quem subiu para a faculdade leva os documentos do colégio.
    transferidos = select(TransferenciaUnidadeModel.aluno_id).where(TransferenciaUnidadeModel.destino_id.in_(vis))
    por_unidade = [TurmaModel, DisciplinaModel, TurmaDisciplinaModel, SolicitacaoAlteracaoModel,
                   CalendarioEscolaModel, AtestadoModel]
    opcoes = [with_loader_criteria(m, lambda c: c.unidade_id.in_(leitura), include_aliases=True) for m in por_unidade]
    opcoes += [
        with_loader_criteria(AlunoModel, lambda c: c.usuario_id.in_(contas), include_aliases=True),
        with_loader_criteria(ProfessorModel, lambda c: c.usuario_id.in_(contas), include_aliases=True),
        with_loader_criteria(ComunicadoModel, lambda c: or_(c.unidade_id.is_(None), c.unidade_id.in_(vis)),
                             include_aliases=True),
        with_loader_criteria(DocumentoModel, lambda c: or_(c.unidade_id.in_(leitura), c.aluno_id.in_(transferidos)),
                             include_aliases=True),
        with_loader_criteria(SolicitacaoDocumentoModel,
                             lambda c: or_(c.unidade_id.in_(leitura), c.aluno_id.in_(transferidos)),
                             include_aliases=True),
    ]
    return opcoes


def _aplicar_escopo(estado):
    from flask import has_app_context
    if not (estado.is_select or estado.is_update or estado.is_delete) or not has_app_context():
        return
    if estado.execution_options.get('sem_escopo_unidade') or g.get('unidade_ativa') is None:
        return
    chave = (tuple(visiveis()), tuple(g.get('unidades_leitura_extra') or ()))
    cache = g.get('_criterios_unidade')
    if cache is None or cache[0] != chave:  # montados uma vez por requisição (e por escopo)
        cache = g._criterios_unidade = (chave, _criterios(*chave))
    estado.statement = estado.statement.options(*cache[1])


def instalar_escopo():
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    if not event.contains(Session, 'do_orm_execute', _aplicar_escopo):
        event.listen(Session, 'do_orm_execute', _aplicar_escopo)


@contextmanager
def lendo_historico_de(db, aluno_id):
    """Histórico escolar de um aluno que subiu para uma unidade visível: libera, só para leitura
    nesta requisição, as unidades de origem dele (turmas, notas e disciplinas do colégio)."""
    from app.models import TransferenciaUnidadeModel
    origens = [o for o, in db.query(TransferenciaUnidadeModel.origem_id).filter(
        TransferenciaUnidadeModel.aluno_id == aluno_id, TransferenciaUnidadeModel.destino_id.in_(visiveis()))]
    anterior = g.get('unidades_leitura_extra')
    g.unidades_leitura_extra = tuple(origens)
    try:
        yield origens
    finally:
        g.unidades_leitura_extra = anterior


# ---------- pessoa que já existe na instituição (regra do usuário, 25/11/2026) ----------
def _sem_escopo(db, query):
    return query.execution_options(sem_escopo_unidade=True)


def _buscar_por_cpf(db, modelo, cpf):
    digitos = ''.join(ch for ch in str(cpf or '') if ch.isdigit())
    valores = {str(cpf).strip(), digitos} - {''}
    if not valores:
        return None
    return _sem_escopo(db, db.query(modelo).filter(modelo.cpf.in_(valores))).first()


def _registrar_subida(db, aluno, origem_id, destino_id, autor_id, motivo):
    from app.models import TransferenciaUnidadeModel
    db.add(TransferenciaUnidadeModel(aluno_id=aluno.id, origem_id=origem_id, destino_id=destino_id,
                                     autor_id=autor_id, motivo=motivo))
    vincular(db, aluno.usuario_id, destino_id)
    db.flush()


def cadastro_de_quem_ja_existe(db, identity, tipo, cpf, unidade_id):
    """Cadastro pela secretaria com o CPF de alguém que já está na instituição.

    Devolve ``(resposta, status)`` quando o CPF já existe, ou ``None`` para seguir com cadastro novo.
    Nunca devolve dados da outra unidade (nem e-mail, turma ou matrícula).
    """
    from app.models import AlunoModel, ProfessorModel, UnidadeModel
    destino = db.get(UnidadeModel, unidade_id)
    if tipo == 'professor':
        professor = _buscar_por_cpf(db, ProfessorModel, cpf)
        if professor is None:
            return None
        if tem_vinculo(db, professor.usuario_id, unidade_id):
            return {'erro': 'Este professor já está cadastrado nesta unidade.'}, 409
        vincular(db, professor.usuario_id, unidade_id)
        return {'id': professor.id, 'vinculado': True,
                'mensagem': 'Professor já cadastrado na instituição: acesso a esta unidade liberado, com o mesmo login.'}, 200
    aluno = _buscar_por_cpf(db, AlunoModel, cpf)
    if aluno is None:
        return None
    if tem_vinculo(db, aluno.usuario_id, unidade_id):
        lugar = 'na faculdade' if destino.nivel == 'superior' else 'nesta unidade'
        return {'erro': f'Este aluno já está {lugar}.'}, 409
    concluiu = _sem_escopo(db, db.query(UsuarioUnidadeModel).join(
        UnidadeModel, UnidadeModel.id == UsuarioUnidadeModel.unidade_id).filter(
        UsuarioUnidadeModel.usuario_id == aluno.usuario_id, UsuarioUnidadeModel.situacao == 'concluido',
        UnidadeModel.nivel == 'basico')).first()
    if destino.nivel == 'superior' and concluiu is not None:
        _registrar_subida(db, aluno, concluiu.unidade_id, unidade_id, identity.id, 'cpf_concluinte')
        return {'id': aluno.id, 'subiu': True,
                'mensagem': 'Aluno que concluiu o ensino médio na instituição: perfil, histórico escolar e '
                            'documentos trazidos para a faculdade, com o mesmo login.'}, 200
    if destino.nivel == 'superior':
        return {'erro': 'Este CPF pertence a um aluno da instituição que ainda não concluiu o ensino médio. '
                        'Fale com a secretaria do colégio.'}, 409
    return {'erro': 'Este CPF já está cadastrado na instituição. Fale com a secretaria.'}, 409


def concluir_aluno(db, aluno, unidade_id):
    """O colégio marca que o aluno concluiu o último ano (habilita a subida pelo CPF)."""
    vinculo = db.get(UsuarioUnidadeModel, (aluno.usuario_id, unidade_id))
    exigir(vinculo is not None and vinculo.situacao in COM_ACESSO)
    vincular(db, aluno.usuario_id, unidade_id, 'concluido')


def levar_para_unidade(db, aluno, origem_id, destino_id, autor_id):
    """Subida manual (aluno sem CPF): só a unidade de origem libera."""
    from app.models import TransferenciaUnidadeModel, UnidadeModel
    destino = db.get(UnidadeModel, destino_id)
    if destino is None or destino.estado != 'ativa' or destino_id == origem_id:
        raise MutationConflict('Unidade de destino inválida', 400)
    if db.query(TransferenciaUnidadeModel.id).filter_by(aluno_id=aluno.id, destino_id=destino_id).first() \
            or tem_vinculo(db, aluno.usuario_id, destino_id):
        raise MutationConflict('Este aluno já está nessa unidade.', 409)
    vincular(db, aluno.usuario_id, origem_id, 'concluido')
    _registrar_subida(db, aluno, origem_id, destino_id, autor_id, 'manual')


def unidade_do_cadastro_publico(db, valor):
    """Cadastro público: com uma unidade, ela; com várias, a escolhida no formulário (validada)."""
    ativas = unidades_ativas(db)
    if len(ativas) == 1:
        return ativas[0]
    try:
        escolhida = int(valor)
    except (TypeError, ValueError):
        raise MutationConflict('Escolha a unidade (colégio ou faculdade) para o cadastro', 422)
    if escolhida not in ativas:
        raise MutationConflict('Unidade não encontrada', 404)
    return escolhida

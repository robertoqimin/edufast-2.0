"""Unidades (colégio e faculdade na mesma instalação) — migration 010.

No banco, as colunas ``unidade_id`` não têm valor padrão: gravar sem unidade é recusado.
Na aplicação, quem cria uma linha sem dizer a unidade recebe a do contexto:
    1. a unidade ativa da requisição (``g.unidade_ativa``), conferida no banco a cada pedido;
    2. fora de requisição, a ÚNICA unidade ativa da instalação;
    3. com mais de uma unidade e nenhum contexto, a gravação é recusada (MutationConflict 422).
O vínculo de uma conta nova segue a mesma regra, mas sem contexto inequívoco a conta fica
SEM vínculo (sem acesso) em vez de falhar.
Estudo: docs/planejamento/ESTUDO_UNIDADES_2026-11-25.md
"""
from sqlalchemy import (CheckConstraint, ForeignKey, Index, Integer, String, TIMESTAMP, UniqueConstraint,
                        event, func, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

NIVEIS = ('basico', 'superior')
SITUACOES = ('ativo', 'concluido', 'revogado')
TODAS = 'todas'


class UnidadeModel(Base):
    __tablename__ = 'unidades'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    nivel: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, server_default='ativa', default='ativa')
    rotulo_turma: Mapped[str] = mapped_column(String(30), nullable=False, server_default='Turma', default='Turma')
    rotulo_serie: Mapped[str] = mapped_column(String(30), nullable=False, server_default='Série', default='Série')
    rotulo_periodo: Mapped[str] = mapped_column(String(30), nullable=False, server_default='Bimestre', default='Bimestre')
    criado_em: Mapped[object] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    __table_args__ = (UniqueConstraint('nome', name='uq_unidade_nome'),
                      CheckConstraint("nivel IN ('basico', 'superior')", name='ck_unidade_nivel'),
                      CheckConstraint("estado IN ('ativa', 'arquivada')", name='ck_unidade_estado'))


class UsuarioUnidadeModel(Base):
    __tablename__ = 'usuario_unidades'
    usuario_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey('unidades.id'), primary_key=True)
    situacao: Mapped[str] = mapped_column(String(10), nullable=False, server_default='ativo', default='ativo')
    criado_em: Mapped[object] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    alterado_em: Mapped[object | None] = mapped_column(TIMESTAMP)
    __table_args__ = (CheckConstraint("situacao IN ('ativo', 'concluido', 'revogado')", name='ck_vinculo_situacao'),
                      Index('ix_usuario_unidades_unidade', 'unidade_id'))


class TransferenciaUnidadeModel(Base):
    __tablename__ = 'transferencias_unidade'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey('alunos.id'), nullable=False)
    origem_id: Mapped[int] = mapped_column(ForeignKey('unidades.id'), nullable=False)
    destino_id: Mapped[int] = mapped_column(ForeignKey('unidades.id'), nullable=False)
    autor_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    motivo: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[object] = mapped_column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    __table_args__ = (UniqueConstraint('aluno_id', 'destino_id', name='uq_transferencia_aluno_destino'),
                      CheckConstraint('origem_id <> destino_id', name='ck_transferencia_unidades_distintas'),
                      CheckConstraint("motivo IN ('cpf_concluinte', 'manual')", name='ck_transferencia_motivo'),
                      Index('ix_transferencias_destino', 'destino_id'))


# ---------- unidade padrão na aplicação ----------
def _ativa_do_pedido():
    from flask import g, has_app_context
    return g.get('unidade_ativa') if has_app_context() else None


def unidade_unica(conexao):
    ids = [r[0] for r in conexao.execute(text("SELECT id FROM unidades WHERE estado = 'ativa' ORDER BY id"))]
    return ids[0] if len(ids) == 1 else None


def unidade_do_contexto(conexao, *, obrigatoria=True):
    ativa = _ativa_do_pedido()
    if isinstance(ativa, int):
        return ativa
    unica = unidade_unica(conexao)
    if unica is None and obrigatoria:
        from app.concurrency import MutationConflict
        raise MutationConflict('Escolha a unidade antes de cadastrar', 422)
    return unica


def padrao_unidade(context):
    """Default de coluna: unidade ativa do pedido ou a única da instalação."""
    return unidade_do_contexto(context.connection)


def padrao_unidade_ou_todas(context):
    """Comunicados: na visão "Todas" do super admin, NULL = para todas as unidades."""
    if _ativa_do_pedido() == TODAS:
        return None
    return unidade_do_contexto(context.connection)


def _da_linha(tabela, chave):
    def padrao(context):
        valor = context.get_current_parameters().get(chave)
        linha = context.connection.execute(text(f'SELECT unidade_id FROM {tabela} WHERE id = :id'), {'id': valor}).first()
        return linha[0] if linha else unidade_do_contexto(context.connection)
    return padrao


padrao_pela_turma = _da_linha('turmas', 'turma_id')
padrao_pela_disciplina = _da_linha('disciplinas', 'disciplina_id')


@event.listens_for(Base, 'after_insert', propagate=True)
def _vincular_conta_nova(mapper, conexao, alvo):
    """Conta criada recebe vínculo com a unidade onde foi criada (super admin vê todas)."""
    if mapper.class_.__name__ != 'UsuarioModel' or str(alvo.tipo).lower() == 'super_admin':
        return
    unidade = unidade_do_contexto(conexao, obrigatoria=False)
    if unidade is not None:
        conexao.execute(text('INSERT INTO usuario_unidades (usuario_id, unidade_id, situacao) '
                             "VALUES (:u, :d, 'ativo')"), {'u': alvo.id, 'd': unidade})


# ---------- o que a 010 faz além das tabelas (para create_all de testes e desenvolvimento) ----------
# O SQL de produção está em migrations/010_unidades.sql (blocos "base:"), copiado para a base v10.
UNIDADE_INICIAL = ("INSERT INTO unidades (id, nome, nivel) VALUES (1, 'Unidade principal', 'basico')")

_SQLITE_GATILHOS = [
    ('tg_alunos_turmas_vinculo', 'alunos_turmas',
     'SELECT 1 FROM usuario_unidades v JOIN alunos a ON a.usuario_id = v.usuario_id '
     'JOIN turmas t ON t.unidade_id = v.unidade_id WHERE a.id = NEW.aluno_id AND t.id = NEW.turma_id'),
    ('tg_professores_turmas_vinculo', 'professores_turmas',
     'SELECT 1 FROM usuario_unidades v JOIN professores p ON p.usuario_id = v.usuario_id '
     'JOIN turmas t ON t.unidade_id = v.unidade_id WHERE p.id = NEW.professor_id AND t.id = NEW.turma_id'),
    ('tg_atribuicoes_docentes_vinculo', 'atribuicoes_docentes',
     'SELECT 1 FROM usuario_unidades v JOIN professores p ON p.usuario_id = v.usuario_id '
     'JOIN turmas_disciplinas td ON td.unidade_id = v.unidade_id '
     'WHERE p.id = NEW.professor_id AND td.id = NEW.turma_disciplina_id'),
]


def _gatilhos_sqlite():
    for nome, tabela, consulta in _SQLITE_GATILHOS:
        for quando in ('INSERT', 'UPDATE'):
            yield (f"CREATE TRIGGER {nome}_{quando.lower()} BEFORE {quando} ON {tabela} "
                   f"WHEN NOT EXISTS ({consulta} AND v.situacao <> 'revogado') "
                   "BEGIN SELECT RAISE(ABORT, 'pessoa sem vínculo com a unidade da turma'); END")


def _sql_postgresql_da_010():
    """Função e gatilhos do PostgreSQL, lidos do bloco "base:gatilhos" da própria 010 (fonte única)."""
    from pathlib import Path
    sql = (Path(__file__).resolve().parents[2] / 'migrations' / '010_unidades.sql').read_text(encoding='utf-8')
    return sql.split('-- base:gatilhos:inicio')[1].split('-- base:gatilhos:fim')[0]


@event.listens_for(Base.metadata, 'after_create')
def _depois_de_criar(metadata, conexao, **_):
    from sqlalchemy import inspect
    tabelas = set(inspect(conexao).get_table_names())
    if 'unidades' not in tabelas:
        return  # esquema parcial (ex.: legado montado pelos testes de migration)
    if conexao.execute(text('SELECT count(*) FROM unidades')).scalar() == 0:
        conexao.execute(text(UNIDADE_INICIAL))
        if conexao.dialect.name == 'postgresql':
            conexao.execute(text("SELECT setval(pg_get_serial_sequence('unidades', 'id'), 1)"))
    if not {'usuario_unidades', 'alunos_turmas', 'professores_turmas', 'atribuicoes_docentes'} <= tabelas:
        return
    if conexao.dialect.name == 'sqlite':
        for nome in [g for n, _, _ in _SQLITE_GATILHOS for g in (n + '_insert', n + '_update')]:
            conexao.execute(text(f'DROP TRIGGER IF EXISTS {nome}'))
        for ddl in _gatilhos_sqlite():
            conexao.execute(text(ddl))
    elif conexao.dialect.name == 'postgresql':
        existe = conexao.execute(text("SELECT 1 FROM pg_trigger WHERE tgname = 'tg_alunos_turmas_vinculo' "
                                      "AND tgrelid = to_regclass('alunos_turmas')")).first()
        if not existe:
            # drop_all dos testes apaga as tabelas, mas não a função: recriar sem erro.
            # exec_driver_sql formata parâmetros: o '%' do RAISE precisa ir dobrado.
            sql = _sql_postgresql_da_010().replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION')
            conexao.exec_driver_sql(sql.replace('%', '%%'))


__all__ = ['UnidadeModel', 'UsuarioUnidadeModel', 'TransferenciaUnidadeModel', 'TODAS', 'NIVEIS', 'SITUACOES',
           'padrao_unidade', 'padrao_unidade_ou_todas', 'padrao_pela_turma', 'padrao_pela_disciplina',
           'unidade_do_contexto', 'unidade_unica']

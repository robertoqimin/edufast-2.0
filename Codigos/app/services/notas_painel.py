"""Leituras de notas para os painéis (B1): a única fonte é o módulo acadêmico.

Nada aqui grava. O professor lança pelo diário da avaliação, onde cada ação continua
sendo uma solicitação aprovada pela secretaria; o aluno vê só avaliações publicadas.
"""
import json

from sqlalchemy import func, inspect

from app.models import (AlunoModel, AlunoTurmaModel, DisciplinaModel, SolicitacaoAlteracaoModel,
                        TurmaDisciplinaModel, TurmaModel)
from app.models.academico_model import AvaliacaoModel, LancamentoNotaModel, PeriodoLetivoModel
from app.models.curso_model import AtribuicaoDocenteModel, EstadoTurmaModel


def disponivel(db):
    # Inspeciona pela conexao da sessao: uma conexao nova quebra o SQLite em memoria (conexao unica).
    return inspect(db.connection()).has_table('academico_notas')


def _formatar(valor):
    return str(valor) if valor is not None else None


def _data(valor):
    return valor.strftime('%d/%m/%Y') if valor else '-'


def _pendencias(db, usuario_id):
    """Solicitações do professor ainda sem decisão, por avaliação."""
    lancamentos, publicacoes = {}, set()
    rows = db.query(SolicitacaoAlteracaoModel.payload).filter_by(
        solicitante_id=usuario_id, tipo='operacao_restaurada', estado='pendente')
    for (payload,) in rows:
        try:
            data = json.loads(payload)
            avaliacao_id = int(data.get('params', {}).get('avaliacao_id'))
        except (TypeError, ValueError, AttributeError):
            continue
        if data.get('endpoint') == 'academico.lancar':
            lancamentos[avaliacao_id] = lancamentos.get(avaliacao_id, 0) + 1
        elif data.get('endpoint') == 'academico.publicar':
            publicacoes.add(avaliacao_id)
    return lancamentos, publicacoes


def diario_professor(db, professor, usuario_id):
    if not disponivel(db):
        return {'disponivel': False, 'ofertas': [], 'recentes': []}
    ofertas = (db.query(TurmaDisciplinaModel, TurmaModel, DisciplinaModel)
               .join(TurmaModel, TurmaModel.id == TurmaDisciplinaModel.turma_id)
               .join(DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id)
               .join(AtribuicaoDocenteModel, AtribuicaoDocenteModel.turma_disciplina_id == TurmaDisciplinaModel.id)
               .filter(AtribuicaoDocenteModel.professor_id == professor.id, AtribuicaoDocenteModel.ativo.is_(True))
               .order_by(TurmaModel.ano_letivo.desc(), TurmaModel.nome, DisciplinaModel.nome).all())
    vinculos = [v.id for v, _, _ in ofertas]
    turmas = {t.id for _, t, _ in ofertas}
    avaliacoes = (db.query(AvaliacaoModel, PeriodoLetivoModel)
                  .join(PeriodoLetivoModel, PeriodoLetivoModel.id == AvaliacaoModel.periodo_id)
                  .filter(AvaliacaoModel.turma_disciplina_id.in_(vinculos))
                  .order_by(PeriodoLetivoModel.ordem, AvaliacaoModel.id).all()) if vinculos else []
    ids = [a.id for a, _ in avaliacoes]
    lancadas = dict(db.query(LancamentoNotaModel.avaliacao_id, func.count(LancamentoNotaModel.id))
                    .filter(LancamentoNotaModel.avaliacao_id.in_(ids))
                    .group_by(LancamentoNotaModel.avaliacao_id).all()) if ids else {}
    alunos = dict(db.query(AlunoTurmaModel.turma_id, func.count(AlunoTurmaModel.id))
                  .filter(AlunoTurmaModel.turma_id.in_(turmas))
                  .group_by(AlunoTurmaModel.turma_id).all()) if turmas else {}
    prontas = {e.turma_id for e in db.query(EstadoTurmaModel).filter(
        EstadoTurmaModel.turma_id.in_(turmas), EstadoTurmaModel.arquivada.is_(False))} if turmas else set()
    pendentes, publicando = _pendencias(db, usuario_id)
    por_vinculo = {}
    for avaliacao, periodo in avaliacoes:
        estado = ('Publicada' if avaliacao.publicada else
                  'Publicação aguardando aprovação' if avaliacao.id in publicando else 'Rascunho')
        por_vinculo.setdefault(avaliacao.turma_disciplina_id, []).append({
            'id': avaliacao.id, 'titulo': avaliacao.titulo, 'periodo': periodo.nome, 'peso': _formatar(avaliacao.peso),
            'estado': estado, 'lancadas': lancadas.get(avaliacao.id, 0), 'pendentes': pendentes.get(avaliacao.id, 0)})
    resultado = [{'id': v.id, 'turma': t.nome, 'ano': t.ano_letivo, 'disciplina': d.nome,
                  'pronta': t.id in prontas, 'alunos': alunos.get(t.id, 0),
                  'avaliacoes': por_vinculo.get(v.id, [])} for v, t, d in ofertas]
    recentes = (db.query(LancamentoNotaModel, AlunoModel, AvaliacaoModel, PeriodoLetivoModel, TurmaModel, DisciplinaModel)
                .join(AlunoModel, AlunoModel.id == LancamentoNotaModel.aluno_id)
                .join(AvaliacaoModel, AvaliacaoModel.id == LancamentoNotaModel.avaliacao_id)
                .join(PeriodoLetivoModel, PeriodoLetivoModel.id == AvaliacaoModel.periodo_id)
                .join(TurmaDisciplinaModel, TurmaDisciplinaModel.id == AvaliacaoModel.turma_disciplina_id)
                .join(TurmaModel, TurmaModel.id == TurmaDisciplinaModel.turma_id)
                .join(DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id)
                .filter(LancamentoNotaModel.professor_id == professor.id,
                        AvaliacaoModel.turma_disciplina_id.in_(vinculos))
                .order_by(LancamentoNotaModel.atualizada_em.desc(), LancamentoNotaModel.id.desc()).limit(30).all()) if vinculos else []
    return {'disponivel': True, 'ofertas': resultado, 'recentes': [
        {'aluno': aluno.nome, 'matricula': aluno.matricula, 'turma': turma.nome, 'disciplina': disciplina.nome,
         'avaliacao': avaliacao.titulo, 'avaliacao_id': avaliacao.id, 'periodo': periodo.nome,
         'nota': _formatar(nota.valor), 'observacao': nota.observacao or '-',
         'estado': 'Publicada' if avaliacao.publicada else 'Rascunho', 'data': _data(nota.atualizada_em)}
        for nota, aluno, avaliacao, periodo, turma, disciplina in recentes]}


def resumo_aluno(db, aluno_id):
    """Resumo do boletim publicado; notas antigas só aparecem no boletim, à parte."""
    if not disponivel(db):
        return {'disponivel': False, 'periodos': [], 'anteriores': 0}
    from app.services.academico import boletim
    dados = boletim(db, aluno_id)
    periodos = [{'disciplina': item['disciplina'], 'turma': item['turma'], 'ano': item['ano'],
                 'periodo': item['periodo'], 'media': item['media'], 'situacao': item['situacao'],
                 'notas': [{'titulo': a['titulo'], 'nota': a['nota']} for a in item['avaliacoes'] if a['nota'] is not None]}
                for item in dados['periodos']]
    return {'disponivel': True, 'periodos': periodos, 'anteriores': len(dados['legadas'])}


def ultimas_do_professor(db, professor_id, limite=10):
    """Últimas notas do diário lançadas pelo professor, para a secretaria."""
    if not disponivel(db):
        return []
    return (db.query(LancamentoNotaModel, AlunoModel, DisciplinaModel, AvaliacaoModel, PeriodoLetivoModel)
            .join(AlunoModel, AlunoModel.id == LancamentoNotaModel.aluno_id)
            .join(AvaliacaoModel, AvaliacaoModel.id == LancamentoNotaModel.avaliacao_id)
            .join(PeriodoLetivoModel, PeriodoLetivoModel.id == AvaliacaoModel.periodo_id)
            .join(TurmaDisciplinaModel, TurmaDisciplinaModel.id == AvaliacaoModel.turma_disciplina_id)
            .join(DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id)
            .filter(LancamentoNotaModel.professor_id == professor_id)
            .order_by(LancamentoNotaModel.atualizada_em.desc(), LancamentoNotaModel.id.desc()).limit(limite).all())

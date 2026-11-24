"""Matrícula do aluno nas disciplinas da própria turma.

O Espaço da disciplina, os cursos e o acesso a materiais exigem que o aluno esteja na turma
**e** na disciplina (`alunos_disciplinas`). Nenhuma tela criava esta segunda matrícula, então
alunos cadastrados pela interface não viam conteúdo. Regra: ao entrar numa turma, o aluno é
matriculado nas disciplinas oferecidas nela; quando a turma ganha uma disciplina, os alunos
dela também. Nunca concede disciplina de outra turma.
"""
from app.concurrency import insert_if_missing
from app.models import AlunoDisciplinaModel, AlunoTurmaModel, TurmaDisciplinaModel


def sincronizar_turma(db, turma_id):
    """Garante aluno × disciplina para todos os alunos e disciplinas da turma (idempotente)."""
    alunos = [a for a, in db.query(AlunoTurmaModel.aluno_id).filter_by(turma_id=turma_id)]
    disciplinas = [d for d, in db.query(TurmaDisciplinaModel.disciplina_id).filter_by(turma_id=turma_id)]
    for aluno_id in alunos:
        for disciplina_id in disciplinas:
            insert_if_missing(db, AlunoDisciplinaModel, aluno_id=aluno_id, disciplina_id=disciplina_id)


def remover_da_turma(db, aluno_id, turma_id):
    """Ao sair da turma, retira as disciplinas dela que o aluno não cursa em outra turma."""
    da_turma = {d for d, in db.query(TurmaDisciplinaModel.disciplina_id).filter_by(turma_id=turma_id)}
    outras_turmas = [t for t, in db.query(AlunoTurmaModel.turma_id).filter(
        AlunoTurmaModel.aluno_id == aluno_id, AlunoTurmaModel.turma_id != turma_id)]
    mantidas = {d for d, in db.query(TurmaDisciplinaModel.disciplina_id).filter(
        TurmaDisciplinaModel.turma_id.in_(outras_turmas))} if outras_turmas else set()
    remover = da_turma - mantidas
    if remover:
        db.query(AlunoDisciplinaModel).filter(AlunoDisciplinaModel.aluno_id == aluno_id,
            AlunoDisciplinaModel.disciplina_id.in_(remover)).delete(synchronize_session=False)

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


# A turma é a unidade que se matricula na matéria: registrar a turma numa disciplina matricula
# todos os seus alunos de uma vez, e quem entrar na turma depois herda todas as matérias dela.
# Assim, no ano seguinte, basta registrar a turma nas novas matérias e associar os professores.

def registrar_disciplina(db, turma_id, disciplina_id):
    """Registra a turma na disciplina e matricula todos os alunos dela (idempotente)."""
    vinculo = insert_if_missing(db, TurmaDisciplinaModel, turma_id=turma_id, disciplina_id=disciplina_id)
    sincronizar_turma(db, turma_id)
    return vinculo


def historico_da_disciplina(db, vinculo_id):
    """Indica se a matéria já tem registros na turma (notas, chamadas, materiais, cursos ou docência)."""
    from sqlalchemy import inspect
    from app.models import (AtribuicaoDocenteModel, AvaliacaoModel, ConteudoEstudoModel, OfertaCursoModel,
                            SecaoEstudoModel)
    from app.models.frequencia_model import ChamadaModel
    existentes = set(inspect(db.connection()).get_table_names())  # módulos opcionais por instalação
    return any(db.query(model.id).filter(model.turma_disciplina_id == vinculo_id).first() is not None
               for model in (AvaliacaoModel, ChamadaModel, ConteudoEstudoModel, SecaoEstudoModel,
                             OfertaCursoModel, AtribuicaoDocenteModel)
               if model.__tablename__ in existentes)


def retirar_disciplina(db, vinculo):
    """Retira a matéria da turma; o aluno só a perde se não a cursa por outra turma."""
    alunos = [a for a, in db.query(AlunoTurmaModel.aluno_id).filter_by(turma_id=vinculo.turma_id)]
    if alunos:
        outras_turmas = db.query(AlunoTurmaModel.aluno_id).join(TurmaDisciplinaModel,
            TurmaDisciplinaModel.turma_id == AlunoTurmaModel.turma_id).filter(
            AlunoTurmaModel.aluno_id.in_(alunos), AlunoTurmaModel.turma_id != vinculo.turma_id,
            TurmaDisciplinaModel.disciplina_id == vinculo.disciplina_id)
        mantidos = {a for a, in outras_turmas}
        perdem = [a for a in alunos if a not in mantidos]
        if perdem:
            db.query(AlunoDisciplinaModel).filter(AlunoDisciplinaModel.disciplina_id == vinculo.disciplina_id,
                AlunoDisciplinaModel.aluno_id.in_(perdem)).delete(synchronize_session=False)
    db.delete(vinculo)

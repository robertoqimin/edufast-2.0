"""U4/O2: checklist "Primeiros passos" da implantação, calculado dos dados (nada novo é gravado).

Ordem de uma escola nova: calendário → regras do boletim → equipe → disciplinas → turma →
disciplinas e professores da turma → alunos → boletim aplicado às turmas → (cursos, opcional).
Passos da direção (superperfil) aparecem para a secretaria como "A cargo da direção", sem link.
"""
from flask import url_for
from sqlalchemy import func

DIRECAO, SECRETARIA = 'direcao', 'secretaria'


def _turmas_ativas(db):
    from app.models import TurmaModel
    from app.models.curso_model import EstadoTurmaModel
    arquivadas = db.query(EstadoTurmaModel.turma_id).filter(EstadoTurmaModel.arquivada.is_(True))
    return [t for t, in db.query(TurmaModel.id).filter(~TurmaModel.id.in_(arquivadas)).all()]


def _com(db, coluna, turmas):
    return {t for t, in db.query(coluna).filter(coluna.in_(turmas)).distinct()} if turmas else set()


def resumo(db, papel, cursos_ms04=False):
    from app.models import AlunoTurmaModel, DisciplinaModel, TurmaDisciplinaModel, UsuarioModel
    from app.models.curso_model import AtribuicaoDocenteModel, OfertaCursoModel
    from app.models.escola_model import CalendarioEscolaModel, PoliticaEscolaModel, RegraTurmaEscolaModel

    turmas = _turmas_ativas(db)
    n_turmas = len(turmas)
    calendarios = db.query(CalendarioEscolaModel.ano).order_by(CalendarioEscolaModel.ano).all()
    politicas = db.query(func.count(PoliticaEscolaModel.id)).scalar()
    contas = dict(db.query(UsuarioModel.tipo, func.count(UsuarioModel.id)).filter(
        UsuarioModel.estado == 'ativo', UsuarioModel.tipo.in_(['admin', 'professor'])).group_by(UsuarioModel.tipo).all())
    disciplinas = db.query(func.count(DisciplinaModel.id)).scalar()
    com_professor = {t for t, in db.query(TurmaDisciplinaModel.turma_id).join(
        AtribuicaoDocenteModel, AtribuicaoDocenteModel.turma_disciplina_id == TurmaDisciplinaModel.id).filter(
        AtribuicaoDocenteModel.ativo.is_(True), TurmaDisciplinaModel.turma_id.in_(turmas or [0])).distinct()}
    com_alunos = _com(db, AlunoTurmaModel.turma_id, turmas)
    matriculas = db.query(func.count(AlunoTurmaModel.aluno_id)).filter(AlunoTurmaModel.turma_id.in_(turmas or [0])).scalar()
    com_boletim = _com(db, RegraTurmaEscolaModel.turma_id, turmas)
    ofertas = db.query(func.count(OfertaCursoModel.id)).filter(OfertaCursoModel.ativa.is_(True)).scalar()

    def todas(conjunto):
        return n_turmas > 0 and len(conjunto) == n_turmas

    def de(conjunto):
        return f'{len(conjunto)} de {n_turmas} turmas' if n_turmas else 'Crie uma turma antes'

    gestao = 'cursos.gestao_turmas'
    passos = [
        ('calendario', 'Calendário escolar do ano', 'Início, fim, dias letivos, feriados e recessos.',
         bool(calendarios), DIRECAO, 'escola.configurar', 'Cadastrar o calendário',
         'Calendário ' + ', '.join(str(a) for a, in calendarios) if calendarios else 'Nenhum calendário'),
        ('boletim', 'Regras do boletim', 'Divisão do ano (bimestres, trimestres…), pesos e período de cada etapa.',
         politicas > 0, DIRECAO, 'escola.configurar', 'Definir as regras', f'{politicas} regra(s) criada(s)'),
        ('equipe', 'Contas da equipe', 'Acesso para a secretaria e para cada professor.',
         contas.get('admin', 0) > 0 and contas.get('professor', 0) > 0, DIRECAO, 'gestao.usuarios', 'Criar as contas',
         f"{contas.get('admin', 0)} na secretaria · {contas.get('professor', 0)} professores"),
        ('disciplinas', 'Disciplinas', 'As matérias oferecidas pela escola (Matemática, Língua Portuguesa…).',
         disciplinas > 0, SECRETARIA, 'home.admin_disciplinas', 'Cadastrar disciplinas', f'{disciplinas} cadastrada(s)'),
        ('turmas', 'Turmas do ano', 'Cada turma com nome, código e ano letivo.',
         n_turmas > 0, SECRETARIA, gestao, 'Criar a turma', f'{n_turmas} turma(s) ativa(s)'),
        ('professores', 'Disciplinas e professores de cada turma', 'Quem dá cada matéria em cada turma: libera diário e chamada.',
         todas(com_professor), SECRETARIA, gestao, 'Atribuir professores', de(com_professor)),
        ('alunos', 'Alunos matriculados', 'Cada aluno na sua turma, para ver materiais, notas e frequência.',
         todas(com_alunos), SECRETARIA, gestao, 'Matricular alunos', f'{matriculas} matrícula(s) · {de(com_alunos)}'),
        ('boletim_turmas', 'Boletim aplicado às turmas', 'Aplica as regras do boletim e cria os períodos de cada turma.',
         todas(com_boletim), DIRECAO, 'escola.configurar', 'Aplicar o boletim', de(com_boletim)),
        ('cursos', 'Cursos liberados para as turmas', 'Opcional: cursos de aprendizagem publicados e liberados pela secretaria.',
         ofertas > 0, SECRETARIA, 'cursos_web.biblioteca' if cursos_ms04 else 'cursos.biblioteca', 'Abrir os cursos',
         f'{ofertas} liberação(ões) ativa(s)'),
    ]
    itens, proximo = [], None
    for chave, titulo, descricao, feito, quem, endpoint, acao, detalhe in passos:
        opcional = chave == 'cursos'
        pode = papel == 'super_admin' or quem == SECRETARIA
        item = {'chave': chave, 'titulo': titulo, 'descricao': descricao, 'feito': feito, 'opcional': opcional,
                'quem': 'Direção' if quem == DIRECAO else 'Secretaria', 'pode': pode, 'acao': acao, 'detalhe': detalhe,
                'url': url_for(endpoint) if pode else None}
        if not feito and not opcional and proximo is None:
            proximo = chave
        itens.append(item)
    obrigatorios = [i for i in itens if not i['opcional']]
    feitos = sum(i['feito'] for i in obrigatorios)
    return {'passos': itens, 'feitos': feitos, 'total': len(obrigatorios), 'proximo': proximo,
            'concluido': feitos == len(obrigatorios), 'percentual': round(100 * feitos / len(obrigatorios))}

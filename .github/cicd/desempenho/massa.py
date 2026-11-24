"""Massa sintética determinística para medir desempenho (B3/MS05). Só dados fictícios.

Uma escola com turmas, disciplinas, professores atribuídos, períodos, avaliações com notas,
chamadas aprovadas com presenças, cursos ofertados com progresso, comunicados e solicitações.
"""
import json
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app.database import get_session
from app.models import (AlunoDisciplinaModel, AlunoModel, AlunoTurmaModel, ComunicadoModel, DisciplinaModel,
                        ProfessorDisciplinaModel, ProfessorModel, ProfessorTurmaModel, SolicitacaoAlteracaoModel,
                        TurmaDisciplinaModel, TurmaModel, UsuarioModel)
from app.models.academico_model import AvaliacaoModel, LancamentoNotaModel, PeriodoLetivoModel
from app.models.curso_model import (AtribuicaoDocenteModel, AulaModel, CapituloModel, CursoModel, EstadoTurmaModel,
                                    OfertaCursoModel, ProgressoAulaModel, TemaModel)
from app.models.frequencia_model import ChamadaModel, PresencaModel

SENHA = 'Medicao-sintetica-2026!'
ESCALAS = {
    'pequena': {'turmas': 3, 'alunos': 20, 'disciplinas': 4, 'chamadas': 5},
    'padrao': {'turmas': 10, 'alunos': 35, 'disciplinas': 8, 'chamadas': 20},
}


def popular(escala='padrao', semente=2026):
    cfg = ESCALAS[escala]
    rnd = random.Random(semente)
    senha = generate_password_hash(SENHA)
    contagem = {}
    with get_session() as db:
        def lote(rows, nome):
            db.add_all(rows)
            db.flush()
            contagem[nome] = contagem.get(nome, 0) + len(rows)
            return rows

        usuarios = [UsuarioModel(id=1, email='admin@medicao.test', tipo='admin', estado='ativo', senha=senha)]
        disciplinas = lote([DisciplinaModel(id=d + 1, nome=f'Disciplina {d + 1:02d}', codigo=f'D{d + 1:02d}', carga_horaria=80)
                            for d in range(cfg['disciplinas'])], 'disciplinas')
        turmas = lote([TurmaModel(id=t + 1, nome=f'{t // 4 + 1}º ano {"ABCD"[t % 4]}', codigo=f'T{t + 1:02d}',
                                  ano_letivo=2026, turno='Matutino') for t in range(cfg['turmas'])], 'turmas')
        # Um professor por disciplina, responsável por ela em todas as turmas.
        for d in disciplinas:
            usuarios.append(UsuarioModel(id=100 + d.id, email=f'professor{d.id:02d}@medicao.test', tipo='professor',
                                         estado='ativo', senha=senha))
        alunos_usuarios = []
        uid = 1000
        for t in turmas:
            for _ in range(cfg['alunos']):
                uid += 1
                alunos_usuarios.append(UsuarioModel(id=uid, email=f'aluno{uid}@medicao.test', tipo='aluno',
                                                    estado='ativo', senha=senha))
        lote(usuarios + alunos_usuarios, 'usuarios')
        professores = lote([ProfessorModel(id=d.id, usuario_id=100 + d.id, nome=f'Professor {d.id:02d}',
                                           cpf=f'{d.id:011d}', disciplina_principal=d.nome) for d in disciplinas], 'professores')
        alunos = lote([AlunoModel(id=i + 1, usuario_id=u.id, nome=f'Aluno Sintetico {i + 1:04d}', matricula=f'2026-{i + 1:05d}',
                                  cpf=f'{90000000000 + i}', status_matricula='Ativo', curso_serie='Médio')
                       for i, u in enumerate(alunos_usuarios)], 'alunos')
        por_turma = {t.id: alunos[i * cfg['alunos']:(i + 1) * cfg['alunos']] for i, t in enumerate(turmas)}
        vinculos = lote([TurmaDisciplinaModel(id=t.id * 100 + d.id, turma_id=t.id, disciplina_id=d.id)
                         for t in turmas for d in disciplinas], 'turmas_disciplinas')
        lote([AlunoTurmaModel(aluno_id=a.id, turma_id=t) for t, lista in por_turma.items() for a in lista], 'matriculas_turma')
        lote([AlunoDisciplinaModel(aluno_id=a.id, disciplina_id=d.id) for a in alunos for d in disciplinas], 'matriculas_disciplina')
        lote([ProfessorTurmaModel(professor_id=p.id, turma_id=t.id) for p in professores for t in turmas], 'professor_turma')
        lote([ProfessorDisciplinaModel(professor_id=p.id, disciplina_id=p.id) for p in professores], 'professor_disciplina')
        lote([AtribuicaoDocenteModel(professor_id=v.disciplina_id, turma_disciplina_id=v.id, ativo=True) for v in vinculos],
             'atribuicoes')
        lote([EstadoTurmaModel(turma_id=t.id, arquivada=False) for t in turmas], 'turmas_revisadas')
        periodos = lote([PeriodoLetivoModel(id=t.id * 10 + o, turma_id=t.id, nome=f'{o}º bimestre', ordem=o,
                                            media_referencia=6, fechado=o == 1) for t in turmas for o in range(1, 5)], 'periodos')
        avaliacoes = []
        for v in vinculos:
            for o in range(1, 5):
                for k in range(2):
                    avaliacoes.append(AvaliacaoModel(turma_disciplina_id=v.id, periodo_id=v.turma_id * 10 + o,
                                                     titulo=('Prova' if k == 0 else 'Trabalho') + f' {o}º bim',
                                                     peso=2 if k == 0 else 1, publicada=o <= 3))
        lote(avaliacoes, 'avaliacoes')
        notas = []
        for av in avaliacoes:
            turma = av.turma_disciplina_id // 100
            if av.periodo_id % 10 == 4:
                continue
            for a in por_turma[turma]:
                notas.append(LancamentoNotaModel(avaliacao_id=av.id, aluno_id=a.id, professor_id=av.turma_disciplina_id % 100,
                                                 valor=f'{rnd.randint(30, 100) / 10:.2f}', observacao='', versao=1))
        lote(notas, 'notas')
        inicio = date(2026, 2, 2)
        chamadas = []
        for v in vinculos:
            for n in range(cfg['chamadas']):
                chamadas.append(ChamadaModel(turma_disciplina_id=v.id, dia=inicio + timedelta(days=7 * n + v.disciplina_id % 5),
                                             aula=1, revisao=1, autor_id=100 + v.disciplina_id, estado='aprovada',
                                             decidido_por=1, versao=1, motivo='', decisao_motivo=''))
        lote(chamadas, 'chamadas')
        lote([PresencaModel(chamada_id=c.id, aluno_id=a.id, situacao='falta' if rnd.random() < 0.08 else 'presente')
              for c in chamadas for a in por_turma[c.turma_disciplina_id // 100]], 'presencas')
        cursos, ofertas = [], []
        for d in disciplinas:
            curso = CursoModel(disciplina_id=d.id, professor_id=d.id, titulo=f'Curso de revisão {d.nome}', descricao='', estado='publicado')
            db.add(curso)
            db.flush()
            cursos.append(curso)
            for c in range(2):
                cap = CapituloModel(curso_id=curso.id, titulo=f'Capítulo {c + 1}', posicao=c + 1)
                db.add(cap)
                db.flush()
                tema = TemaModel(capitulo_id=cap.id, titulo='Tema', posicao=1)
                db.add(tema)
                db.flush()
                db.add_all([AulaModel(tema_id=tema.id, titulo=f'Aula {c + 1}.{a + 1}', video_id='abcdefghijk', posicao=a + 1)
                            for a in range(3)])
            db.flush()
            for v in vinculos:
                if v.disciplina_id == d.id:
                    ofertas.append(OfertaCursoModel(curso_id=curso.id, turma_disciplina_id=v.id, ativa=True))
        contagem['cursos'] = len(cursos)
        lote(ofertas, 'ofertas')
        aulas_por_curso = {}
        for aula, curso_id in db.query(AulaModel, CapituloModel.curso_id).join(TemaModel, TemaModel.id == AulaModel.tema_id).join(
                CapituloModel, CapituloModel.id == TemaModel.capitulo_id):
            aulas_por_curso.setdefault(curso_id, []).append(aula.id)
        progresso = []
        for o in ofertas:
            for a in por_turma[o.turma_disciplina_id // 100]:
                for aula_id in aulas_por_curso[o.curso_id][:rnd.randint(0, 3)]:
                    progresso.append(ProgressoAulaModel(aluno_id=a.id, oferta_id=o.id, aula_id=aula_id))
        lote(progresso, 'progresso')
        lote([ComunicadoModel(titulo=f'Comunicado {i + 1}', destinatario='Todos', mensagem='Aviso sintético. ' * 8,
                              criado_por='Secretaria') for i in range(40)], 'comunicados')
        lote([SolicitacaoAlteracaoModel(solicitante_id=100 + disciplinas[i % len(disciplinas)].id, tipo='operacao_restaurada',
                                        estado='pendente', payload=json.dumps({'endpoint': 'academico.lancar',
                                        'params': {'avaliacao_id': avaliacoes[i].id, 'aluno_id': 1},
                                        'payload': {'valor': '7', 'versao': 1}})) for i in range(20)], 'solicitacoes')
        db.commit()
    return contagem

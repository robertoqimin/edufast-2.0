"""C1 — escola fictícia completa para demonstração. Recusa qualquer banco que não seja o da demo.

Uso (dentro do container da demo): EDUFAST_DEMO_COMPLETA=1 python demo_completa.py
Cria: identidade da escola, contas de todos os perfis, turma de ensino médio com três
disciplinas e professores atribuídos, calendário e regras do boletim (bimestres) aplicados,
avaliações com notas publicadas (1º bimestre fechado), chamadas, avisos, materiais (PDF e
imagem), abas e o curso de Matemática para o ENEM. Conteúdo com arquivo, criptografia ou
aprovação passa pelas rotas reais do sistema. Somente dados fictícios.
"""
import io
import json
import os
import random
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect
from werkzeug.security import generate_password_hash

from app.database import engine, get_session
from config import Config

SENHA = 'Demo-EduFast-2026!'
DOMINIO = 'demo.edufast.test'
ESCOLA = 'Colégio Horizonte'
PROFESSORES = [('ana.ribeiro', 'Ana Ribeiro', 'Matemática'), ('carlos.mendes', 'Carlos Mendes', 'Língua Portuguesa'),
               ('beatriz.lopes', 'Beatriz Lopes', 'Biologia')]
ALUNOS = ['Bruno Lima', 'Carla Souza', 'Diego Ferreira', 'Elisa Rocha', 'Felipe Araújo', 'Gabriela Nunes',
          'Heitor Campos', 'Isabela Martins', 'João Pedro Alves', 'Larissa Duarte', 'Mateus Oliveira', 'Natália Costa']
DISCIPLINAS = [('MAT1', 'Matemática', 120), ('POR1', 'Língua Portuguesa', 120), ('BIO1', 'Biologia', 80)]
DEMO = Path(__file__).parent / 'demo'


def slug(nome):
    sem_acento = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode()
    return sem_acento.lower().replace(' ', '.')


def email(usuario):
    return f'{usuario}@{DOMINIO}'


def contas():
    """Tabela de acessos impressa pelo iniciador."""
    linhas = [('Super admin (direção)', email('diretoria')), ('Admin (secretaria)', email('secretaria'))]
    linhas += [(f'Professor(a) de {d}', email(u)) for u, _, d in PROFESSORES]
    linhas += [('Aluno', email('bruno.lima')), ('Aluna', email('carla.souza'))]
    return linhas


def pdf(titulo, linhas, paginas=None):
    """PDF mínimo sem dependências. ``paginas``: lista de (título, linhas) para slides com várias páginas."""
    paginas = paginas or [(titulo, linhas)]
    objs = ['<</Type/Catalog/Pages 2 0 R>>', None, '<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>']
    kids = []
    for t, ls in paginas:
        corpo = '\n'.join([f'BT /F1 20 Tf 50 760 Td ({t}) Tj ET'] +
                          [f'BT /F1 12 Tf 50 {720 - i * 20} Td ({l}) Tj ET' for i, l in enumerate(ls)])
        objs.append(f'<</Length {len(corpo)}>>stream\n{corpo}\nendstream')
        objs.append(f'<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents {len(objs)} 0 R/Resources<</Font<</F1 3 0 R>>>>>>')
        kids.append(f'{len(objs)} 0 R')
    objs[1] = f'<</Type/Pages/Kids[{" ".join(kids)}]/Count {len(kids)}>>'
    saida, offsets = '%PDF-1.4\n', []
    for i, o in enumerate(objs):
        offsets.append(len(saida))
        saida += f'{i + 1} 0 obj{o}endobj\n'
    xref = len(saida)
    saida += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n' + ''.join(f'{o:010d} 00000 n \n' for o in offsets)
    return (saida + f'trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n').encode('latin-1')


def base(db):
    """Identidade, contas, turma, disciplinas e vínculos (dados de demonstração)."""
    from app.models import (AlunoModel, AlunoTurmaModel, ComunicadoModel, DisciplinaModel, ProfessorModel,
                            TurmaModel, UsuarioModel)
    from app.models.escola_model import IdentidadeEscolaModel
    from app.services import cursos
    from app.services.matriculas import registrar_disciplina, sincronizar_turma
    from app.models.curso_model import EstadoTurmaModel
    senha = generate_password_hash(SENHA)
    db.add(IdentidadeEscolaModel(id=1, versao=1, dados=json.dumps({'nome': ESCOLA, 'sigla': 'CH',
        'subtitulo': 'DEMONSTRAÇÃO EDUFAST'}, ensure_ascii=False)))

    def usuario(nome, tipo):
        row = UsuarioModel(email=email(nome), tipo=tipo, estado='ativo', senha=senha)
        db.add(row)
        db.flush()
        return row
    usuario('diretoria', 'super_admin')
    usuario('secretaria', 'admin')
    turma = TurmaModel(nome='1º ano A', codigo='1A-2026', ano_letivo=2026, turno='Matutino')
    disciplinas = [DisciplinaModel(codigo=c, nome=n, carga_horaria=h) for c, n, h in DISCIPLINAS]
    db.add_all([turma, *disciplinas])
    db.flush()
    db.add(EstadoTurmaModel(turma_id=turma.id, arquivada=False))
    for i, (u, nome, disc) in enumerate(PROFESSORES):
        conta = usuario(u, 'professor')
        prof = ProfessorModel(usuario_id=conta.id, nome=nome, cpf=f'DEMO-P{i + 1:02d}', disciplina_principal=disc,
                              regime_trabalho='Integral')
        db.add(prof)
        db.flush()
        registrar_disciplina(db, turma.id, disciplinas[i].id)
        cursos.atribuir(db, prof.id, turma.id, disciplinas[i].id)
    for i, nome in enumerate(ALUNOS):
        conta = usuario(slug(nome), 'aluno')
        aluno = AlunoModel(usuario_id=conta.id, nome=nome, matricula=f'2026{i + 1:03d}', curso_serie='1º ano',
                           status_matricula='Ativo')
        db.add(aluno)
        db.flush()
        db.add(AlunoTurmaModel(aluno_id=aluno.id, turma_id=turma.id))
    db.flush()
    sincronizar_turma(db, turma.id)
    db.add_all([ComunicadoModel(titulo='Reunião de pais e responsáveis', destinatario='Todos', criado_por='Secretaria',
                                mensagem='A reunião do 1º bimestre será no dia 24/04, às 19h, no auditório.'),
                ComunicadoModel(titulo='Semana de provas', destinatario='Alunos', criado_por='Secretaria',
                                mensagem='As provas do 2º bimestre acontecem de 29/06 a 03/07.')])
    db.commit()
    return turma.id


def cliente(app, email_conta):
    from app.models import UsuarioModel
    with get_session() as db:
        u = db.query(UsuarioModel).filter_by(email=email_conta).one()
        dados = (u.id, u.tipo, u.email, u.auth_version)
    c = app.test_client()
    with c.session_transaction() as s:
        s.update(user_id=dados[0], user_role=dados[1], user_email=dados[2], auth_version=dados[3], csrf_token='demo')
    return c


def post(c, caminho, dados=None, arquivos=None):
    cab = {'X-CSRF-Token': 'demo', 'Idempotency-Key': uuid4().hex}
    r = c.post(caminho, data={**(dados or {}), **(arquivos or {})}, headers=cab) if arquivos else c.post(caminho, json=dados or {}, headers=cab)
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f'Falha ao preparar {caminho}: {r.status_code} {r.get_data(as_text=True)[:300]}')
    return r.get_json(silent=True) or {}


def regras(app, turma_id):
    """Calendário, recesso e regras do boletim pelas telas do super admin; regra aplicada à turma."""
    super_admin = cliente(app, email('diretoria'))
    cal = post(super_admin, '/super/escola/calendarios', {'ano': 2026, 'nome': 'Calendário 2026', 'inicio': '2026-02-02',
               'fim': '2026-12-11', 'dias_semana': [0, 1, 2, 3, 4], 'meta_letivos': 200})['calendario_id']
    datas = [('2026-02-02', '2026-04-17'), ('2026-04-20', '2026-07-10'), ('2026-07-27', '2026-09-30'), ('2026-10-01', '2026-12-11')]
    politica = post(super_admin, '/super/escola/politicas', {'nome': 'Boletim 2026 — bimestral', 'calendario_id': cal,
        'divisao': 'bimestres', 'media_referencia': '6', 'casas': '1', 'arredondamento': 'comercial',
        'periodos': [{'nome': f'{i + 1}º bimestre', 'peso': '1', 'inicio': a, 'fim': b} for i, (a, b) in enumerate(datas)]})['politica_id']
    post(super_admin, f'/super/escola/politicas/{politica}/aplicar', {'turma_id': turma_id})


def academico(turma_id):
    """Avaliações e notas (1º bimestre fechado e 2º em andamento) e chamadas confirmadas."""
    from app.models import AlunoTurmaModel, ProfessorModel, TurmaDisciplinaModel, UsuarioModel
    from app.models.curso_model import AtribuicaoDocenteModel
    from app.models.academico_model import AvaliacaoModel, LancamentoNotaModel, PeriodoLetivoModel
    from app.models.frequencia_model import ChamadaModel, PresencaModel
    rnd = random.Random(2026)
    with get_session() as db:
        periodos = db.query(PeriodoLetivoModel).filter_by(turma_id=turma_id).order_by(PeriodoLetivoModel.ordem).all()
        alunos = [a for a, in db.query(AlunoTurmaModel.aluno_id).filter_by(turma_id=turma_id)]
        admin = db.query(UsuarioModel).filter_by(email=email('secretaria')).one().id
        for vinculo in db.query(TurmaDisciplinaModel).filter_by(turma_id=turma_id).all():
            prof = db.query(ProfessorModel).join(AtribuicaoDocenteModel, AtribuicaoDocenteModel.professor_id == ProfessorModel.id).filter(
                AtribuicaoDocenteModel.turma_disciplina_id == vinculo.id, AtribuicaoDocenteModel.ativo.is_(True)).one()
            for periodo in periodos[:2]:
                for titulo, peso in (('Prova', 2), ('Trabalho', 1)):
                    av = AvaliacaoModel(turma_disciplina_id=vinculo.id, periodo_id=periodo.id, peso=peso, publicada=True,
                                        titulo=f'{titulo} — {periodo.nome}')
                    db.add(av)
                    db.flush()
                    for aluno_id in alunos:
                        db.add(LancamentoNotaModel(avaliacao_id=av.id, aluno_id=aluno_id, professor_id=prof.id, versao=1,
                                                   valor=f'{rnd.randint(45, 100) / 10:.2f}', observacao=''))
            dia = date(2026, 2, 3)
            for n in range(10):
                chamada = ChamadaModel(turma_disciplina_id=vinculo.id, dia=dia + timedelta(days=7 * n), aula=1, revisao=1,
                                       autor_id=prof.usuario_id, estado='aprovada', decidido_por=admin, versao=1,
                                       motivo='', decisao_motivo='')
                db.add(chamada)
                db.flush()
                db.add_all([PresencaModel(chamada_id=chamada.id, aluno_id=a,
                                          situacao='falta' if rnd.random() < 0.07 else 'presente') for a in alunos])
        periodos[0].fechado = True
        db.commit()


def conteudos(app, turma_id):
    """Abas, avisos e materiais da disciplina pelas rotas reais, aprovados pela secretaria."""
    from app.models import DisciplinaModel, TurmaDisciplinaModel
    secretaria = cliente(app, email('secretaria'))
    with get_session() as db:
        pares = {d.nome: v.id for v, d in db.query(TurmaDisciplinaModel, DisciplinaModel).join(
            DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id).filter(TurmaDisciplinaModel.turma_id == turma_id)}
    grafico = (DEMO / 'funcao_afim.png').read_bytes()
    planos = {
        ('ana.ribeiro', 'Matemática'): [
            ('Unidade 1 — Funções', [
                {'tipo': 'aviso', 'titulo': 'Boas-vindas à Matemática', 'texto': 'Neste bimestre estudamos funções. Tragam a apostila na primeira aula.'},
                {'tipo': 'arquivo', 'titulo': 'Apostila — funções do 1º grau', 'texto': 'Leitura obrigatória antes da prova.',
                 'arquivo': ('apostila-funcoes.pdf', pdf('Apostila - Funcoes do 1o grau', ['1. O que e uma funcao', '2. Funcao afim: f(x) = ax + b', '3. Exercicios resolvidos']))},
                {'tipo': 'arquivo', 'titulo': 'Gráfico da função afim', 'texto': 'Use para a atividade da aula 3.', 'arquivo': ('funcao-afim.png', grafico)},
                {'tipo': 'arquivo', 'titulo': 'Slides — função afim na prática', 'texto': 'Slides da aula 2. Leia aqui mesmo, página por página.',
                 'arquivo': ('slides-funcao-afim.pdf', pdf('', [], [
                     ('Funcao afim na pratica', ['Aula 2 - Matematica - 1o ano', 'Profa. Ana Ribeiro']),
                     ('1. Onde aparece', ['Taxi: bandeirada + preco por km', 'Conta de agua: taxa fixa + consumo']),
                     ('2. Lendo o grafico', ['a > 0: reta crescente', 'b: onde a reta corta o eixo y']),
                     ('3. Desafio', ['Uma corrida custa R$ 5 + R$ 2 por km.', 'Quanto custa uma corrida de 8 km?'])]))},
                {'tipo': 'link', 'titulo': 'Exercícios online', 'texto': 'Lista para treinar em casa.', 'link': 'https://www.khanacademy.org/math'},
            ])],
        ('carlos.mendes', 'Língua Portuguesa'): [
            ('Leitura e interpretação', [
                {'tipo': 'aviso', 'titulo': 'Leitura do bimestre', 'texto': 'Livro do bimestre: "Vidas Secas", de Graciliano Ramos.'},
                {'tipo': 'arquivo', 'titulo': 'Roteiro de leitura', 'texto': 'Responda às questões ao fim de cada capítulo.',
                 'arquivo': ('roteiro-leitura.pdf', pdf('Roteiro de leitura - Vidas Secas', ['Capitulos 1 a 3: personagens', 'Capitulos 4 a 6: espaco e tempo']))},
            ])],
        ('beatriz.lopes', 'Biologia'): [
            ('Citologia', [
                {'tipo': 'aviso', 'titulo': 'Aula prática no laboratório', 'texto': 'Na próxima semana: observação de células ao microscópio. Uso de jaleco obrigatório.'},
                {'tipo': 'link', 'titulo': 'Vídeo de exemplo do player', 'texto': 'Exemplo de vídeo do YouTube aberto dentro da plataforma (curta da Blender Foundation).',
                 'link': 'https://www.youtube.com/watch?v=aqz-KE-bpKQ'},
            ])],
    }
    for (prof, disciplina), abas in planos.items():
        professor = cliente(app, email(prof))
        par = pares[disciplina]
        for ordem, (nome_aba, itens) in enumerate(abas, 1):
            aba = post(professor, f'/estudos/disciplinas/{par}/abas', {'nome': nome_aba, 'ordem': ordem * 10})
            for item in itens:
                dados = {k: v for k, v in item.items() if k != 'arquivo'}
                if item['tipo'] != 'aviso':  # avisos ficam na aba geral; materiais na aba temática
                    dados['secao_id'] = aba.get('id')
                if 'arquivo' in item:
                    nome, conteudo = item['arquivo']
                    criado = post(professor, f'/estudos/disciplinas/{par}/novo?formato=json',
                                  {k: str(v) for k, v in dados.items()}, {'arquivo': (io.BytesIO(conteudo), nome)})
                else:
                    criado = post(professor, f'/estudos/disciplinas/{par}/novo', dados)
                pedido = post(professor, f'/estudos/conteudos/{criado["id"]}/publicar', {'versao': 1})
                post(secretaria, f'/solicitacoes/alteracoes/{pedido["id"]}/decidir', {'decisao': 'aprovar'})
    return pares


def main():
    if (os.getenv('EDUFAST_DEMO_COMPLETA') != '1' or engine.dialect.name != 'postgresql'
            or engine.url.database != 'edufast_demo_completa'):
        raise SystemExit('Somente no banco descartável edufast_demo_completa do iniciador da demo.')
    tabelas = set(inspect(engine).get_table_names())
    if not tabelas:
        from schema_base import criar_esquema_base
        criar_esquema_base(engine)
    else:
        from app.models import UsuarioModel
        with get_session() as db:
            if db.query(UsuarioModel.id).first() is not None:
                raise SystemExit('A demo já tem dados. Use "reset" para recomeçar do zero.')
    from app import create_app
    app = create_app()
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    with app.app_context():
        with get_session() as db:
            turma_id = base(db)
        regras(app, turma_id)
        academico(turma_id)
        pares = conteudos(app, turma_id)
        from enem_demo_server import montar_curso_enem
        from app.models import DisciplinaModel
        with get_session() as db:
            matematica = db.query(DisciplinaModel.id).filter_by(nome='Matemática').one()[0]
        montar_curso_enem(app, email('ana.ribeiro'), email('secretaria'), disciplina_id=matematica,
                          turma_disciplina_id=pares['Matemática'], laboratorio=False)
    print(json.dumps({'escola': ESCOLA, 'senha': SENHA, 'contas': contas()}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    sys.exit(main())

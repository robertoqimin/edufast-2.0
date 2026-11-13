"""Massa sintética e limites destrutivos do ambiente TDD, sem mocks da API."""
from datetime import date, datetime
import hashlib
import os
from pathlib import Path
from sample_files import pdf

ACTORS = {'plataforma': 1, 'gestor_a': 2, 'secretaria_a': 3, 'coordenacao_a': 4,
          'professor_a': 5, 'aluno_a': 6, 'dupla': 7, 'gestor_b': 8,
          'aluno_b': 9, 'sem_vinculo': 10, 'convidado': 11}
PASSWORD = 'Senha-ci-123456'
REQUIRED = {
    'usuarios': ['id', 'email', 'senha', 'tipo'],
    'escolas': ['id', 'nome', 'codigo', 'status'],
    'participacoes_escolas': ['id', 'escola_id', 'usuario_id', 'papel', 'status'],
    'periodos_letivos': ['id', 'escola_id', 'nome', 'inicio', 'fim', 'status'],
    'alunos': ['id', 'escola_id', 'usuario_id', 'nome', 'matricula'],
    'professores': ['id', 'escola_id', 'usuario_id', 'nome', 'cpf'],
    'turmas': ['id', 'escola_id', 'periodo_id', 'nome', 'codigo', 'ano_letivo', 'turno', 'status'],
    'disciplinas': ['id', 'escola_id', 'nome', 'codigo', 'carga_horaria'],
    'ofertas_disciplinas': ['id', 'escola_id', 'periodo_id', 'turma_id', 'disciplina_id'],
    'matriculas': ['id', 'escola_id', 'periodo_id', 'aluno_id', 'turma_id', 'status'],
    'atribuicoes_docentes': ['id', 'escola_id', 'professor_id', 'oferta_id', 'ativo'],
    'documentos': ['id', 'escola_id', 'aluno_id', 'disciplina_id', 'titulo', 'caminho_arquivo'],
    'solicitacoes_documentos': ['id', 'escola_id', 'aluno_id', 'titulo', 'status'],
    'convites_escolas': ['id', 'escola_id', 'email', 'papel', 'token_hash', 'status', 'expires_at'],
    'comunicados': ['id', 'escola_id', 'titulo', 'mensagem', 'destinatario'],
    'notas': ['id', 'escola_id', 'aluno_id', 'oferta_id', 'professor_id', 'nota'],
    'atividades': ['id', 'escola_id', 'oferta_id', 'professor_id', 'titulo'],
    'solicitacoes_alteracoes': ['id', 'escola_id', 'solicitante_id', 'tipo', 'payload', 'estado', 'decidido_por'],
    'eventos_auditoria': ['id', 'escola_id', 'ator_id', 'acao', 'recurso_id'],
}


def assert_disposable(engine):
    if os.environ.get('EDUFAST_TEST_NEXT') != '1':
        raise RuntimeError('Recusado: use exclusivamente o executor TDD isolado.')
    url = engine.url
    memory = url.drivername == 'sqlite' and url.database == ':memory:'
    mysql = (url.drivername == 'mysql+pymysql' and url.host == 'db' and
             url.database == 'edufast_next' and url.username == 'next_ci')
    if not (memory or mysql):
        raise RuntimeError('Recusado: banco fora da lista descartável do TDD.')


def schema(engine):
    from sqlalchemy import MetaData
    assert_disposable(engine)
    metadata = MetaData()
    metadata.reflect(engine)
    missing = []
    for table, columns in REQUIRED.items():
        if table not in metadata.tables:
            missing.append(table+' (tabela)')
        else:
            missing += [table+'.'+column for column in columns if column not in metadata.tables[table].c]
    if missing:
        raise AssertionError('RED: esquema da próxima versão ainda ausente: '+', '.join(missing))
    return metadata


def rows(password_hash):
    data = {}
    data['usuarios'] = [dict(id=identity, email=actor+'@example.test', senha=password_hash,
                              tipo='plataforma' if actor == 'plataforma' else 'usuario')
                        for actor, identity in ACTORS.items()]
    data['escolas'] = [dict(id=1, nome='Escola Alfa', codigo='ALFA', status='ativa'),
                       dict(id=2, nome='Escola Beta', codigo='BETA', status='ativa')]
    members = [(1, 2, 'gestor'), (1, 3, 'secretaria'), (1, 4, 'coordenacao'),
               (1, 5, 'professor'), (1, 6, 'aluno'), (1, 7, 'gestor'),
               (2, 8, 'gestor'), (2, 9, 'aluno'), (2, 7, 'aluno')]
    data['participacoes_escolas'] = [dict(id=i, escola_id=school, usuario_id=user, papel=role, status='ativa')
                                    for i, (school, user, role) in enumerate(members, 1)]
    data['periodos_letivos'] = [dict(id=i, escola_id=i, nome='2026', inicio=date(2026, 2, 1), fim=date(2026, 12, 15), status='aberto') for i in (1, 2)]
    data['alunos'] = [dict(id=1, escola_id=1, usuario_id=6, nome='Aluno Alfa', matricula='A001'),
                      dict(id=2, escola_id=2, usuario_id=9, nome='Aluno Beta', matricula='B001', foto_perfil='perfil_beta.png'),
                      dict(id=3, escola_id=1, usuario_id=7, nome='Aluno Dupla', matricula='A002'),
                      dict(id=4, escola_id=2, usuario_id=7, nome='Aluno Dupla Beta', matricula='B002')]
    data['professores'] = [dict(id=1, escola_id=1, usuario_id=5, nome='Professor Alfa', cpf='12345000198'),
                           dict(id=2, escola_id=2, usuario_id=8, nome='Professor Beta', cpf='12345000279')]
    data['turmas'] = [dict(id=i, escola_id=school, periodo_id=school, nome=name, codigo=code,
                           ano_letivo=2026, turno='manha', status='ativa')
                      for i, school, name, code in [(1, 1, '6º A', '6A'), (2, 2, '6º B', '6B'), (3, 1, '6º C', '6C')]]
    data['disciplinas'] = [dict(id=i, escola_id=school, nome=name, codigo=code, carga_horaria=80)
                           for i, school, name, code in [(1, 1, 'Matemática Alfa', 'MAT'), (2, 2, 'Matemática Beta', 'MAT'), (3, 1, 'Português', 'POR')]]
    data['ofertas_disciplinas'] = [dict(id=i, escola_id=school, periodo_id=school, turma_id=turma, disciplina_id=discipline)
                                  for i, school, turma, discipline in [(1, 1, 1, 1), (2, 2, 2, 2), (3, 1, 3, 1)]]
    data['matriculas'] = [dict(id=i, escola_id=i, periodo_id=i, aluno_id=i, turma_id=i, status='ativa') for i in (1, 2)]
    data['atribuicoes_docentes'] = [dict(id=1, escola_id=1, professor_id=1, oferta_id=1, ativo=True)]
    data['documentos'] = [dict(id=i, escola_id=i, aluno_id=i, disciplina_id=i, titulo='Documento '+str(i), caminho_arquivo='documento-'+('alfa' if i == 1 else 'beta')+'.pdf') for i in (1, 2)]
    data['solicitacoes_documentos'] = [dict(id=i, escola_id=2 if i == 2 else 1, aluno_id=i, titulo='Comprovante', status='pendente') for i in (1, 2, 3)]
    data['convites_escolas'] = [dict(id=i, escola_id=1, email='convidado@example.test', papel='secretaria',
                                    token_hash=hashlib.sha256(token.encode()).hexdigest(), status='pendente', expires_at=expires)
                               for i, token, expires in [(1, 'convite-ci-valido', datetime(2099, 1, 1)), (2, 'convite-ci-expirado', datetime(2000, 1, 1))]]
    data['comunicados'] = [dict(id=1, escola_id=1, titulo='Comunicado Alfa', mensagem='ALFA', destinatario='alunos'),
                           dict(id=2, escola_id=2, titulo='Comunicado Beta', mensagem='BETA', destinatario='alunos'),
                           dict(id=3, escola_id=1, titulo='Equipe Alfa', mensagem='Restrito', destinatario='equipe')]
    return data


def seed(engine, metadata, upload_directory, password_hash):
    assert_disposable(engine)
    data = rows(password_hash)
    with engine.begin() as connection:
        for table in reversed(metadata.sorted_tables):
            connection.execute(table.delete())
        for table in metadata.sorted_tables:
            for row in data.get(table.name, []):
                connection.execute(table.insert().values(**row))
    directory = Path(upload_directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in [('documento-alfa.pdf', pdf('DOCUMENTO-ALFA').encode()),
                          ('documento-beta.pdf', pdf('DOCUMENTO-BETA').encode()),
                          ('perfil_beta.png', b'FOTO-BETA')]:
        (directory/name).write_bytes(content)

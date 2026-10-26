"""Migração real e restrições do banco. Contrato futuro: app.migrations.upgrade."""
import importlib
import json
from pathlib import Path
import unittest

from fixtures import assert_disposable, schema, seed


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        from app.database import engine
        from sqlalchemy import MetaData
        self.engine = engine
        assert_disposable(engine)
        metadata = MetaData()
        metadata.reflect(engine)
        metadata.drop_all(engine)

    def migrate(self, **kwargs):
        module = importlib.import_module('app.migrations')
        return module.upgrade(self.engine, **kwargs)

    def legacy(self):
        from sqlalchemy import MetaData
        snapshot = json.loads(Path(__file__).with_name('legacy').joinpath(self.engine.dialect.name+'.json').read_text(encoding='utf-8'))
        with self.engine.begin() as db:
            for statement in snapshot['statements']:
                db.exec_driver_sql(statement)
        metadata = MetaData()
        metadata.reflect(self.engine)
        with self.engine.begin() as db:
            for identity, role in [(1, 'admin'), (2, 'aluno'), (3, 'professor')]:
                db.execute(metadata.tables['usuarios'].insert().values(id=identity, email=f'legacy{identity}@example.test', senha='legacy-hash-preserve', tipo=role))
            for table, row in [
                ('alunos', dict(id=1, usuario_id=2, nome='Aluno Legado', matricula='LEG001')),
                ('professores', dict(id=1, usuario_id=3, nome='Professor Legado', cpf='33333333333')),
                ('turmas', dict(id=1, nome='Turma Legada', codigo='LEG', ano_letivo=2026)),
                ('disciplinas', dict(id=1, nome='Disciplina Legada', codigo='LEG', carga_horaria=80)),
                ('notas', dict(id=1, aluno_id=1, professor_id=1, disciplina_id=1, nota=8.5)),
                ('documentos', dict(id=1, aluno_id=1, disciplina_id=1, titulo='Documento legado', caminho_arquivo='arquivo-preservado.pdf')),
            ]:
                db.execute(metadata.tables[table].insert().values(**row))

    def fingerprint(self):
        from sqlalchemy import MetaData, select
        metadata = MetaData()
        metadata.reflect(self.engine)
        with self.engine.connect() as db:
            return {table.name: [dict(row._mapping) for row in db.execute(select(table).order_by(*table.primary_key.columns))]
                    for table in metadata.sorted_tables}

    def test_INT_001_empty_database_receives_full_schema(self):
        self.migrate()
        schema(self.engine)

    def test_INT_002_legacy_requires_explicit_owner(self):
        self.legacy()
        before = self.fingerprint()
        module = importlib.import_module('app.migrations')
        with self.assertRaises(module.MigrationError) as caught:
            self.migrate()
        self.assertEqual(caught.exception.code, 'legacy_owner_required')
        self.assertEqual(before, self.fingerprint())

    def test_INT_003_migration_preserves_legacy_data_and_file_references(self):
        self.legacy()
        self.migrate(legacy_school={'nome': 'Escola Legada', 'codigo': 'LEGADO'})
        schema(self.engine)
        data = self.fingerprint()
        self.assertEqual(data['usuarios'][0]['senha'], 'legacy-hash-preserve')
        self.assertEqual(data['alunos'][0]['matricula'], 'LEG001')
        self.assertEqual(float(data['notas'][0]['nota']), 8.5)
        self.assertEqual(data['documentos'][0]['caminho_arquivo'], 'arquivo-preservado.pdf')
        school = data['escolas'][0]['id']
        self.assertTrue(all(row['escola_id'] == school for table in ['alunos', 'professores', 'turmas', 'disciplinas', 'notas', 'documentos'] for row in data[table]))

    def test_INT_004_migration_is_idempotent(self):
        self.legacy()
        owner = {'nome': 'Escola Legada', 'codigo': 'LEGADO'}
        self.migrate(legacy_school=owner)
        before = self.fingerprint()
        self.migrate(legacy_school=owner)
        self.assertEqual(before, self.fingerprint())

    def test_INT_005_dry_run_does_not_modify_schema_or_rows(self):
        self.legacy()
        before = self.fingerprint()
        report = self.migrate(legacy_school={'nome': 'Legado', 'codigo': 'LEG'}, dry_run=True)
        self.assertIsInstance(report, dict)
        self.assertTrue(report['pending_changes'])
        self.assertEqual(before, self.fingerprint())

    def future_data(self):
        self.migrate()
        metadata = schema(self.engine)
        seed(self.engine, metadata, '/tmp/next-uploads', 'hash-test-only')
        return metadata

    def test_INT_006_database_rejects_cross_school_enrollment(self):
        from sqlalchemy.exc import IntegrityError
        metadata = self.future_data()
        with self.assertRaises(IntegrityError), self.engine.begin() as db:
            db.execute(metadata.tables['matriculas'].insert().values(id=99, escola_id=1, aluno_id=2, turma_id=1, periodo_id=1, status='ativa'))

    def test_INT_007_database_rejects_duplicate_active_enrollment(self):
        from sqlalchemy.exc import IntegrityError
        metadata = self.future_data()
        with self.assertRaises(IntegrityError), self.engine.begin() as db:
            db.execute(metadata.tables['matriculas'].insert().values(id=99, escola_id=1, aluno_id=1, turma_id=1, periodo_id=1, status='ativa'))

    def test_INT_008_identity_can_have_student_profile_in_two_schools(self):
        from sqlalchemy import select, func
        metadata = self.future_data()
        table = metadata.tables['alunos']
        with self.engine.connect() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(table).where(table.c.usuario_id == 7)), 2)

    def test_INT_009_database_rejects_cross_school_teacher_assignment(self):
        from sqlalchemy.exc import IntegrityError
        metadata = self.future_data()
        with self.assertRaises(IntegrityError), self.engine.begin() as db:
            db.execute(metadata.tables['atribuicoes_docentes'].insert().values(id=99, escola_id=1, professor_id=2, oferta_id=1, ativo=True))

    def test_INT_010_grades_of_different_periods_do_not_overwrite_each_other(self):
        from datetime import date
        from sqlalchemy import select, func
        metadata = self.future_data()
        table = metadata.tables['notas']
        with self.engine.begin() as db:
            db.execute(metadata.tables['periodos_letivos'].insert().values(id=3, escola_id=1, nome='2027', inicio=date(2027, 2, 1), fim=date(2027, 12, 15), status='aberto'))
            db.execute(metadata.tables['turmas'].insert().values(id=4, escola_id=1, periodo_id=3, nome='Nova turma', codigo='7A', ano_letivo=2027, turno='manha', status='ativa'))
            db.execute(metadata.tables['ofertas_disciplinas'].insert().values(id=4, escola_id=1, periodo_id=3, turma_id=4, disciplina_id=1))
            for identity, offering, grade in [(1, 1, 8.5), (2, 4, 9.0)]:
                row = dict(id=identity, escola_id=1, aluno_id=1, professor_id=1, oferta_id=offering, nota=grade)
                if 'disciplina_id' in table.c:
                    row['disciplina_id'] = 1
                db.execute(table.insert().values(**row))
            self.assertEqual(db.scalar(select(func.count()).select_from(table).where(table.c.aluno_id == 1)), 2)

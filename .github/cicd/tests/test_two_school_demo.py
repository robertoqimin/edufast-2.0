"""Proteções e dados do cenário de duas escolas em bancos SQLite descartáveis."""
import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import UsuarioModel, AlunoModel, DisciplinaModel
from two_school_test_data import initialize, validate_target


class TwoSchoolDemoTests(unittest.TestCase):
    def test_two_separate_schools_have_exact_counts_and_local_accounts(self):
        for school in ['teste01', 'teste02']:
            engine = create_engine('sqlite:///:memory:')
            self.addCleanup(engine.dispose)
            counts = initialize(engine, school)
            self.assertEqual(counts['alunos'], 20)
            self.assertEqual(counts['professores'], 5)
            self.assertEqual(counts['materias'], 3)
            self.assertEqual(counts['alunos_materias'], 60)
            with Session(engine) as db:
                self.assertEqual(db.query(UsuarioModel).count(), 26)
                self.assertTrue(all(u.email.endswith(f'@{school}.local') for u in db.query(UsuarioModel)))
                self.assertTrue(all(s.nome.endswith(f'Teste {school[-2:]}') for s in db.query(AlunoModel)))
                self.assertEqual({s.nome for s in db.query(DisciplinaModel)}, {'Matemática', 'Português', 'Ciências'})
            self.assertEqual(initialize(engine, school), counts)
            with self.assertRaises(RuntimeError):
                initialize(engine, 'teste02' if school == 'teste01' else 'teste01')

    def test_restart_does_not_reset_password_role_or_approval(self):
        engine = create_engine('sqlite:///:memory:')
        self.addCleanup(engine.dispose)
        initialize(engine, 'teste01')
        with Session(engine) as db, db.begin():
            user = db.query(UsuarioModel).filter_by(email='professor01@teste01.local').one()
            user.senha = 'hash-modificado-pelo-usuario'
            user.estado = 'pendente'
            user.auth_version = 9
        initialize(engine, 'teste01')
        with Session(engine) as db:
            user = db.query(UsuarioModel).filter_by(email='professor01@teste01.local').one()
            self.assertEqual((user.senha, user.estado, user.auth_version), ('hash-modificado-pelo-usuario', 'pendente', 9))

    def test_existing_unrelated_database_is_untouched(self):
        engine = create_engine('sqlite:///:memory:')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE dados_existentes (id INTEGER PRIMARY KEY)'))
            connection.execute(text('INSERT INTO dados_existentes VALUES (42)'))
        with self.assertRaises(RuntimeError):
            initialize(engine, 'teste01')
        self.assertEqual(inspect(engine).get_table_names(), ['dados_existentes'])
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT id FROM dados_existentes')).scalar(), 42)

    def test_cli_requires_explicit_local_database_and_opt_in(self):
        env = {'EDUFAST_TEST_SCHOOL': 'teste01', 'EDUFAST_TWO_SCHOOLS_TEST': '1'}
        config = SimpleNamespace(APP_ENV='development', DB_URL='')
        url = make_url('postgresql+psycopg://edufast:synthetic@db-teste01/edufast_teste01')
        self.assertEqual(validate_target(config, url, env), 'teste01')
        for wrong_config, wrong_url, wrong_env in [
            (SimpleNamespace(APP_ENV='production', DB_URL=''), url, env),
            (SimpleNamespace(APP_ENV='development', DB_URL='override'), url, env),
            (config, url.set(host='db'), env),
            (config, url.set(database='edufast'), env),
            (config, url, {}),
            (config, make_url('sqlite:///:memory:'), env),
        ]:
            with self.assertRaises(RuntimeError):
                validate_target(wrong_config, wrong_url, wrong_env)


if __name__ == '__main__':
    unittest.main()

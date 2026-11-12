"""Manual demo fixtures must be repeatable, guarded and non-destructive."""
from unittest import TestCase
from werkzeug.security import check_password_hash, generate_password_hash
import test_concurrency as fixtures
from app.database import get_session
from app.models import UsuarioModel, TurmaModel, DisciplinaModel
from manual_test_data import ACCOUNTS, TEST_PASSWORD, main, populate


class ManualFixturesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_four_logins_and_repeat_preserve_records(self):
        for _ in range(2):
            with get_session() as db:
                populate(db)
                db.commit()
        self.assertEqual(self.fixture.count(UsuarioModel), 8)
        self.assertEqual(self.fixture.count(TurmaModel), 2)
        self.assertEqual(self.fixture.count(DisciplinaModel), 2)
        for email, role in ACCOUNTS.items():
            response = self.fixture.app.test_client().post('/login', json={'email': email, 'senha': TEST_PASSWORD})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['role'], role)

    def test_existing_password_state_and_capability_are_not_reset(self):
        with get_session() as db:
            populate(db)
            user = db.query(UsuarioModel).filter_by(email='professor@teste.local').one()
            user.senha = generate_password_hash('changed-local-password')
            user.estado, user.revisor_materiais = 'pendente', True
            db.commit()
        with get_session() as db:
            populate(db)
            db.commit()
            user = db.query(UsuarioModel).filter_by(email='professor@teste.local').one()
            self.assertTrue(check_password_hash(user.senha, 'changed-local-password'))
            self.assertEqual((user.estado, user.revisor_materiais), ('pendente', True))

    def test_conflicting_account_rolls_back_instead_of_promoting(self):
        with get_session() as db:
            db.add(UsuarioModel(email='admin@teste.local', tipo='aluno', senha='unchanged'))
            db.commit()
        with self.assertRaises(RuntimeError):
            with get_session() as db:
                populate(db)
                db.commit()
        self.assertEqual(self.fixture.count(UsuarioModel), 5)
        with get_session() as db:
            self.assertEqual(db.query(UsuarioModel).filter_by(email='admin@teste.local').one().tipo, 'aluno')

    def test_entrypoint_refuses_nonmanual_environment(self):
        with self.assertRaises(RuntimeError):
            main()
        self.assertEqual(self.fixture.count(UsuarioModel), 4)

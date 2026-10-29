"""HTTP contracts; real concurrency is required on disposable MySQL, never mocked DB."""
import io
import os
from pathlib import Path
import tempfile
import threading
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase, skipUnless
from unittest.mock import patch

from sqlalchemy import event, inspect
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import Base, engine, get_session
from app.models import (AlunoModel, ProfessorModel, UsuarioModel, TurmaModel,
                        DisciplinaModel, AlunoTurmaModel, ProfessorTurmaModel,
                        ProfessorDisciplinaModel, TurmaDisciplinaModel, NotaModel,
                        DocumentoModel, SolicitacaoDocumentoModel, ComunicadoModel,
                        AtividadeModel, IdempotenciaModel)


MYSQL = engine.dialect.name == "mysql"


class MutationApiTests(TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("EDUFAST_TEST_DISPOSABLE") != "1":
            raise RuntimeError("Use the isolated runner; this suite rebuilds its test database")
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app.config["UPLOAD_FOLDER"] = self.folder.name
        with get_session() as db:
            users = [UsuarioModel(id=i, email=f"u{i}@example.test", senha=generate_password_hash("test-password-123"),
                                  tipo=role) for i, role in [(1, "admin"), (2, "aluno"), (3, "professor"), (4, "professor")]]
            db.add_all(users)
            db.flush()
            db.add_all([AlunoModel(id=1, usuario_id=2, nome="Aluno", matricula="M1"),
                        ProfessorModel(id=1, usuario_id=3, nome="Professor", cpf="11111111111"),
                        ProfessorModel(id=2, usuario_id=4, nome="Professor 2", cpf="22222222222"),
                        TurmaModel(id=1, nome="Turma", codigo="T1", ano_letivo=2026),
                        DisciplinaModel(id=1, nome="Matematica", codigo="MAT", carga_horaria=40)])
            db.flush()
            db.add_all([AlunoTurmaModel(aluno_id=1, turma_id=1),
                        ProfessorTurmaModel(professor_id=1, turma_id=1),
                        ProfessorDisciplinaModel(professor_id=1, disciplina_id=1),
                        ProfessorDisciplinaModel(professor_id=2, disciplina_id=1),
                        TurmaDisciplinaModel(turma_id=1, disciplina_id=1),
                        SolicitacaoDocumentoModel(id=1, aluno_id=1, titulo="RG"),
                        SolicitacaoDocumentoModel(id=2, professor_id=1, titulo="Diploma")])
            db.commit()

    def client(self, user=1):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = user
            session["user_role"] = {1: "admin", 2: "aluno", 3: "professor", 4: "professor"}[user]
            session["user_email"] = f"u{user}@example.test"
        return client

    def count(self, model):
        with get_session() as db:
            return db.query(model).count()

    def files(self):
        return list(Path(self.folder.name).iterdir())

    def upload(self, **data):
        return {**data, "arquivo": (io.BytesIO(b"synthetic-document"), "doc.txt")}

    def pair(self, path, factory, user=1, hook=None):
        barrier = threading.Barrier(2)
        def send(index):
            client = self.client(user)
            data = factory(index)
            barrier.wait(timeout=15)
            return client.post(path, data=data)
        if hook:
            with hook:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    return list(pool.map(send, range(2)))
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(send, range(2)))

    def statuses(self, responses, expected):
        self.assertEqual(sorted(r.status_code for r in responses), sorted(expected),
                         [r.get_data(as_text=True)[:300] for r in responses])

    def version_hook(self, module):
        from app.concurrency import check_version
        barrier = threading.Barrier(2)
        def check(record, data):
            check_version(record, data)
            barrier.wait(timeout=15)
        return patch(module + ".check_version", side_effect=check)

    def student_edit(self, **extra):
        return {"nome": "Aluno editado", "email": "u2@example.test", "matricula": "M1", "versao": "1", **extra}

    def teacher_edit(self, **extra):
        return {"nome": "Professor editado", "email": "u3@example.test", "cpf": "11111111111", "versao": "1", **extra}

    def grade(self, **extra):
        return {"aluno_id": "1", "turma_id": "1", "disciplina_id": "1", "nota": "8", "versao": "0", **extra}

    def test_schema_declares_all_unique_guarantees(self):
        inspector = inspect(engine)
        for table, columns in [("usuarios", {"email"}), ("notas", {"aluno_id", "disciplina_id"}),
                               ("alunos_turmas", {"aluno_id", "turma_id"}),
                               ("professores_turmas", {"professor_id", "turma_id"}),
                               ("professores_disciplinas", {"professor_id", "disciplina_id"}),
                               ("turmas_disciplinas", {"turma_id", "disciplina_id"}),
                               ("idempotencias", {"ator", "operacao", "chave"})]:
            with self.subTest(table=table):
                unique = inspector.get_unique_constraints(table)
                unique += [i for i in inspector.get_indexes(table) if i.get("unique")]
                self.assertTrue(any(set(i["column_names"]) == columns for i in unique))

    def test_startup_never_executes_ddl(self):
        statements = []
        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(engine, "before_cursor_execute", capture)
        try:
            create_app()
            create_app()
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        self.assertFalse(any(s.lstrip().upper().startswith(("CREATE", "ALTER", "DROP")) for s in statements))

    def test_document_request_cannot_be_reused_sequentially(self):
        for user, request_id, path in [(2, 1, "/aluno/documentos/upload"), (3, 2, "/professor/documentos/upload")]:
            with self.subTest(user=user):
                self.assertEqual(self.client(user).post(path, data=self.upload(solicitacao_id=str(request_id))).status_code, 302)
                self.assertEqual(self.client(user).post(path, data=self.upload(solicitacao_id=str(request_id))).status_code, 409)
        self.assertEqual(self.count(DocumentoModel), 2)
        self.assertEqual(len(self.files()), 2)

    def test_document_owner_is_checked(self):
        response = self.client(2).post("/aluno/documentos/upload", data=self.upload(solicitacao_id="2"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.count(DocumentoModel), 0)
        self.assertFalse(self.files())

    def test_document_failure_rolls_back_claim_record_and_file(self):
        with patch("app.controllers.document_controller.DocumentoModel", side_effect=RuntimeError("injected failure")):
            with self.assertRaises(RuntimeError):
                self.client(2).post("/aluno/documentos/upload", data=self.upload(solicitacao_id="1"))
        with get_session() as db:
            row = db.get(SolicitacaoDocumentoModel, 1)
            self.assertEqual(row.status, "pendente")
            self.assertIsNone(row.documento_id)
        self.assertEqual(self.count(DocumentoModel), 0)
        self.assertFalse(self.files())
        self.assertEqual(self.client(2).post("/aluno/documentos/upload", data=self.upload(solicitacao_id="1")).status_code, 302)

    def test_old_student_and_teacher_forms_are_rejected(self):
        for path, data in [("/admin/alunos/1/editar", self.student_edit()),
                           ("/admin/professores/1/editar", self.teacher_edit())]:
            with self.subTest(path=path):
                client = self.client()
                self.assertEqual(client.post(path, data=data).status_code, 302)
                self.assertEqual(client.post(path, data=data).status_code, 409)
                data.pop("versao")
                self.assertEqual(client.post(path, data=data).status_code, 428)

    def test_grade_version_is_required_and_stale_grade_rejected(self):
        path = "/professor/notas/salvar"
        client = self.client(3)
        self.assertEqual(client.post(path, data=self.grade()).status_code, 302)
        self.assertEqual(client.post(path, data=self.grade(nota="4")).status_code, 409)
        self.assertEqual(client.post(path, data=self.grade(nota="9", versao="1")).status_code, 302)
        with get_session() as db:
            self.assertEqual(float(db.query(NotaModel).one().nota), 9)

    def test_idempotency_replays_and_rejects_changed_content(self):
        data = {"titulo": "Aviso", "mensagem": "Mensagem", "idempotency_key": "same-send"}
        client = self.client()
        self.assertEqual(client.post("/admin/comunicados", data=data).status_code, 302)
        self.assertEqual(client.post("/admin/comunicados", data=data).status_code, 302)
        self.assertEqual(client.post("/admin/comunicados", data={**data, "mensagem": "Alterada"}).status_code, 409)
        self.assertEqual(self.count(ComunicadoModel), 1)

    def test_idempotency_header_and_missing_key(self):
        client = self.client()
        data = {"titulo": "Aviso", "mensagem": "Mensagem"}
        self.assertEqual(client.post("/admin/comunicados", data=data).status_code, 428)
        for _ in range(2):
            self.assertEqual(client.post("/admin/comunicados", data=data, headers={"Idempotency-Key": "header-key"}).status_code, 302)
        self.assertEqual(self.count(ComunicadoModel), 1)

    def test_new_key_allows_intentional_repetition(self):
        for key in ["first-intent", "second-intent", "case-key", "CASE-KEY"]:
            self.assertEqual(self.client().post("/admin/comunicados", data={"titulo": "Aviso", "mensagem": "Mesma", "idempotency_key": key}).status_code, 302)
        self.assertEqual(self.count(ComunicadoModel), 4)

    def test_key_is_scoped_to_operation(self):
        data = {"titulo": "Documento", "idempotency_key": "same-key"}
        for path in ["/admin/alunos/1/documentos/solicitar", "/admin/professores/1/documentos/solicitar"]:
            self.assertEqual(self.client().post(path, data=data).status_code, 302)
        self.assertEqual(self.count(SolicitacaoDocumentoModel), 4)

    def test_failed_operation_does_not_consume_key(self):
        path = "/arquivos/upload"
        data = lambda: self.upload(aluno_id="999", idempotency_key="retry-failed")
        self.assertEqual(self.client().post(path, data=data()).status_code, 404)
        self.assertEqual(self.count(IdempotenciaModel), 0)
        self.assertEqual(self.count(DocumentoModel), 0)

    def test_upload_replay_keeps_one_file_and_rejects_different_bytes(self):
        client = self.client()
        data = lambda: self.upload(aluno_id="1", idempotency_key="upload-key")
        first = client.post("/arquivos/upload", data=data())
        second = client.post("/arquivos/upload", data=data())
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.json, first.json)
        changed = data()
        changed["arquivo"] = (io.BytesIO(b"different"), "doc.txt")
        self.assertEqual(client.post("/arquivos/upload", data=changed).status_code, 409)
        self.assertEqual(self.count(DocumentoModel), 1)
        self.assertEqual(len(self.files()), 1)

    def test_forms_include_key_and_versions(self):
        for user, path in [(1, "/admin/comunicados"), (1, "/admin/alunos/1"),
                           (1, "/admin/professores/1"), (3, "/professor/dashboard")]:
            with self.subTest(path=path):
                response = self.client(user).get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'name="idempotency_key"', response.data)
                self.assertIn(b'submission.js', response.data)
                if "comunicados" not in path:
                    self.assertIn(b'name="versao"', response.data)

    def test_legacy_seed_cannot_delete_users(self):
        from app.seed import run_seed
        with self.assertRaises(RuntimeError):
            run_seed()
        self.assertEqual(self.count(UsuarioModel), 4)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_student_document(self):
        self.statuses(self.pair("/aluno/documentos/upload", lambda _: self.upload(solicitacao_id="1"), user=2), [302, 409])
        self.assert_document_winner(1)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_teacher_document(self):
        self.statuses(self.pair("/professor/documentos/upload", lambda _: self.upload(solicitacao_id="2"), user=3), [302, 409])
        self.assert_document_winner(2)

    def assert_document_winner(self, request_id):
        self.assertEqual(self.count(DocumentoModel), 1)
        self.assertEqual(len(self.files()), 1)
        with get_session() as db:
            row = db.get(SolicitacaoDocumentoModel, request_id)
            self.assertEqual(row.status, "enviado")
            self.assertEqual(row.documento_id, db.query(DocumentoModel).one().id)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_student_edit_with_photo(self):
        hook = self.version_hook("app.controllers.admin_controller")
        self.statuses(self.pair("/admin/alunos/1/editar", lambda _: self.student_edit(
            foto_perfil=(io.BytesIO(b"synthetic-photo"), "new.png")), hook=hook), [302, 409])
        with get_session() as db:
            self.assertEqual(db.get(AlunoModel, 1).versao, 2)
            self.assertTrue((Path(self.folder.name) / db.get(AlunoModel, 1).foto_perfil).exists())
        self.assertEqual(len(self.files()), 1)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_teacher_edit_with_photo(self):
        self.statuses(self.pair("/admin/professores/1/editar", lambda _: self.teacher_edit(
            foto_perfil=(io.BytesIO(b"synthetic-photo"), "new.png")),
            hook=self.version_hook("app.controllers.admin_controller")), [302, 409])
        with get_session() as db:
            self.assertEqual(db.get(ProfessorModel, 1).versao, 2)
            self.assertTrue((Path(self.folder.name) / db.get(ProfessorModel, 1).foto_perfil).exists())
        self.assertEqual(len(self.files()), 1)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_existing_grade(self):
        with get_session() as db:
            db.add(NotaModel(aluno_id=1, disciplina_id=1, professor_id=1, nota=5))
            db.commit()
        self.statuses(self.pair("/professor/notas/salvar", lambda _: self.grade(versao="1"), user=3,
                               hook=self.version_hook("app.controllers.professor_controller")), [302, 409])
        with get_session() as db:
            note = db.query(NotaModel).one()
            self.assertEqual(note.versao, 2)
            self.assertEqual(float(note.nota), 8)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_new_grade(self):
        self.statuses(self.pair("/professor/notas/salvar", lambda _: self.grade(), user=3,
                               hook=self.version_hook("app.controllers.professor_controller")), [302, 409])
        self.assertEqual(self.count(NotaModel), 1)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_repeated_creations(self):
        cases = [
            ("/admin/comunicados", 1, lambda: {"titulo": "Aviso", "mensagem": "Texto"}, ComunicadoModel, 1),
            ("/admin/alunos/1/documentos/solicitar", 1, lambda: {"titulo": "Novo RG"}, SolicitacaoDocumentoModel, 3),
            ("/admin/professores/1/documentos/solicitar", 1, lambda: {"titulo": "Novo diploma"}, SolicitacaoDocumentoModel, 4),
            ("/professor/atividades/lancar", 3, lambda: self.upload(turma_id="1", disciplina_id="1", titulo="Atividade"), AtividadeModel, 1),
            ("/arquivos/upload", 1, lambda: self.upload(aluno_id="1"), DocumentoModel, 1),
            ("/professores/1/arquivos/upload", 1, lambda: self.upload(), DocumentoModel, 2),
        ]
        for index, (path, user, factory, model, expected) in enumerate(cases):
            with self.subTest(path=path):
                responses = self.pair(path, lambda _: {**factory(), "idempotency_key": f"same-{index}"}, user=user)
                self.assertTrue(all(r.status_code in {201, 302} for r in responses), [r.status_code for r in responses])
                self.assertEqual(self.count(model), expected)
        self.assertEqual(len(self.files()), 3)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_distinct_uploads_create_one_geral(self):
        self.statuses(self.pair("/arquivos/upload", lambda i: self.upload(aluno_id="1", idempotency_key=f"intent-{i}")), [201, 201])
        with get_session() as db:
            self.assertEqual(db.query(DisciplinaModel).filter_by(codigo="GERAL").count(), 1)
        self.assertEqual(self.count(DocumentoModel), 2)
        self.assertEqual(len(self.files()), 2)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_distinct_teachers_share_one_class_subject(self):
        with get_session() as db:
            db.query(ProfessorTurmaModel).delete()
            db.query(TurmaDisciplinaModel).delete()
            db.add(DisciplinaModel(id=2, nome="Portugues", codigo="POR", carga_horaria=40))
            db.flush()
            db.add_all([ProfessorDisciplinaModel(professor_id=2, disciplina_id=2),
                        ProfessorDisciplinaModel(professor_id=1, disciplina_id=2)])
            db.commit()
        responses = self.pair("/admin/turmas", lambda i: {"action": "associate_teacher", "professor_id": str(i + 1), "turma_id": "1"})
        self.statuses(responses, [302, 302])
        self.assertEqual(self.count(ProfessorTurmaModel), 2)
        self.assertEqual(self.count(TurmaDisciplinaModel), 2)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_unique_registrations_and_links(self):
        cases = [
            ("/cadastro/alunos", lambda _: {"nome": "Novo", "email": "new@example.test", "senha": "test-password-123", "matricula": "M2"}, UsuarioModel, 5),
            ("/cadastro/professores", lambda _: {"nome": "Novo", "email": "newteacher@example.test", "senha": "test-password-123", "cpf": "33333333333"}, UsuarioModel, 6),
            ("/admin/turmas", lambda _: {"nome": "Nova", "codigo": "T2", "ano_letivo": "2026"}, TurmaModel, 2),
            ("/admin/disciplinas", lambda _: {"nome": "Nova", "codigo": "D2", "carga_horaria": "40"}, DisciplinaModel, 2),
            ("/admin/disciplinas", lambda _: {"action": "associate_teacher", "professor_id": "1", "disciplina_id": "2"}, ProfessorDisciplinaModel, 3),
            ("/admin/turmas", lambda _: {"action": "associate_student", "aluno_id": "1", "turma_id": "2"}, AlunoTurmaModel, 2),
            ("/admin/turmas", lambda _: {"action": "associate_teacher", "professor_id": "2", "turma_id": "2"}, ProfessorTurmaModel, 2),
        ]
        for path, factory, model, expected in cases:
            with self.subTest(path=path, model=model.__tablename__):
                responses = self.pair(path, factory)
                self.assertTrue(all(r.status_code < 500 for r in responses))
                self.assertEqual(sum(r.status_code in {201, 302} for r in responses), 1)
                self.assertEqual(self.count(model), expected)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_create_admin_preserves_accounts(self):
        barrier = threading.Barrier(2)
        def create(_):
            barrier.wait(timeout=15)
            return subprocess.run([sys.executable, "-m", "flask", "--app", "app:create_app()",
                                   "create-admin", "--email", "newadmin@example.test", "--password", "another-password-123"],
                                  capture_output=True, timeout=30)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, range(2)))
        self.assertEqual(sorted(r.returncode for r in results), [0, 1])
        self.assertEqual(self.count(UsuarioModel), 5)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_distinct_accounts_share_unique_profile_fields(self):
        cases = [
            ("/cadastro/alunos", lambda i: {"nome": "Novo", "email": f"cpf{i}@example.test", "senha": "test-password-123", "matricula": f"CPF{i}", "cpf": "55555555555"}, AlunoModel),
            ("/cadastro/alunos", lambda i: {"nome": "Novo", "email": f"mat{i}@example.test", "senha": "test-password-123", "matricula": "SAME-MAT"}, AlunoModel),
            ("/cadastro/professores", lambda i: {"nome": "Novo", "email": f"teacher{i}@example.test", "senha": "test-password-123", "cpf": "66666666666"}, ProfessorModel),
        ]
        for path, factory, model in cases:
            with self.subTest(path=path, model=model.__tablename__):
                before_users, before_profiles = self.count(UsuarioModel), self.count(model)
                self.statuses(self.pair(path, factory), [201, 409])
                self.assertEqual(self.count(UsuarioModel), before_users + 1)
                self.assertEqual(self.count(model), before_profiles + 1)

    @skipUnless(MYSQL, "Concurrency requires the MySQL runner")
    def test_concurrent_key_with_different_payloads_has_one_winner(self):
        responses = self.pair("/admin/comunicados", lambda i: {
            "titulo": "Aviso", "mensagem": f"Mensagem {i}", "idempotency_key": "conflicting-key"})
        self.statuses(responses, [302, 409])
        self.assertEqual(self.count(ComunicadoModel), 1)
        self.assertEqual(self.count(IdempotenciaModel), 1)

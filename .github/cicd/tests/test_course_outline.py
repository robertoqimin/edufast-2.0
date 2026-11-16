"""Course outline growth, ordering and isolation on a private in-memory database."""
from contextlib import contextmanager
from unittest import TestCase

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.database import Base
from app import models  # noqa: F401 — register FK targets
from app.models.curso_model import CursoModel, CapituloModel, TemaModel, AulaModel
from app.services.cursos import duplicar, estrutura


class CourseOutlineTests(TestCase):
    def setUp(self):
        # Never connect to the configured application database or rebuild its tables.
        self.engine = create_engine('sqlite:///:memory:')
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add_all([
            models.UsuarioModel(id=1, email='outline@example.test', senha='unused', tipo='professor'),
            models.DisciplinaModel(id=1, nome='Disciplina', codigo='D1', carga_horaria=40),
        ])
        self.db.flush()
        self.db.add(models.ProfessorModel(id=1, usuario_id=1, nome='Professor', cpf='11111111111'))
        self.db.flush()
        self.db.add_all([CursoModel(id=i, disciplina_id=1, professor_id=1, titulo=f'Curso {i}')
                         for i in (1, 2)])
        self.db.commit()

    @contextmanager
    def queries(self):
        statements = []
        def capture(conn, cursor, statement, parameters, context, many):
            if statement.lstrip().upper().startswith('SELECT'):
                statements.append(statement)
        event.listen(self.engine, 'before_cursor_execute', capture)
        try:
            yield statements
        finally:
            event.remove(self.engine, 'before_cursor_execute', capture)

    def add_chapter(self, course, position, theme_positions=()):
        chapter = CapituloModel(curso_id=course, titulo=f'Capítulo {position}', posicao=position)
        self.db.add(chapter)
        self.db.flush()
        for position in theme_positions:
            theme = TemaModel(capitulo_id=chapter.id, titulo=f'Tema {position}', posicao=position)
            self.db.add(theme)
            self.db.flush()
            # Insertion order differs from presentation order.
            for lesson_position in (2, 1):
                self.db.add(AulaModel(tema_id=theme.id, titulo=f'Aula {lesson_position}',
                    descricao='Material de estudo', video_id='abcdefghijk', posicao=lesson_position))
        return chapter

    def test_outline_preserves_order_empty_groups_and_course_scope(self):
        self.add_chapter(1, 2, (2, 1))
        empty = self.add_chapter(1, 1)
        self.db.add(TemaModel(capitulo_id=empty.id, titulo='Tema vazio', posicao=1))
        self.add_chapter(1, 3)
        self.add_chapter(2, 1, (1,))
        self.db.commit()
        self.db.expunge_all()
        with self.queries() as queries:
            outline = estrutura(self.db, 1)
            self.assertEqual([item['capitulo'].posicao for item in outline], [1, 2, 3])
            self.assertEqual(outline[0]['temas'][0]['aulas'], [])
            self.assertEqual(outline[2]['temas'], [])
            self.assertEqual([group['tema'].posicao for group in outline[1]['temas']], [1, 2])
            for item in outline:
                self.assertEqual(item['capitulo'].curso_id, 1)
                for group in item['temas']:
                    self.assertEqual(group['tema'].capitulo_id, item['capitulo'].id)
                    if group['aulas']:
                        self.assertEqual([aula.posicao for aula in group['aulas']], [1, 2])
                        self.assertTrue(all(aula.tema_id == group['tema'].id for aula in group['aulas']))
        self.assertLessEqual(len(queries), 3)

    def test_query_budget_does_not_grow_with_chapters_or_themes(self):
        self.add_chapter(1, 1, (1,))
        self.db.commit()
        self.db.expunge_all()
        with self.queries() as small:
            estrutura(self.db, 1)
        for position in range(2, 22):
            self.add_chapter(1, position, (3, 2, 1))
        self.db.commit()
        self.db.expunge_all()
        with self.queries() as large:
            outline = estrutura(self.db, 1)
            self.assertEqual(sum(len(g['aulas']) for c in outline for g in c['temas']), 122)
        self.assertLessEqual(len(large), 3)
        self.assertEqual(len(small), len(large))

    def test_empty_or_unknown_course_has_no_outline(self):
        for course in (1, 999):
            with self.subTest(course=course), self.queries() as queries:
                self.assertEqual(estrutura(self.db, course), [])
            self.assertLessEqual(len(queries), 1)

    def test_duplicating_course_preserves_structure_and_original(self):
        self.add_chapter(1, 1, (1, 2))
        self.add_chapter(1, 2)
        self.db.commit()
        original = self.db.get(CursoModel, 1)
        copy = duplicar(self.db, original, 1)
        self.db.commit()
        def content(course_id):
            return [(c['capitulo'].titulo, [(g['tema'].titulo,
                [(a.titulo, a.descricao, a.video_id) for a in g['aulas']])
                for g in c['temas']]) for c in estrutura(self.db, course_id)]
        self.assertEqual(content(copy.id), content(original.id))
        self.assertEqual(copy.origem_id, original.id)
        self.assertEqual(copy.estado, 'rascunho')
        original_ids = {c['capitulo'].id for c in estrutura(self.db, original.id)}
        self.assertTrue(original_ids.isdisjoint(c['capitulo'].id for c in estrutura(self.db, copy.id)))

"""A4: aplicador revisado em PostgreSQL descartavel (legado com dados, base, falhas e trava)."""
import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch

from sqlalchemy import inspect, text

from app import database
from app.database import Base, engine
from aplicar_migracoes import TRAVA, aplicar, main, planejar
from legacy_fixture import criar_legado, popular_legado, retrato
from schema_base import arquivo_base
from schema_inventory import ESCOLA_DIR, checksum_arquivo, inventory, load_migrations

POSTGRES = engine.dialect.name == 'postgresql'


@skipUnless(POSTGRES, 'Aplicador exige o PostgreSQL descartavel')
class AplicadorPostgresTests(TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv('EDUFAST_TEST_DISPOSABLE') != '1':
            raise RuntimeError('Use the isolated runner; this suite rebuilds its test database')
        cls.migrations = load_migrations()

    def setUp(self):
        Base.metadata.drop_all(engine)
        self.addCleanup(Base.metadata.drop_all, engine)

    def legado(self):
        criar_legado(engine)
        popular_legado(engine)
        return retrato(engine)

    def registro(self):
        with engine.connect() as connection:
            return {r.versao: r for r in connection.execute(text(
                'SELECT versao, arquivo, checksum, origem FROM educafast_migracoes ORDER BY versao'))}

    def copia_migrations(self):
        pasta = Path(tempfile.mkdtemp(prefix='edufast-migrations-'))
        self.addCleanup(shutil.rmtree, pasta, True)
        shutil.copytree(ESCOLA_DIR, pasta, dirs_exist_ok=True, ignore=shutil.ignore_patterns('legado-mysql', '*.py'))
        return pasta

    def test_legacy_with_data_is_upgraded_preserving_every_record(self):
        antes = self.legado()
        plano = planejar(engine)
        self.assertEqual(plano['modo'], 'sequencial')
        self.assertEqual(plano['versao_atual'], 0)
        self.assertEqual([p['arquivo'] for p in plano['pendentes']], [m['arquivo'] for m in self.migrations])
        self.assertEqual(plano['bloqueios'], [])
        self.assertTrue(any('quarentena' in a for a in plano['avisos']))
        self.assertTrue(any('maiusculas' in a for a in plano['avisos']))
        passos = aplicar(engine, plano)
        self.assertEqual([p['arquivo'] for p in passos], [m['arquivo'] for m in self.migrations])
        self.assertEqual(retrato(engine), antes)
        report = inventory(engine)
        self.assertEqual(report['versao_estrutural'], self.migrations[-1]['versao'])
        self.assertEqual(report['alertas'], [])
        registro = self.registro()
        for m in self.migrations:
            with self.subTest(arquivo=m['arquivo']):
                linha = registro[m['versao']]
                self.assertEqual((linha.arquivo, linha.origem), (m['arquivo'], 'aplicada'))
                self.assertEqual(linha.checksum, checksum_arquivo(ESCOLA_DIR / m['arquivo']))
        with patch.object(database.Config, 'APP_ENV', 'production'):
            database.init_db()
        self.assertEqual(planejar(engine)['pendentes'], [])

    def test_empty_database_is_created_by_base_with_checksum(self):
        plano = planejar(engine)
        self.assertEqual((plano['modo'], plano['arquivo']), ('base', arquivo_base()))
        aplicar(engine, plano)
        digest = checksum_arquivo(ESCOLA_DIR / arquivo_base())
        self.assertEqual({(r.arquivo, r.checksum, r.origem) for r in self.registro().values()},
                         {(arquivo_base(), digest, 'aplicada')})
        self.assertEqual(inventory(engine)['alertas'], [])
        with patch.object(database.Config, 'APP_ENV', 'production'):
            database.init_db()

    def test_failure_rolls_back_only_the_failing_proposal_and_rerun_completes(self):
        antes = self.legado()
        pasta = self.copia_migrations()
        quebrada = pasta / '005_espaco_disciplina.sql'
        original = quebrada.read_text(encoding='utf-8')
        quebrada.write_text(original.replace('COMMIT;', 'SELECT 1 / 0;\nCOMMIT;'), encoding='utf-8')
        with self.assertRaises(Exception):
            aplicar(engine, planejar(engine, pasta), pasta)
        estado = {i['versao']: i['situacao'] for i in inventory(engine, pasta)['migrations']}
        self.assertEqual([estado[v] for v in range(1, 5)], ['aplicada'] * 4)
        self.assertEqual(estado[5], 'ausente')  # nada parcial
        quebrada.write_text(original, encoding='utf-8')
        plano = planejar(engine, pasta)
        self.assertEqual([p['versao'] for p in plano['pendentes']], [5, 6, 7, 8, 9, 10])
        aplicar(engine, plano, pasta)
        self.assertEqual(retrato(engine), antes)
        origens = {v: r.origem for v, r in self.registro().items()}
        # 1-4 entraram antes do registro existir na execucao interrompida: a 008 as detecta.
        self.assertEqual(origens, {1: 'detectada', 2: 'detectada', 3: 'detectada', 4: 'detectada',
                                   5: 'aplicada', 6: 'aplicada', 7: 'aplicada', 8: 'aplicada', 9: 'aplicada',
                                   10: 'aplicada'})
        self.assertEqual(inventory(engine, pasta)['alertas'], [])

    def test_partial_structure_blocks_without_changing_anything(self):
        self.legado()
        pasta = self.copia_migrations()
        aplicar(engine, planejar(engine, pasta, ate=4), pasta)
        with engine.begin() as connection:
            connection.execute(text('DROP TABLE frequencia_presencas'))
        bloqueado = planejar(engine, pasta)
        self.assertTrue(any('004_frequencia.sql esta parcial' in b for b in bloqueado['bloqueios']))
        antes = set(inspect(engine).get_table_names())
        with self.assertRaisesRegex(RuntimeError, 'nada foi aplicado'):
            aplicar(engine, bloqueado, pasta)
        self.assertEqual(set(inspect(engine).get_table_names()), antes)
        self.assertNotIn('estudo_conteudos', antes)

    def test_concurrent_application_is_refused_by_database_lock(self):
        self.legado()
        plano = planejar(engine)
        with engine.connect() as outra:
            outra.execute(text('SELECT pg_advisory_lock(:k)'), {'k': TRAVA})
            try:
                with self.assertRaisesRegex(RuntimeError, 'em andamento'):
                    aplicar(engine, plano)
            finally:
                outra.execute(text('SELECT pg_advisory_unlock(:k)'), {'k': TRAVA})
                outra.commit()
        self.assertEqual(inventory(engine)['versao_estrutural'], 0)

    def test_stale_plan_is_refused_after_database_changes(self):
        self.legado()
        plano = planejar(engine)
        pasta = self.copia_migrations()
        aplicar(engine, planejar(engine, pasta, ate=1), pasta)
        with self.assertRaisesRegex(RuntimeError, 'mudou desde o plano'):
            aplicar(engine, plano)
        self.assertEqual(inventory(engine)['versao_estrutural'], 1)

    def test_staged_upgrade_with_ate_and_base_refuses_ate(self):
        self.legado()
        aplicar(engine, planejar(engine, ate=3))
        self.assertEqual(inventory(engine)['versao_estrutural'], 3)
        resto = planejar(engine)
        self.assertEqual([p['versao'] for p in resto['pendentes']], [4, 5, 6, 7, 8, 9, 10])
        aplicar(engine, resto)
        self.assertEqual(inventory(engine)['alertas'], [])
        Base.metadata.drop_all(engine)
        self.assertTrue(planejar(engine, ate=3)['bloqueios'])

    def test_cli_requires_explicit_target_and_exact_confirmation(self):
        self.legado()
        url = engine.url.render_as_string(hide_password=False)
        with patch.dict(os.environ, {'EDUFAST_APPLY_DB_URL': url}):
            self.assertEqual(main([]), 0)  # so plano
            self.assertEqual(inventory(engine)['versao_estrutural'], 0)
            with self.assertRaises(SystemExit):
                main(['--aplicar', '--confirmar', 'outro_banco'])
            self.assertEqual(inventory(engine)['versao_estrutural'], 0)
            self.assertEqual(main(['--aplicar', '--confirmar', engine.url.database]), 0)
        self.assertEqual(inventory(engine)['versao_estrutural'], self.migrations[-1]['versao'])
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit):
            main([])

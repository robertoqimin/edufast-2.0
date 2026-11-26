-- PROPOSTA 008: registro de versoes do esquema. REVISAR antes de executar.
-- Completa educafast_migracoes (criada pela 003) e registra como "detectada" cada proposta
-- anterior cuja estrutura completa ja existe. Nao altera outras tabelas nem dados escolares.
-- checksum fica vazio: um arquivo nao contem o proprio hash; o aplicador revisado o preenche.
-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.
-- Gerado por migrations/gerar_postgresql.py a partir dos modelos; revisar antes de executar.
-- Aplicar com: psql -v ON_ERROR_STOP=1 -f <arquivo>

BEGIN;

ALTER TABLE educafast_migracoes
    ADD COLUMN descricao VARCHAR(120),
    ADD COLUMN arquivo VARCHAR(120),
    ADD COLUMN checksum VARCHAR(64),
    ADD COLUMN aplicada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN origem VARCHAR(12) DEFAULT 'aplicada' NOT NULL,
    ADD CONSTRAINT ck_migracao_origem CHECK (origem IN ('aplicada','detectada')),
    ADD CONSTRAINT ck_migracao_checksum CHECK (checksum IS NULL OR length(checksum) = 64);

-- 001_concorrencia.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 1, 'concorrencia', '001_concorrencia.sql', 'detectada'
WHERE to_regclass('idempotencias') IS NOT NULL
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'alunos' AND column_name = 'versao')
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'professores' AND column_name = 'versao')
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'notas' AND column_name = 'versao')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

-- 002_aprovacoes_e_permissoes.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 2, 'aprovacoes_e_permissoes', '002_aprovacoes_e_permissoes.sql', 'detectada'
WHERE to_regclass('solicitacoes_alteracoes') IS NOT NULL
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'usuarios' AND column_name = 'estado')
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'usuarios' AND column_name = 'revisor_materiais')
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'usuarios' AND column_name = 'auth_version')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

-- 003_restauracao_educafast.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 3, 'restauracao_educafast', '003_restauracao_educafast.sql', 'detectada'
WHERE to_regclass('configuracoes') IS NOT NULL
  AND to_regclass('educafast_migracoes') IS NOT NULL
  AND to_regclass('escola_calendarios') IS NOT NULL
  AND to_regclass('escola_identidade') IS NOT NULL
  AND to_regclass('limites_login') IS NOT NULL
  AND to_regclass('academico_auditoria') IS NOT NULL
  AND to_regclass('academico_periodos') IS NOT NULL
  AND to_regclass('auditoria_privacidade') IS NOT NULL
  AND to_regclass('curso_auditoria') IS NOT NULL
  AND to_regclass('escola_eventos') IS NOT NULL
  AND to_regclass('escola_politicas') IS NOT NULL
  AND to_regclass('pedidos_privacidade') IS NOT NULL
  AND to_regclass('turma_estados') IS NOT NULL
  AND to_regclass('academico_avaliacoes') IS NOT NULL
  AND to_regclass('atribuicoes_docentes') IS NOT NULL
  AND to_regclass('cursos') IS NOT NULL
  AND to_regclass('escola_regras_periodos') IS NOT NULL
  AND to_regclass('escola_regras_turmas') IS NOT NULL
  AND to_regclass('academico_notas') IS NOT NULL
  AND to_regclass('curso_capitulos') IS NOT NULL
  AND to_regclass('curso_ofertas') IS NOT NULL
  AND to_regclass('curso_temas') IS NOT NULL
  AND to_regclass('curso_aulas') IS NOT NULL
  AND to_regclass('curso_progressos') IS NOT NULL
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'limites_login' AND indexname = 'ix_limites_login_janela')
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'pedidos_privacidade' AND indexname = 'ix_pedidos_privacidade_usuario_id')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

-- 004_frequencia.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 4, 'frequencia', '004_frequencia.sql', 'detectada'
WHERE to_regclass('frequencia_auditoria') IS NOT NULL
  AND to_regclass('frequencia_atestados') IS NOT NULL
  AND to_regclass('frequencia_chamadas') IS NOT NULL
  AND to_regclass('frequencia_presencas') IS NOT NULL
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'frequencia_atestados' AND indexname = 'ix_frequencia_atestados_aluno_id')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

-- 005_espaco_disciplina.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 5, 'espaco_disciplina', '005_espaco_disciplina.sql', 'detectada'
WHERE to_regclass('estudo_conteudos') IS NOT NULL
  AND to_regclass('estudo_auditoria') IS NOT NULL
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'estudo_conteudos' AND indexname = 'ix_estudo_oferta_estado_id')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

-- 006_abas_disciplina.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 6, 'abas_disciplina', '006_abas_disciplina.sql', 'detectada'
WHERE to_regclass('estudo_secoes') IS NOT NULL
  AND to_regclass('estudo_conteudo_secao') IS NOT NULL
  AND to_regclass('estudo_secao_auditoria') IS NOT NULL
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'estudo_secoes' AND indexname = 'ix_estudo_secao_oferta_ordem')
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'estudo_conteudo_secao' AND indexname = 'ix_estudo_conteudo_secao_secao_id')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

-- 007_cursos_backend_ms04.sql: registrada somente se toda a estrutura estiver presente.
INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
SELECT 7, 'cursos_backend_ms04', '007_cursos_backend_ms04.sql', 'detectada'
WHERE to_regclass('curso_versoes') IS NOT NULL
  AND to_regclass('curso_aula_conteudos') IS NOT NULL
  AND to_regclass('curso_retomadas') IS NOT NULL
  AND to_regclass('curso_aula_recursos') IS NOT NULL
  AND EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'curso_aula_recursos' AND indexname = 'ix_curso_aula_recursos_aula_id')
  AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'curso_aulas' AND column_name = 'video_id' AND is_nullable = 'YES')
ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;

INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)
VALUES (8, 'registro_migracoes', '008_registro_migracoes.sql', 'aplicada');

COMMIT;

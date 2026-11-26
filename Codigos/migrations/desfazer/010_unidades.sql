-- DESFAZER A MIGRATION 010 (unidades), aprovada em 25/11/2026. Uso só em emergência, antes de existir uma 2ª unidade.
-- Preferir sempre a restauração do backup feito antes de aplicar a 010.
-- Recusa se já houver dados de outra unidade (eles se misturariam com a unidade 1).
BEGIN;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM unidades WHERE id <> 1) THEN
        RAISE EXCEPTION 'Há mais de uma unidade: desfazer misturaria os dados. Restaure o backup.';
    END IF;
END $$;

DROP TABLE transferencias_unidade;
DROP TRIGGER tg_alunos_turmas_vinculo ON alunos_turmas;
DROP TRIGGER tg_professores_turmas_vinculo ON professores_turmas;
DROP TRIGGER tg_atribuicoes_docentes_vinculo ON atribuicoes_docentes;
DROP FUNCTION edufast_exige_vinculo();

ALTER TABLE turmas_disciplinas DROP COLUMN unidade_id;
ALTER TABLE documentos DROP COLUMN unidade_id;
ALTER TABLE frequencia_atestados DROP COLUMN unidade_id;
ALTER TABLE solicitacoes_documentos DROP COLUMN unidade_id;
ALTER TABLE solicitacoes_alteracoes DROP COLUMN unidade_id;
ALTER TABLE comunicados DROP COLUMN unidade_id;
ALTER TABLE escola_calendarios DROP COLUMN unidade_id;
ALTER TABLE escola_calendarios ADD CONSTRAINT escola_calendarios_ano_key UNIQUE (ano);
ALTER TABLE disciplinas DROP COLUMN unidade_id;
ALTER TABLE disciplinas ADD CONSTRAINT disciplinas_codigo_key UNIQUE (codigo);
ALTER TABLE turmas DROP COLUMN unidade_id;
ALTER TABLE turmas ADD CONSTRAINT turmas_codigo_key UNIQUE (codigo);

DROP TABLE usuario_unidades;
DROP TABLE unidades;
DELETE FROM educafast_migracoes WHERE versao = 10;
COMMIT;

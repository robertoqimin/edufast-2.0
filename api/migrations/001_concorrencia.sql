-- PENDENTE DE REVISAO HUMANA. Nao executar automaticamente.
-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.
-- Gerado por migrations/gerar_postgresql.py a partir dos modelos; revisar antes de executar.
-- Aplicar com: psql -v ON_ERROR_STOP=1 -f <arquivo>

BEGIN;

ALTER TABLE alunos ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;
ALTER TABLE professores ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;
ALTER TABLE notas ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;

CREATE TABLE idempotencias (
	id SERIAL NOT NULL,
	ator VARCHAR(40) NOT NULL,
	operacao VARCHAR(100) NOT NULL,
	chave VARCHAR(128) NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	resposta TEXT NOT NULL,
	status_http INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_envio UNIQUE (ator, operacao, chave)
);

-- Constraints antigas ausentes precisam de DDL separado revisado apos preflight.
-- Este arquivo nao elimina nem consolida registros antigos.

COMMIT;

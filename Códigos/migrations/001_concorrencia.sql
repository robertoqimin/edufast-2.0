-- PENDENTE DE REVISAO HUMANA. Nao executar automaticamente.
-- MySQL 8.4. Rodar preflight, conferir backup e plano de recuperacao antes.
-- DDL MySQL tem commits implicitos: nao e uma transacao reversivel.
ALTER TABLE alunos ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;
ALTER TABLE professores ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;
ALTER TABLE notas ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;
CREATE TABLE idempotencias (
    id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
    ator VARCHAR(40) NOT NULL,
    operacao VARCHAR(100) NOT NULL,
    chave VARCHAR(128) NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    resposta TEXT NOT NULL,
    status_http INTEGER NOT NULL,
    CONSTRAINT uq_envio UNIQUE (ator, operacao, chave)
);
-- Constraints antigas ausentes precisam de DDL separado revisado apos preflight.
-- Este arquivo nao elimina nem consolida registros antigos.

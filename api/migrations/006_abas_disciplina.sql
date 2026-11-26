-- PROPOSTA 006: abas docentes. REVISAR antes de executar.
-- Compilada offline; nenhuma migration executada. Requer proposta 005.
-- Preserva conteudos existentes, arquivos, aprovacoes e vinculos.
-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.
-- Gerado por migrations/gerar_postgresql.py a partir dos modelos; revisar antes de executar.
-- Aplicar com: psql -v ON_ERROR_STOP=1 -f <arquivo>

BEGIN;

CREATE TABLE estudo_secoes (
	id SERIAL NOT NULL,
	turma_disciplina_id INTEGER NOT NULL,
	autor_id INTEGER NOT NULL,
	nome VARCHAR(80) NOT NULL,
	ordem INTEGER NOT NULL,
	estado VARCHAR(12) NOT NULL,
	versao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_estudo_secao_estado CHECK (estado IN ('ativa','arquivada')),
	CONSTRAINT ck_estudo_secao_ordem CHECK (ordem BETWEEN 0 AND 9999),
	CONSTRAINT ck_estudo_secao_versao CHECK (versao >= 1),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id),
	FOREIGN KEY(autor_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_estudo_secao_oferta_ordem ON estudo_secoes (turma_disciplina_id, ordem, id);

CREATE TABLE estudo_conteudo_secao (
	conteudo_id INTEGER NOT NULL,
	secao_id INTEGER NOT NULL,
	PRIMARY KEY (conteudo_id),
	FOREIGN KEY(conteudo_id) REFERENCES estudo_conteudos (id),
	FOREIGN KEY(secao_id) REFERENCES estudo_secoes (id)
);
CREATE INDEX ix_estudo_conteudo_secao_secao_id ON estudo_conteudo_secao (secao_id);

CREATE TABLE estudo_secao_auditoria (
	id SERIAL NOT NULL,
	secao_id INTEGER NOT NULL,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(30) NOT NULL,
	nome VARCHAR(80) NOT NULL,
	ordem INTEGER NOT NULL,
	estado VARCHAR(12) NOT NULL,
	versao INTEGER NOT NULL,
	criada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(secao_id) REFERENCES estudo_secoes (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);

COMMIT;

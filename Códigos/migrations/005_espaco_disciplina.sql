-- PROPOSTA 005: avisos e materiais por turma/disciplina. REVISAR antes de executar.
-- Nao executada em banco persistente. Sem conversao de dados ou permissoes.
-- Fazer backup consistente de banco/uploads e guardar DATA_ENCRYPTION_KEY.
-- Requer as tabelas de usuarios e turmas/disciplinas existentes.


CREATE TABLE estudo_conteudos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	turma_disciplina_id INTEGER NOT NULL,
	autor_id INTEGER NOT NULL,
	tipo VARCHAR(12) NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	texto TEXT NOT NULL,
	link VARCHAR(2048) NOT NULL,
	arquivo VARCHAR(36),
	mime VARCHAR(32),
	tamanho INTEGER,
	estado VARCHAR(12) NOT NULL,
	versao INTEGER NOT NULL,
	criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT ck_estudo_tipo CHECK (tipo IN ('aviso','link','arquivo')),
	CONSTRAINT ck_estudo_estado CHECK (estado IN ('rascunho','publicado','arquivado')),
	CONSTRAINT ck_estudo_versao CHECK (versao >= 1),
	CONSTRAINT ck_estudo_recurso CHECK ((tipo = 'arquivo' AND arquivo IS NOT NULL AND mime IS NOT NULL AND tamanho IS NOT NULL AND tamanho BETWEEN 1 AND 5242880 AND link = '') OR (tipo = 'link' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link <> '') OR (tipo = 'aviso' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link = '')),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id),
	FOREIGN KEY(autor_id) REFERENCES usuarios (id),
	UNIQUE (arquivo)
);

CREATE INDEX ix_estudo_oferta_estado_id ON estudo_conteudos (turma_disciplina_id, estado, id);

CREATE TABLE estudo_auditoria (
	id INTEGER NOT NULL AUTO_INCREMENT,
	conteudo_id INTEGER NOT NULL,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(30) NOT NULL,
	criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(conteudo_id) REFERENCES estudo_conteudos (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);

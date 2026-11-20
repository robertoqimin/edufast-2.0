-- PROPOSTA 007 MS04 backend/API. REVISAR antes de executar.
-- Nenhuma migration foi executada em banco persistente.
-- Requer esquema escolar existente e tabelas de cursos da proposta 003.
-- Conferir dados legados, backup consistente banco/uploads/chave e ensaio isolado.
-- DDL MySQL pode deixar estado parcial: nao reexecutar sem inspecao.
-- Novos formatos requerem a API; frontend sera integrado posteriormente.

ALTER TABLE curso_aulas MODIFY COLUMN video_id VARCHAR(11) NULL;

CREATE TABLE curso_versoes (
	id INTEGER NOT NULL AUTO_INCREMENT,
	curso_id INTEGER NOT NULL,
	versao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_curso_versao_positiva CHECK (versao >= 1),
	UNIQUE (curso_id),
	FOREIGN KEY(curso_id) REFERENCES cursos (id)
);

CREATE TABLE curso_aula_conteudos (
	aula_id INTEGER NOT NULL,
	tipo VARCHAR(12) NOT NULL,
	corpo TEXT NOT NULL,
	PRIMARY KEY (aula_id),
	CONSTRAINT ck_curso_aula_tipo CHECK (tipo IN ('video','texto')),
	CONSTRAINT ck_curso_aula_texto CHECK (tipo <> 'texto' OR length(trim(corpo)) > 0),
	FOREIGN KEY(aula_id) REFERENCES curso_aulas (id)
);

CREATE TABLE curso_retomadas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	aluno_id INTEGER NOT NULL,
	oferta_id INTEGER NOT NULL,
	aula_id INTEGER NOT NULL,
	versao INTEGER NOT NULL,
	atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_curso_retomada_aluno_oferta UNIQUE (aluno_id, oferta_id),
	CONSTRAINT ck_curso_retomada_versao CHECK (versao >= 0),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(oferta_id) REFERENCES curso_ofertas (id),
	FOREIGN KEY(aula_id) REFERENCES curso_aulas (id)
);

CREATE TABLE curso_aula_recursos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	aula_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	tipo VARCHAR(12) NOT NULL,
	link VARCHAR(2048) NOT NULL,
	arquivo VARCHAR(36),
	mime VARCHAR(32),
	tamanho INTEGER,
	estado VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_curso_recurso_estado CHECK (estado IN ('ativo','arquivado')),
	CONSTRAINT ck_curso_recurso_tipo CHECK ((tipo = 'arquivo' AND arquivo IS NOT NULL AND mime IS NOT NULL AND tamanho BETWEEN 1 AND 5242880 AND tamanho IS NOT NULL AND link = '') OR (tipo = 'link' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link <> '')),
	FOREIGN KEY(aula_id) REFERENCES curso_aulas (id)
);

CREATE INDEX ix_curso_aula_recursos_aula_id ON curso_aula_recursos (aula_id);

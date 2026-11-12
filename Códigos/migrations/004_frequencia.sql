-- PROPOSTA 004: frequencia. REVISAR antes de executar. Sem IF NOT EXISTS.
-- Banco/uploads e DATA_ENCRYPTION_KEY devem ter backup recuperavel.
-- Nao cria atribuicoes docentes e nao converte presencas historicas.
CREATE TABLE frequencia_auditoria (
	id INTEGER NOT NULL AUTO_INCREMENT,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(40) NOT NULL,
	referencia INTEGER NOT NULL,
	criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);
CREATE TABLE frequencia_atestados (
	id INTEGER NOT NULL AUTO_INCREMENT,
	aluno_id INTEGER NOT NULL,
	inicio DATE NOT NULL,
	fim DATE NOT NULL,
	arquivo VARCHAR(64) NOT NULL,
	mime VARCHAR(30) NOT NULL,
	enviado_por INTEGER NOT NULL,
	estado VARCHAR(20) NOT NULL,
	versao INTEGER NOT NULL,
	decidido_por INTEGER,
	motivo TEXT NOT NULL,
	criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT ck_atestado_datas CHECK (fim >= inicio),
	CONSTRAINT ck_atestado_estado CHECK (estado IN ('pendente','aceito','rejeitado')),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	UNIQUE (arquivo),
	FOREIGN KEY(enviado_por) REFERENCES usuarios (id),
	FOREIGN KEY(decidido_por) REFERENCES usuarios (id)
);
CREATE INDEX ix_frequencia_atestados_aluno_id ON frequencia_atestados (aluno_id);
CREATE TABLE frequencia_chamadas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	turma_disciplina_id INTEGER NOT NULL,
	dia DATE NOT NULL,
	aula INTEGER NOT NULL,
	revisao INTEGER NOT NULL,
	anterior_id INTEGER,
	autor_id INTEGER NOT NULL,
	estado VARCHAR(20) NOT NULL,
	versao INTEGER NOT NULL,
	decidido_por INTEGER,
	motivo TEXT NOT NULL,
	decisao_motivo TEXT NOT NULL,
	criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_chamada_revisao UNIQUE (turma_disciplina_id, dia, aula, revisao),
	CONSTRAINT ck_chamada_aula CHECK (aula >= 1 AND aula <= 20),
	CONSTRAINT ck_chamada_estado CHECK (estado IN ('pendente','aprovada','rejeitada','substituida')),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id),
	FOREIGN KEY(anterior_id) REFERENCES frequencia_chamadas (id),
	FOREIGN KEY(autor_id) REFERENCES usuarios (id),
	FOREIGN KEY(decidido_por) REFERENCES usuarios (id)
);
CREATE TABLE frequencia_presencas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	chamada_id INTEGER NOT NULL,
	aluno_id INTEGER NOT NULL,
	situacao VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_presenca_aluno UNIQUE (chamada_id, aluno_id),
	CONSTRAINT ck_presenca_situacao CHECK (situacao IN ('presente','falta')),
	FOREIGN KEY(chamada_id) REFERENCES frequencia_chamadas (id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id)
);

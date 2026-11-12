-- PENDENTE DE REVISAO DO USUARIO. NAO EXECUTAR AUTOMATICAMENTE.
-- Restauracao baseada em Projeto-Educa-Fast cb27d3c; depois de 001 e 002 revisadas.
-- Somente tabelas novas. Sem DELETE, sem inferir vinculos historicos.
-- MySQL 8.4: DDL tem commits implicitos; backup e janela de manutencao necessarios.


CREATE TABLE configuracoes (
	id INTEGER NOT NULL AUTO_INCREMENT,
	cor_fundo VARCHAR(7) NOT NULL,
	cor_destaque VARCHAR(7) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE educafast_migracoes (
	versao INTEGER NOT NULL,
	PRIMARY KEY (versao)
);

CREATE TABLE escola_calendarios (
	id INTEGER NOT NULL AUTO_INCREMENT,
	ano INTEGER NOT NULL,
	nome VARCHAR(120) NOT NULL,
	inicio DATE NOT NULL,
	fim DATE NOT NULL,
	dias_semana VARCHAR(30) NOT NULL,
	meta_letivos INTEGER NOT NULL,
	versao INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (ano)
);

CREATE TABLE escola_identidade (
	id INTEGER NOT NULL,
	versao INTEGER NOT NULL,
	dados TEXT NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE limites_login (
	chave VARCHAR(64) NOT NULL,
	janela INTEGER NOT NULL,
	tentativas INTEGER NOT NULL,
	PRIMARY KEY (chave)
);

CREATE INDEX ix_limites_login_janela ON limites_login (janela);

CREATE TABLE academico_auditoria (
	id INTEGER NOT NULL AUTO_INCREMENT,
	usuario_id INTEGER NOT NULL,
	acao VARCHAR(60) NOT NULL,
	recurso VARCHAR(100) NOT NULL,
	detalhe TEXT NOT NULL,
	criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE TABLE academico_periodos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	turma_id INTEGER NOT NULL,
	nome VARCHAR(80) NOT NULL,
	ordem INTEGER NOT NULL,
	media_referencia NUMERIC(4, 2) NOT NULL,
	fechado BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_periodo_nome UNIQUE (turma_id, nome),
	CONSTRAINT uq_periodo_ordem UNIQUE (turma_id, ordem),
	CONSTRAINT ck_periodo_media CHECK (media_referencia >= 0 AND media_referencia <= 10),
	FOREIGN KEY(turma_id) REFERENCES turmas (id)
);

CREATE TABLE auditoria_privacidade (
	id INTEGER NOT NULL AUTO_INCREMENT,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(50) NOT NULL,
	referencia INTEGER,
	criado_em DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);

CREATE TABLE curso_auditoria (
	id INTEGER NOT NULL AUTO_INCREMENT,
	usuario_id INTEGER NOT NULL,
	acao VARCHAR(60) NOT NULL,
	recurso VARCHAR(120) NOT NULL,
	criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE TABLE escola_eventos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	calendario_id INTEGER NOT NULL,
	dia DATE NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	tipo VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_evento_calendario_dia UNIQUE (calendario_id, dia),
	FOREIGN KEY(calendario_id) REFERENCES escola_calendarios (id)
);

CREATE TABLE escola_politicas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	calendario_id INTEGER NOT NULL,
	nome VARCHAR(120) NOT NULL,
	configuracao TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(calendario_id) REFERENCES escola_calendarios (id)
);

CREATE TABLE pedidos_privacidade (
	id INTEGER NOT NULL AUTO_INCREMENT,
	usuario_id INTEGER NOT NULL,
	tipo VARCHAR(30) NOT NULL,
	detalhe TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	resposta TEXT NOT NULL,
	criado_em DATETIME NOT NULL,
	atualizado_em DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_pedidos_privacidade_usuario_id ON pedidos_privacidade (usuario_id);

CREATE TABLE turma_estados (
	turma_id INTEGER NOT NULL,
	arquivada BOOL NOT NULL,
	PRIMARY KEY (turma_id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id)
);

CREATE TABLE academico_avaliacoes (
	id INTEGER NOT NULL AUTO_INCREMENT,
	turma_disciplina_id INTEGER NOT NULL,
	periodo_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	peso NUMERIC(6, 2) NOT NULL,
	publicada BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_avaliacao_peso CHECK (peso > 0 AND peso <= 100),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id),
	FOREIGN KEY(periodo_id) REFERENCES academico_periodos (id)
);

CREATE TABLE atribuicoes_docentes (
	id INTEGER NOT NULL AUTO_INCREMENT,
	professor_id INTEGER NOT NULL,
	turma_disciplina_id INTEGER NOT NULL,
	ativo BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_atribuicao_docente UNIQUE (professor_id, turma_disciplina_id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id)
);

CREATE TABLE cursos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	disciplina_id INTEGER NOT NULL,
	professor_id INTEGER NOT NULL,
	origem_id INTEGER,
	titulo VARCHAR(150) NOT NULL,
	descricao TEXT NOT NULL,
	estado VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_curso_estado CHECK (estado IN ('rascunho','publicado','arquivado')),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(origem_id) REFERENCES cursos (id)
);

CREATE TABLE escola_regras_periodos (
	periodo_id INTEGER NOT NULL,
	politica_id INTEGER NOT NULL,
	ordem INTEGER NOT NULL,
	PRIMARY KEY (periodo_id),
	FOREIGN KEY(periodo_id) REFERENCES academico_periodos (id),
	FOREIGN KEY(politica_id) REFERENCES escola_politicas (id)
);

CREATE TABLE escola_regras_turmas (
	turma_id INTEGER NOT NULL,
	politica_id INTEGER NOT NULL,
	PRIMARY KEY (turma_id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id),
	FOREIGN KEY(politica_id) REFERENCES escola_politicas (id)
);

CREATE TABLE academico_notas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	avaliacao_id INTEGER NOT NULL,
	aluno_id INTEGER NOT NULL,
	professor_id INTEGER NOT NULL,
	valor NUMERIC(4, 2) NOT NULL,
	observacao VARCHAR(255) NOT NULL,
	versao INTEGER NOT NULL,
	nota_legada_id INTEGER,
	atualizada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_lancamento_aluno UNIQUE (avaliacao_id, aluno_id),
	CONSTRAINT ck_lancamento_valor CHECK (valor >= 0 AND valor <= 10),
	FOREIGN KEY(avaliacao_id) REFERENCES academico_avaliacoes (id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	UNIQUE (nota_legada_id),
	FOREIGN KEY(nota_legada_id) REFERENCES notas (id)
);

CREATE TABLE curso_capitulos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	curso_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	posicao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_capitulo_posicao UNIQUE (curso_id, posicao),
	FOREIGN KEY(curso_id) REFERENCES cursos (id)
);

CREATE TABLE curso_ofertas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	curso_id INTEGER NOT NULL,
	turma_disciplina_id INTEGER NOT NULL,
	ativa BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_curso_oferta UNIQUE (curso_id, turma_disciplina_id),
	FOREIGN KEY(curso_id) REFERENCES cursos (id),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id)
);

CREATE TABLE curso_temas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	capitulo_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	posicao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_tema_posicao UNIQUE (capitulo_id, posicao),
	FOREIGN KEY(capitulo_id) REFERENCES curso_capitulos (id)
);

CREATE TABLE curso_aulas (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tema_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	descricao TEXT NOT NULL,
	video_id VARCHAR(11) NOT NULL,
	posicao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_aula_posicao UNIQUE (tema_id, posicao),
	FOREIGN KEY(tema_id) REFERENCES curso_temas (id)
);

CREATE TABLE curso_progressos (
	id INTEGER NOT NULL AUTO_INCREMENT,
	aluno_id INTEGER NOT NULL,
	oferta_id INTEGER NOT NULL,
	aula_id INTEGER NOT NULL,
	concluida_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_progresso_oferta_aula UNIQUE (aluno_id, oferta_id, aula_id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(oferta_id) REFERENCES curso_ofertas (id),
	FOREIGN KEY(aula_id) REFERENCES curso_aulas (id)
);

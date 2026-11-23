-- ESQUEMA BASE v8: cria o banco COMPLETO de uma escola nova. REVISAR antes de executar.
-- Equivale ao esquema legado com as propostas 001-008 aplicadas em sequencia;
-- o CI compara os dois caminhos em PostgreSQL. Somente para banco VAZIO.
-- O registro marca cada versao como aplicada por este arquivo (checksum: ver A4).
-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.
-- Gerado por migrations/gerar_postgresql.py a partir dos modelos; revisar antes de executar.
-- Aplicar com: psql -v ON_ERROR_STOP=1 -f <arquivo>

BEGIN;

CREATE TABLE comunicados (
	id SERIAL NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	destinatario VARCHAR(80) NOT NULL,
	mensagem TEXT NOT NULL,
	criado_por VARCHAR(120),
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE configuracoes (
	id SERIAL NOT NULL,
	cor_fundo VARCHAR(7) NOT NULL,
	cor_destaque VARCHAR(7) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE disciplinas (
	id SERIAL NOT NULL,
	nome VARCHAR(120) NOT NULL,
	codigo VARCHAR(30) NOT NULL,
	carga_horaria INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (codigo)
);

CREATE TABLE educafast_migracoes (
	versao INTEGER NOT NULL,
	descricao VARCHAR(120),
	arquivo VARCHAR(120),
	checksum VARCHAR(64),
	aplicada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	origem VARCHAR(12) DEFAULT 'aplicada' NOT NULL,
	PRIMARY KEY (versao),
	CONSTRAINT ck_migracao_origem CHECK (origem IN ('aplicada','detectada')),
	CONSTRAINT ck_migracao_checksum CHECK (checksum IS NULL OR length(checksum) = 64)
);

CREATE TABLE escola_calendarios (
	id SERIAL NOT NULL,
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

CREATE TABLE limites_login (
	chave VARCHAR(64) NOT NULL,
	janela INTEGER NOT NULL,
	tentativas INTEGER NOT NULL,
	PRIMARY KEY (chave)
);
CREATE INDEX ix_limites_login_janela ON limites_login (janela);

CREATE TABLE turmas (
	id SERIAL NOT NULL,
	nome VARCHAR(120) NOT NULL,
	codigo VARCHAR(30) NOT NULL,
	ano_letivo INTEGER NOT NULL,
	turno VARCHAR(30),
	PRIMARY KEY (id),
	UNIQUE (codigo)
);

CREATE TABLE usuarios (
	id SERIAL NOT NULL,
	email VARCHAR(120) NOT NULL,
	senha VARCHAR(200) NOT NULL,
	tipo VARCHAR(20) NOT NULL,
	estado VARCHAR(20) DEFAULT 'ativo' NOT NULL,
	revisor_materiais BOOLEAN DEFAULT false NOT NULL,
	auth_version INTEGER DEFAULT '0' NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
);

CREATE TABLE academico_auditoria (
	id SERIAL NOT NULL,
	usuario_id INTEGER NOT NULL,
	acao VARCHAR(60) NOT NULL,
	recurso VARCHAR(100) NOT NULL,
	detalhe TEXT NOT NULL,
	criada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE TABLE academico_periodos (
	id SERIAL NOT NULL,
	turma_id INTEGER NOT NULL,
	nome VARCHAR(80) NOT NULL,
	ordem INTEGER NOT NULL,
	media_referencia NUMERIC(4, 2) NOT NULL,
	fechado BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_periodo_nome UNIQUE (turma_id, nome),
	CONSTRAINT uq_periodo_ordem UNIQUE (turma_id, ordem),
	CONSTRAINT ck_periodo_media CHECK (media_referencia >= 0 AND media_referencia <= 10),
	FOREIGN KEY(turma_id) REFERENCES turmas (id)
);

CREATE TABLE alunos (
	versao INTEGER DEFAULT '1' NOT NULL,
	id SERIAL NOT NULL,
	usuario_id INTEGER NOT NULL,
	nome VARCHAR(120) NOT NULL,
	cpf VARCHAR(14),
	matricula VARCHAR(30) NOT NULL,
	curso_serie VARCHAR(80),
	status_matricula VARCHAR(20),
	foto_perfil VARCHAR(255),
	data_nascimento DATE,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (usuario_id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id),
	UNIQUE (cpf),
	UNIQUE (matricula)
);

CREATE TABLE auditoria_privacidade (
	id SERIAL NOT NULL,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(50) NOT NULL,
	referencia INTEGER,
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);

CREATE TABLE curso_auditoria (
	id SERIAL NOT NULL,
	usuario_id INTEGER NOT NULL,
	acao VARCHAR(60) NOT NULL,
	recurso VARCHAR(120) NOT NULL,
	criada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE TABLE escola_eventos (
	id SERIAL NOT NULL,
	calendario_id INTEGER NOT NULL,
	dia DATE NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	tipo VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_evento_calendario_dia UNIQUE (calendario_id, dia),
	FOREIGN KEY(calendario_id) REFERENCES escola_calendarios (id)
);

CREATE TABLE escola_politicas (
	id SERIAL NOT NULL,
	calendario_id INTEGER NOT NULL,
	nome VARCHAR(120) NOT NULL,
	configuracao TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(calendario_id) REFERENCES escola_calendarios (id)
);

CREATE TABLE frequencia_auditoria (
	id SERIAL NOT NULL,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(40) NOT NULL,
	referencia INTEGER NOT NULL,
	criada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);

CREATE TABLE pedidos_privacidade (
	id SERIAL NOT NULL,
	usuario_id INTEGER NOT NULL,
	tipo VARCHAR(30) NOT NULL,
	detalhe TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	resposta TEXT NOT NULL,
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_pedidos_privacidade_usuario_id ON pedidos_privacidade (usuario_id);

CREATE TABLE professores (
	versao INTEGER DEFAULT '1' NOT NULL,
	id SERIAL NOT NULL,
	usuario_id INTEGER NOT NULL,
	nome VARCHAR(120) NOT NULL,
	cpf VARCHAR(14) NOT NULL,
	telefone VARCHAR(20),
	disciplina_principal VARCHAR(80),
	formacao_academica VARCHAR(120),
	regime_trabalho VARCHAR(50),
	foto_perfil VARCHAR(255),
	data_admissao DATE,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (usuario_id),
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id),
	UNIQUE (cpf)
);

CREATE TABLE solicitacoes_alteracoes (
	id SERIAL NOT NULL,
	solicitante_id INTEGER NOT NULL,
	tipo VARCHAR(40) NOT NULL,
	payload TEXT NOT NULL,
	estado VARCHAR(20) NOT NULL,
	recurso_pendente VARCHAR(128),
	arquivo VARCHAR(255),
	decidido_por INTEGER,
	justificativa VARCHAR(500),
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	decided_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(solicitante_id) REFERENCES usuarios (id),
	UNIQUE (recurso_pendente),
	FOREIGN KEY(decidido_por) REFERENCES usuarios (id)
);

CREATE TABLE turma_estados (
	turma_id INTEGER NOT NULL,
	arquivada BOOLEAN NOT NULL,
	PRIMARY KEY (turma_id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id)
);

CREATE TABLE turmas_disciplinas (
	id SERIAL NOT NULL,
	turma_id INTEGER NOT NULL,
	disciplina_id INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_turma_disciplina UNIQUE (turma_id, disciplina_id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id)
);

CREATE TABLE academico_avaliacoes (
	id SERIAL NOT NULL,
	turma_disciplina_id INTEGER NOT NULL,
	periodo_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	peso NUMERIC(6, 2) NOT NULL,
	publicada BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_avaliacao_peso CHECK (peso > 0 AND peso <= 100),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id),
	FOREIGN KEY(periodo_id) REFERENCES academico_periodos (id)
);

CREATE TABLE alunos_disciplinas (
	id SERIAL NOT NULL,
	aluno_id INTEGER NOT NULL,
	disciplina_id INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_aluno_disciplina UNIQUE (aluno_id, disciplina_id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id)
);

CREATE TABLE alunos_turmas (
	id SERIAL NOT NULL,
	aluno_id INTEGER NOT NULL,
	turma_id INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_aluno_turma UNIQUE (aluno_id, turma_id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id)
);

CREATE TABLE atividades (
	id SERIAL NOT NULL,
	professor_id INTEGER NOT NULL,
	turma_id INTEGER NOT NULL,
	disciplina_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	descricao TEXT,
	data_entrega VARCHAR(10),
	caminho_arquivo VARCHAR(255),
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id)
);

CREATE TABLE atribuicoes_docentes (
	id SERIAL NOT NULL,
	professor_id INTEGER NOT NULL,
	turma_disciplina_id INTEGER NOT NULL,
	ativo BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_atribuicao_docente UNIQUE (professor_id, turma_disciplina_id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id)
);

CREATE TABLE cursos (
	id SERIAL NOT NULL,
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

CREATE TABLE documentos (
	id SERIAL NOT NULL,
	aluno_id INTEGER,
	professor_id INTEGER,
	disciplina_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	caminho_arquivo VARCHAR(255) NOT NULL,
	data_envio TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id)
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

CREATE TABLE estudo_conteudos (
	id SERIAL NOT NULL,
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
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
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

CREATE TABLE frequencia_atestados (
	id SERIAL NOT NULL,
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
	criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
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
	id SERIAL NOT NULL,
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
	criada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_chamada_revisao UNIQUE (turma_disciplina_id, dia, aula, revisao),
	CONSTRAINT ck_chamada_aula CHECK (aula >= 1 AND aula <= 20),
	CONSTRAINT ck_chamada_estado CHECK (estado IN ('pendente','aprovada','rejeitada','substituida')),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id),
	FOREIGN KEY(anterior_id) REFERENCES frequencia_chamadas (id),
	FOREIGN KEY(autor_id) REFERENCES usuarios (id),
	FOREIGN KEY(decidido_por) REFERENCES usuarios (id)
);

CREATE TABLE notas (
	versao INTEGER DEFAULT '1' NOT NULL,
	id SERIAL NOT NULL,
	aluno_id INTEGER NOT NULL,
	disciplina_id INTEGER NOT NULL,
	professor_id INTEGER NOT NULL,
	nota DECIMAL(4, 2) NOT NULL,
	observacao VARCHAR(255),
	data_lancamento TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_nota_aluno_disciplina UNIQUE (aluno_id, disciplina_id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id),
	FOREIGN KEY(professor_id) REFERENCES professores (id)
);

CREATE TABLE professores_disciplinas (
	id SERIAL NOT NULL,
	professor_id INTEGER NOT NULL,
	disciplina_id INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_professor_disciplina UNIQUE (professor_id, disciplina_id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id)
);

CREATE TABLE professores_turmas (
	id SERIAL NOT NULL,
	professor_id INTEGER NOT NULL,
	turma_id INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_professor_turma UNIQUE (professor_id, turma_id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(turma_id) REFERENCES turmas (id)
);

CREATE TABLE academico_notas (
	id SERIAL NOT NULL,
	avaliacao_id INTEGER NOT NULL,
	aluno_id INTEGER NOT NULL,
	professor_id INTEGER NOT NULL,
	valor NUMERIC(4, 2) NOT NULL,
	observacao VARCHAR(255) NOT NULL,
	versao INTEGER NOT NULL,
	nota_legada_id INTEGER,
	atualizada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
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
	id SERIAL NOT NULL,
	curso_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	posicao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_capitulo_posicao UNIQUE (curso_id, posicao),
	FOREIGN KEY(curso_id) REFERENCES cursos (id)
);

CREATE TABLE curso_ofertas (
	id SERIAL NOT NULL,
	curso_id INTEGER NOT NULL,
	turma_disciplina_id INTEGER NOT NULL,
	ativa BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_curso_oferta UNIQUE (curso_id, turma_disciplina_id),
	FOREIGN KEY(curso_id) REFERENCES cursos (id),
	FOREIGN KEY(turma_disciplina_id) REFERENCES turmas_disciplinas (id)
);

CREATE TABLE curso_versoes (
	id SERIAL NOT NULL,
	curso_id INTEGER NOT NULL,
	versao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_curso_versao_positiva CHECK (versao >= 1),
	UNIQUE (curso_id),
	FOREIGN KEY(curso_id) REFERENCES cursos (id)
);

CREATE TABLE estudo_auditoria (
	id SERIAL NOT NULL,
	conteudo_id INTEGER NOT NULL,
	ator_id INTEGER NOT NULL,
	acao VARCHAR(30) NOT NULL,
	criada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(conteudo_id) REFERENCES estudo_conteudos (id),
	FOREIGN KEY(ator_id) REFERENCES usuarios (id)
);

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

CREATE TABLE frequencia_presencas (
	id SERIAL NOT NULL,
	chamada_id INTEGER NOT NULL,
	aluno_id INTEGER NOT NULL,
	situacao VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_presenca_aluno UNIQUE (chamada_id, aluno_id),
	CONSTRAINT ck_presenca_situacao CHECK (situacao IN ('presente','falta')),
	FOREIGN KEY(chamada_id) REFERENCES frequencia_chamadas (id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id)
);

CREATE TABLE solicitacoes_documentos (
	id SERIAL NOT NULL,
	aluno_id INTEGER,
	professor_id INTEGER,
	documento_id INTEGER,
	titulo VARCHAR(150) NOT NULL,
	mensagem TEXT,
	status VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	completed_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(professor_id) REFERENCES professores (id),
	FOREIGN KEY(documento_id) REFERENCES documentos (id)
);

CREATE TABLE curso_temas (
	id SERIAL NOT NULL,
	capitulo_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	posicao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_tema_posicao UNIQUE (capitulo_id, posicao),
	FOREIGN KEY(capitulo_id) REFERENCES curso_capitulos (id)
);

CREATE TABLE curso_aulas (
	id SERIAL NOT NULL,
	tema_id INTEGER NOT NULL,
	titulo VARCHAR(150) NOT NULL,
	descricao TEXT NOT NULL,
	video_id VARCHAR(11),
	posicao INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_aula_posicao UNIQUE (tema_id, posicao),
	FOREIGN KEY(tema_id) REFERENCES curso_temas (id)
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

CREATE TABLE curso_aula_recursos (
	id SERIAL NOT NULL,
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

CREATE TABLE curso_progressos (
	id SERIAL NOT NULL,
	aluno_id INTEGER NOT NULL,
	oferta_id INTEGER NOT NULL,
	aula_id INTEGER NOT NULL,
	concluida_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_progresso_oferta_aula UNIQUE (aluno_id, oferta_id, aula_id),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(oferta_id) REFERENCES curso_ofertas (id),
	FOREIGN KEY(aula_id) REFERENCES curso_aulas (id)
);

CREATE TABLE curso_retomadas (
	id SERIAL NOT NULL,
	aluno_id INTEGER NOT NULL,
	oferta_id INTEGER NOT NULL,
	aula_id INTEGER NOT NULL,
	versao INTEGER NOT NULL,
	atualizado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_curso_retomada_aluno_oferta UNIQUE (aluno_id, oferta_id),
	CONSTRAINT ck_curso_retomada_versao CHECK (versao >= 0),
	FOREIGN KEY(aluno_id) REFERENCES alunos (id),
	FOREIGN KEY(oferta_id) REFERENCES curso_ofertas (id),
	FOREIGN KEY(aula_id) REFERENCES curso_aulas (id)
);

INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem) VALUES
    (1, 'concorrencia', 'base/esquema_v8.sql', 'aplicada'),
    (2, 'aprovacoes_e_permissoes', 'base/esquema_v8.sql', 'aplicada'),
    (3, 'restauracao_educafast', 'base/esquema_v8.sql', 'aplicada'),
    (4, 'frequencia', 'base/esquema_v8.sql', 'aplicada'),
    (5, 'espaco_disciplina', 'base/esquema_v8.sql', 'aplicada'),
    (6, 'abas_disciplina', 'base/esquema_v8.sql', 'aplicada'),
    (7, 'cursos_backend_ms04', 'base/esquema_v8.sql', 'aplicada'),
    (8, 'registro_migracoes', 'base/esquema_v8.sql', 'aplicada');

COMMIT;

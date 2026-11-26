-- PROPOSTA 010 — UNIDADES (25/11/2026) — APROVADA PELO USUÁRIO EM 25/11/2026.
-- Colégio e faculdade na mesma instalação, com secretarias separadas.
-- Estudo:  Documentos/planejamento/ESTUDO_UNIDADES_2026-11-25.md
-- Ficha:   Documentos/planejamento/PROPOSTA_010_UNIDADES_2026-11-25.md (riscos e como desfazer)
-- Desfazer: migrations/desfazer/010_unidades.sql (só antes de existir a 2ª unidade).
-- Aplicar SOMENTE junto com o back-end das unidades: as colunas unidade_id não têm valor padrão.
-- Blocos "base:" entram também no esquema base v10 (gerar_postgresql.py) e no create_all dos testes.
-- PostgreSQL 17, transacional: uma falha desfaz tudo. Em banco real, só pelo aplicar_migracoes.py,
-- depois de backup de banco, uploads e chave.
-- O que faz com os dados de hoje: a instalação vira a UNIDADE 1 (nível básico); todas as linhas
-- existentes recebem unidade_id = 1 e todas as contas (menos o super admin, que vê todas) ganham
-- vínculo com a unidade 1. Nenhuma linha é apagada; nenhum valor existente é alterado.
-- Não liga a Row-Level Security: ela é a proposta 011, aplicada só depois que o back-end
-- informar a unidade em cada transação (sem isso, a aplicação deixaria de enxergar os dados).
-- Numeração: 011 = Row-Level Security; 012 = ofertas extras (B4, antes 010); 013 = passagem de ano.
BEGIN;

-- 1. Unidades ------------------------------------------------------------------------------
CREATE TABLE unidades (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    nivel VARCHAR(10) NOT NULL,
    estado VARCHAR(10) NOT NULL DEFAULT 'ativa',
    rotulo_turma VARCHAR(30) NOT NULL DEFAULT 'Turma',
    rotulo_serie VARCHAR(30) NOT NULL DEFAULT 'Série',
    rotulo_periodo VARCHAR(30) NOT NULL DEFAULT 'Bimestre',
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_unidade_nome UNIQUE (nome),
    CONSTRAINT ck_unidade_nivel CHECK (nivel IN ('basico', 'superior')),
    CONSTRAINT ck_unidade_estado CHECK (estado IN ('ativa', 'arquivada'))
);
-- A instalação atual. O nome aparece no seletor e pode ser trocado pela direção depois.
-- base:dados:inicio
INSERT INTO unidades (id, nome, nivel) VALUES (1, 'Unidade principal', 'basico');
SELECT setval(pg_get_serial_sequence('unidades', 'id'), 1);
-- base:dados:fim

-- 2. Vínculo da pessoa com a unidade --------------------------------------------------------
-- situacao: ativo | concluido (concluiu o último ano da unidade: habilita a subida para a
-- faculdade pelo CPF) | revogado (perde o acesso àquela unidade na requisição seguinte).
CREATE TABLE usuario_unidades (
    usuario_id INTEGER NOT NULL REFERENCES usuarios (id),
    unidade_id INTEGER NOT NULL REFERENCES unidades (id),
    situacao VARCHAR(10) NOT NULL DEFAULT 'ativo',
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alterado_em TIMESTAMP,
    PRIMARY KEY (usuario_id, unidade_id),
    CONSTRAINT ck_vinculo_situacao CHECK (situacao IN ('ativo', 'concluido', 'revogado'))
);
CREATE INDEX ix_usuario_unidades_unidade ON usuario_unidades (unidade_id);
INSERT INTO usuario_unidades (usuario_id, unidade_id)
    SELECT id, 1 FROM usuarios WHERE lower(tipo) <> 'super_admin';

-- 3. Tabelas raiz ganham a unidade ----------------------------------------------------------
-- Padrão: coluna com DEFAULT 1 só para preencher as linhas atuais; o DEFAULT é retirado em
-- seguida, para que nenhum código novo grave numa unidade "por esquecimento".
ALTER TABLE turmas ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1 REFERENCES unidades (id);
ALTER TABLE turmas ALTER COLUMN unidade_id DROP DEFAULT;
ALTER TABLE turmas ADD CONSTRAINT uq_turma_id_unidade UNIQUE (id, unidade_id);
-- Código da turma passa a ser único POR UNIDADE (colégio e faculdade podem repetir "1A").
ALTER TABLE turmas DROP CONSTRAINT turmas_codigo_key;
ALTER TABLE turmas ADD CONSTRAINT uq_turma_unidade_codigo UNIQUE (unidade_id, codigo);
CREATE INDEX ix_turmas_unidade ON turmas (unidade_id);

ALTER TABLE disciplinas ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1 REFERENCES unidades (id);
ALTER TABLE disciplinas ALTER COLUMN unidade_id DROP DEFAULT;
ALTER TABLE disciplinas ADD CONSTRAINT uq_disciplina_id_unidade UNIQUE (id, unidade_id);
ALTER TABLE disciplinas DROP CONSTRAINT disciplinas_codigo_key;
ALTER TABLE disciplinas ADD CONSTRAINT uq_disciplina_unidade_codigo UNIQUE (unidade_id, codigo);
CREATE INDEX ix_disciplinas_unidade ON disciplinas (unidade_id);

-- Calendário: o colégio tem o ano letivo; a faculdade, os semestres. Ano único POR UNIDADE.
ALTER TABLE escola_calendarios ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1 REFERENCES unidades (id);
ALTER TABLE escola_calendarios ALTER COLUMN unidade_id DROP DEFAULT;
ALTER TABLE escola_calendarios DROP CONSTRAINT escola_calendarios_ano_key;
ALTER TABLE escola_calendarios ADD CONSTRAINT uq_calendario_unidade_ano UNIQUE (unidade_id, ano);

-- Comunicado sem unidade (NULL) = enviado pelo super admin para todas as unidades.
ALTER TABLE comunicados ADD COLUMN unidade_id INTEGER REFERENCES unidades (id);
UPDATE comunicados SET unidade_id = 1;
CREATE INDEX ix_comunicados_unidade ON comunicados (unidade_id);

ALTER TABLE solicitacoes_alteracoes ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1 REFERENCES unidades (id);
ALTER TABLE solicitacoes_alteracoes ALTER COLUMN unidade_id DROP DEFAULT;
CREATE INDEX ix_solicitacoes_alteracoes_unidade ON solicitacoes_alteracoes (unidade_id, estado);

ALTER TABLE solicitacoes_documentos ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1 REFERENCES unidades (id);
ALTER TABLE solicitacoes_documentos ALTER COLUMN unidade_id DROP DEFAULT;
CREATE INDEX ix_solicitacoes_documentos_unidade ON solicitacoes_documentos (unidade_id);

ALTER TABLE frequencia_atestados ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1 REFERENCES unidades (id);
ALTER TABLE frequencia_atestados ALTER COLUMN unidade_id DROP DEFAULT;
CREATE INDEX ix_frequencia_atestados_unidade ON frequencia_atestados (unidade_id);

-- Documento pertence à unidade da sua disciplina (chave composta: não há como divergir).
ALTER TABLE documentos ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1;
ALTER TABLE documentos ALTER COLUMN unidade_id DROP DEFAULT;
ALTER TABLE documentos ADD CONSTRAINT fk_documento_disciplina_unidade
    FOREIGN KEY (disciplina_id, unidade_id) REFERENCES disciplinas (id, unidade_id);

-- 4. Turma e disciplina ligadas precisam ser da MESMA unidade ------------------------------
ALTER TABLE turmas_disciplinas ADD COLUMN unidade_id INTEGER NOT NULL DEFAULT 1;
ALTER TABLE turmas_disciplinas ALTER COLUMN unidade_id DROP DEFAULT;
ALTER TABLE turmas_disciplinas ADD CONSTRAINT fk_turma_disciplina_turma_unidade
    FOREIGN KEY (turma_id, unidade_id) REFERENCES turmas (id, unidade_id);
ALTER TABLE turmas_disciplinas ADD CONSTRAINT fk_turma_disciplina_disciplina_unidade
    FOREIGN KEY (disciplina_id, unidade_id) REFERENCES disciplinas (id, unidade_id);

-- 5. Matrícula e atribuição só com vínculo ativo na unidade da turma -------------------------
-- Gatilho (não chave), porque o vínculo é da conta e a matrícula é do cadastro do aluno.
-- base:gatilhos:inicio
CREATE FUNCTION edufast_exige_vinculo() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    conta INTEGER;
    unidade INTEGER;
BEGIN
    IF TG_TABLE_NAME = 'alunos_turmas' THEN
        SELECT usuario_id INTO conta FROM alunos WHERE id = NEW.aluno_id;
        SELECT unidade_id INTO unidade FROM turmas WHERE id = NEW.turma_id;
    ELSIF TG_TABLE_NAME = 'professores_turmas' THEN
        SELECT usuario_id INTO conta FROM professores WHERE id = NEW.professor_id;
        SELECT unidade_id INTO unidade FROM turmas WHERE id = NEW.turma_id;
    ELSE  -- atribuicoes_docentes
        SELECT usuario_id INTO conta FROM professores WHERE id = NEW.professor_id;
        SELECT unidade_id INTO unidade FROM turmas_disciplinas WHERE id = NEW.turma_disciplina_id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM usuario_unidades v
                   WHERE v.usuario_id = conta AND v.unidade_id = unidade AND v.situacao <> 'revogado') THEN
        RAISE EXCEPTION 'pessoa sem vínculo com a unidade % da turma', unidade USING ERRCODE = '23503';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tg_alunos_turmas_vinculo BEFORE INSERT OR UPDATE ON alunos_turmas
    FOR EACH ROW EXECUTE FUNCTION edufast_exige_vinculo();
CREATE TRIGGER tg_professores_turmas_vinculo BEFORE INSERT OR UPDATE ON professores_turmas
    FOR EACH ROW EXECUTE FUNCTION edufast_exige_vinculo();
CREATE TRIGGER tg_atribuicoes_docentes_vinculo BEFORE INSERT OR UPDATE ON atribuicoes_docentes
    FOR EACH ROW EXECUTE FUNCTION edufast_exige_vinculo();
-- base:gatilhos:fim

-- 6. Subida do aluno do colégio para a faculdade ---------------------------------------------
-- motivo 'cpf_concluinte': a faculdade cadastrou o CPF de um aluno que concluiu o 3º ano;
-- 'manual': liberada pela secretaria do colégio ou pelo super admin (aluno sem CPF, por exemplo).
-- Uma subida por aluno e destino; a faculdade passa a LER o histórico e os documentos do colégio.
CREATE TABLE transferencias_unidade (
    id SERIAL PRIMARY KEY,
    aluno_id INTEGER NOT NULL REFERENCES alunos (id),
    origem_id INTEGER NOT NULL REFERENCES unidades (id),
    destino_id INTEGER NOT NULL REFERENCES unidades (id),
    autor_id INTEGER NOT NULL REFERENCES usuarios (id),
    motivo VARCHAR(20) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_transferencia_aluno_destino UNIQUE (aluno_id, destino_id),
    CONSTRAINT ck_transferencia_unidades_distintas CHECK (origem_id <> destino_id),
    CONSTRAINT ck_transferencia_motivo CHECK (motivo IN ('cpf_concluinte', 'manual'))
);
CREATE INDEX ix_transferencias_destino ON transferencias_unidade (destino_id);

COMMIT;

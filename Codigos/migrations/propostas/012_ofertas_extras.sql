-- PROPOSTA B4 (24/11/2026) — PENDENTE DE APROVAÇÃO DO USUÁRIO. NÃO EXECUTAR.
-- Ofertas extras (disciplinas/cursos que a turma inteira ou um aluno podem pegar).
-- Estudo: Documentos/planejamento/ESTUDO_ENSINO_SUPERIOR_B4_2026-11-24.md
-- PostgreSQL 17, transacional: uma falha desfaz tudo. Só acrescenta colunas com padrão e
-- tabelas novas; nenhum dado existente é alterado. Turmas existentes ficam 'regular'.
-- Renumerada de 009 para 010 em 25/11/2026 (a 009 passou a ser a de vídeos enviados, U2b).
-- Renumerada de 010 para 012 em 25/11/2026: 010 = unidades, 011 = Row-Level Security. Com as
-- unidades, a tabela escola_termos desta proposta sai (os rótulos ficam em unidades) e as ofertas
-- vivem dentro da unidade de nível superior; a revisão final ajusta isso.
-- Depois de aprovada, será movida para Codigos/migrations/ como 010_*.sql, gerada a partir
-- dos modelos e congelada em checksums.json, como as demais.
BEGIN;

ALTER TABLE turmas ADD COLUMN tipo VARCHAR(10) NOT NULL DEFAULT 'regular';
ALTER TABLE turmas ADD CONSTRAINT ck_turma_tipo CHECK (tipo IN ('regular', 'oferta'));
ALTER TABLE turmas ADD COLUMN periodo_letivo VARCHAR(20);
ALTER TABLE turmas ADD COLUMN inscricao_aberta BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE turmas ADD COLUMN vagas INTEGER;
ALTER TABLE turmas ADD CONSTRAINT ck_turma_vagas CHECK (vagas IS NULL OR vagas > 0);
ALTER TABLE turmas ADD CONSTRAINT ck_inscricao_so_oferta CHECK (inscricao_aberta = FALSE OR tipo = 'oferta');

-- Vazio = matrícula direta do aluno; preenchido = entrou pela turma inscrita na oferta.
ALTER TABLE alunos_turmas ADD COLUMN via_turma_id INTEGER REFERENCES turmas (id);

CREATE TABLE turmas_ofertas (
    id SERIAL PRIMARY KEY,
    turma_id INTEGER NOT NULL REFERENCES turmas (id),
    oferta_id INTEGER NOT NULL REFERENCES turmas (id),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_turma_oferta UNIQUE (turma_id, oferta_id),
    CONSTRAINT ck_turma_oferta_distintas CHECK (turma_id <> oferta_id)
);
CREATE INDEX ix_turmas_ofertas_oferta ON turmas_ofertas (oferta_id);

CREATE TABLE escola_termos (
    chave VARCHAR(30) PRIMARY KEY,
    rotulo VARCHAR(40) NOT NULL,
    CONSTRAINT ck_termo_chave CHECK (chave IN ('turma', 'turmas', 'oferta', 'ofertas', 'serie', 'periodo'))
);

COMMIT;

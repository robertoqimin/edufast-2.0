-- PENDENTE DE REVISAO HUMANA. Nunca executar automaticamente na inicializacao.
-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.
-- Gerado por migrations/gerar_postgresql.py a partir dos modelos; revisar antes de executar.
-- Aplicar com: psql -v ON_ERROR_STOP=1 -f <arquivo>

BEGIN;

ALTER TABLE usuarios
    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'ativo',
    ADD COLUMN revisor_materiais BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0;

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

-- Nao ha evidencia no legado que diferencie docente criado por admin de autoinscricao.
-- Revisar esta quarentena e uma allowlist comprovada ANTES de rodar; nao aprovar todos.
INSERT INTO solicitacoes_alteracoes (solicitante_id, tipo, payload, estado, recurso_pendente)
SELECT id, 'cadastro', json_build_object('usuario_id', id, 'papel_solicitado', 'professor')::text,
       'pendente', 'cadastro:' || id
FROM usuarios WHERE LOWER(tipo) = 'professor';
UPDATE usuarios SET estado = 'pendente', revisor_materiais = FALSE,
                    auth_version = auth_version + 1
WHERE LOWER(tipo) = 'professor';
-- Nao promove nenhum usuario a super_admin. Provisionar conta NOVA via CLI autorizada.

COMMIT;

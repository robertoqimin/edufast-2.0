-- PENDENTE DE REVISAO HUMANA. Nunca executar automaticamente na inicializacao.
-- MySQL 8.4; aplicar depois da migration 001 aprovada. DDL faz commits implicitos.
ALTER TABLE usuarios
    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'ativo',
    ADD COLUMN revisor_materiais BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0;
CREATE TABLE solicitacoes_alteracoes (
    id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
    solicitante_id INTEGER NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    payload TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendente',
    recurso_pendente VARCHAR(128) NULL,
    arquivo VARCHAR(255) NULL,
    decidido_por INTEGER NULL,
    justificativa VARCHAR(500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMP NULL,
    CONSTRAINT uq_recurso_pendente UNIQUE (recurso_pendente),
    FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
    FOREIGN KEY (decidido_por) REFERENCES usuarios(id)
);
-- Nao ha evidencia no legado que diferencie docente criado por admin de autoinscricao.
-- Revisar esta quarentena e uma allowlist comprovada ANTES de rodar; nao aprovar todos.
INSERT INTO solicitacoes_alteracoes (solicitante_id, tipo, payload, estado, recurso_pendente)
SELECT id, 'cadastro', JSON_OBJECT('usuario_id', id, 'papel_solicitado', 'professor'),
       'pendente', CONCAT('cadastro:', id)
FROM usuarios WHERE LOWER(tipo) = 'professor';
UPDATE usuarios SET estado = 'pendente', revisor_materiais = FALSE,
                    auth_version = auth_version + 1
WHERE LOWER(tipo) = 'professor';
-- Nao promove nenhum usuario a super_admin. Provisionar conta NOVA via CLI autorizada.

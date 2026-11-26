-- PROPOSTA 009 / U2b (25/11/2026) — APROVADA PELO USUÁRIO EM 25/11/2026.
-- Em banco real, aplicar só pelo aplicar_migracoes.py, depois de backup de banco, uploads e chave.
-- Vídeos enviados pelo professor (MP4 ou WebM, até 300 MiB), no Espaço da disciplina e nos cursos.
-- Resumo e riscos: Documentos/planejamento/PROPOSTA_U2B_VIDEOS_2026-11-25.md
-- PostgreSQL 17, transacional: uma falha desfaz tudo.
-- Só AMPLIA duas regras de verificação: PDF, PNG e JPEG continuam limitados a 5 MiB; arquivos
-- com tipo de vídeo passam a aceitar até 300 MiB (314572800 bytes). A regra nova contém a antiga
-- (antiga OU vídeo), então toda linha existente continua válida; nenhum dado é alterado.
-- As regras ganham nomes novos para o inventário (schema_inventory.py) detectar a proposta.
-- Entra no esquema base v9 e fica congelada em checksums.json, como as demais.
-- A proposta B4 (ofertas extras) passou a ser a 010.
BEGIN;

ALTER TABLE estudo_conteudos DROP CONSTRAINT ck_estudo_recurso;
ALTER TABLE estudo_conteudos ADD CONSTRAINT ck_estudo_recurso_video CHECK (
    (tipo = 'arquivo' AND arquivo IS NOT NULL AND mime IS NOT NULL AND tamanho IS NOT NULL AND link = ''
        AND (tamanho BETWEEN 1 AND 5242880
             OR (mime IN ('video/mp4', 'video/webm') AND tamanho BETWEEN 1 AND 314572800)))
    OR (tipo = 'link' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link <> '')
    OR (tipo = 'aviso' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link = ''));

ALTER TABLE curso_aula_recursos DROP CONSTRAINT ck_curso_recurso_tipo;
ALTER TABLE curso_aula_recursos ADD CONSTRAINT ck_curso_recurso_video CHECK (
    (tipo = 'arquivo' AND arquivo IS NOT NULL AND mime IS NOT NULL AND tamanho IS NOT NULL AND link = ''
        AND (tamanho BETWEEN 1 AND 5242880
             OR (mime IN ('video/mp4', 'video/webm') AND tamanho BETWEEN 1 AND 314572800)))
    OR (tipo = 'link' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link <> ''));

COMMIT;

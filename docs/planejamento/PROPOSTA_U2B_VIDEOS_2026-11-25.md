# U2b — Vídeos enviados pelo professor (proposta)

> **Aprovada pelo usuário em 25/11/2026** e implementada no mesmo dia: [relatório U2b](../testes/U2B_VIDEOS_2026-11-25.md). A migration está em `api/migrations/009_videos_enviados.sql`.

Data: 25/11/2026. Pedido do usuário: o professor pode subir vídeos em arquivo para o sistema.
Decisões do usuário:

- até **300 MB** por vídeo;
- vídeos **cifrados em blocos**;
- envio no **Espaço da disciplina e nos cursos**;
- fazer **agora, antes da U3**.

## O que precisa de aprovação: migration 009

Arquivo (após a aprovação): [`api/migrations/009_videos_enviados.sql`](../../api/migrations/009_videos_enviados.sql).

| Tabela | Regra hoje | Regra proposta |
| --- | --- | --- |
| `estudo_conteudos` | `ck_estudo_recurso`: arquivo de 1 B a 5 MiB | `ck_estudo_recurso_video`: a mesma regra **ou** `video/mp4`/`video/webm` de 1 B a 300 MiB |
| `curso_aula_recursos` | `ck_curso_recurso_tipo`: arquivo de 1 B a 5 MiB | `ck_curso_recurso_video`: a mesma regra **ou** vídeo de 1 B a 300 MiB |

- **Só amplia.** A nova regra é "antiga OU vídeo": toda linha existente continua válida e
  nenhum dado é alterado. Ela roda numa transação, então ou entra tudo, ou nada.
- **Nenhuma tabela ou coluna nova.**
  - O envio em partes fica em arquivos temporários cifrados na pasta de uploads e é apagado em
    24 h.
  - O vídeo final usa as mesmas colunas `arquivo`, `mime` e `tamanho`.
- **Numeração.** A proposta B4 (ofertas extras, próximo ciclo) hoje se chama `009` e passa a
  `010`. O conteúdo dela não muda.
- **Ajuste da ferramenta de migrations.** As regras ganham nomes novos e o inventário
  (`schema_inventory.py`) passa a reconhecer `ADD CONSTRAINT`. Assim a 009 é detectada como
  aplicada ou ausente, como as demais.
- **Esquema base.** O esquema base vira `esquema_v9.sql` e os checksums são registrados. A base
  v8 é mantida.

## Como vai funcionar

- **Envio em partes de 8 MiB.** O servidor aceita no máximo 16 MB por envio (Flask e Nginx),
  e não é preciso mudar isso. O navegador mostra uma barra de progresso. Se a conexão cair, o
  envio retoma da última parte recebida.
  - Só MP4 e WebM, conferidos pelo conteúdo do arquivo, não pela extensão.
  - O professor pode ter no máximo 3 envios em andamento.
  - O envio é recusado se o disco não tiver espaço para o vídeo e mais uma folga.
- **Cifra em blocos.** Cada bloco de 1 MiB é cifrado com AES-256-GCM. A chave é derivada da
  `DATA_ENCRYPTION_KEY`, a mesma usada hoje, por HKDF.
  - Cada bloco é autenticado com o seu número e o tamanho total. Trocar, cortar ou reordenar
    blocos é detectado.
  - Para assistir e avançar no vídeo, o servidor decifra só os blocos pedidos (pedidos
    `Range`), sem carregar o arquivo inteiro na memória.
  - PDFs e imagens continuam como hoje.
- **Quem envia e quem vê não muda.**
  - O material do Espaço da disciplina continua como rascunho e só chega ao aluno depois da
    aprovação da secretaria.
  - Nos cursos, o vídeo entra na aula em edição e segue a publicação do curso.
  - Acesso, auditoria e "Baixar uma cópia" (opcional) seguem as regras atuais.
- **Aluno.** O vídeo aparece já no player da página, como o YouTube.
  - Na aula do curso com vídeo enviado, o vídeo fica no topo da aula.
  - Assistir conta como visto, como os demais materiais.
- **Demonstração.** Um vídeo curto em WebM, gerado no próprio Edge a partir de uma animação
  (sem ffmpeg e sem conteúdo de terceiros), enviado pela professora pelas rotas reais.

## Riscos e custos

- **Disco e backup:** cada vídeo pode ocupar até 300 MB. O backup de uploads cresce na mesma
  proporção. Não há cota por escola nesta etapa; fica sugerida para depois.
- **Formato:** não há conversão de vídeo. O professor precisa enviar MP4 (H.264/AAC) ou WebM,
  que o Edge, o Chrome e o Firefox tocam. Outros codecs podem não tocar em todos os
  navegadores; a tela avisa isso.
- **Aplicar em banco real:** pelo procedimento do `aplicar_migracoes.py`, com backup de banco,
  uploads e chave antes.

## Execução depois da aprovação

1. Mover a 009 para `api/migrations/`, renumerar a B4 para 010, ajustar o inventário e o
   gerador, gerar a base v9 e os checksums.
2. Cifra em blocos e envio em partes, com testes de adulteração, corte, retomada,
   concorrência e `Range`.
3. Telas: formulário do Espaço da disciplina, editor da aula do curso, player do aluno.
4. Regressão em SQLite e PostgreSQL, incluindo o caminho legado + 001–009 contra a base v9.
   Também a auditoria de acessibilidade, a jornada no Edge e o roteiro lento.
5. Relatório, commit e envio ao GitHub.

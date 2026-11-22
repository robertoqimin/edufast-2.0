# Migração de concorrência — revisão pendente

## Inventário antes de qualquer revisão

Para saber quais propostas já estão presentes num banco, sem alterá-lo:
`EDUFAST_REVIEW_DB_URL=... python schema_inventory.py` em `Códigos/` (banco central:
`--central`). Mostra cada migration como aplicada, parcial ou ausente e alerta sobre
estado parcial ou registro divergente. Detalhes: `Documentos/testes/INVENTARIO_ESQUEMA_2026-11-22.md`.

## Cursos MS04 — 007 pendente de revisão

`007_cursos_backend_ms04.sql` foi compilado offline. Propõe tornar `video_id`
opcional e criar quatro extensões: versões por curso, corpos/tipo de aula,
retomada por aluno/oferta e apoios privados. Não altera IDs, títulos ou conclusões
anteriores. O backend usa `/api`; o frontend dos novos formatos será integrado
depois. Nenhum SQL foi executado em banco persistente nesta implementação.

A API exige as quatro tabelas e a coluna com nulabilidade compatível; caso
contrário responde 503. O startup não aplica DDL. Cursos legados sem versão
continuam em seus contratos; a primeira gravação/duplicação pela nova API adota
edição versionada e bloqueia gravação pelos caminhos antigos daquele curso.

Revisar SQL, tipos/chaves/dados anteriores, backup consistente de banco/uploads
e `DATA_ENCRYPTION_KEY`; ensaiar atualização e recuperação em ambiente isolado.
Incluir `uploads/materiais_curso` no backup. Objetos binários são imutáveis e podem
ter referências em mais de uma edição; não limpar arquivos por nome/idade sem
conferir essas referências. Não repetir DDL após falha parcial sem inspeção.
Código anterior não suporta texto sem vídeo, exigindo revisão antes de rollback
após ativação. Contratos e testes: `Documentos/testes/API_CURSOS_MS04_2026-11-20.md`.

## Abas docentes — 006 pendente de revisão

`006_abas_disciplina.sql` propõe três tabelas opcionais: `estudo_secoes`,
`estudo_conteudo_secao` e `estudo_secao_auditoria`. Depende da proposta 005 e das
tabelas de usuários/ofertas. Foi compilado offline, sem executar migrations.
Não altera tabelas do MS02: conteúdos antigos permanecem nas abas padrão.

O autor autorizado organiza suas abas; administração pode intervir. A publicação
dos conteúdos continua passando pela aprovação existente. Arquivar uma aba revoga
leitura e download pelo aluno, preservando associações, conteúdos e arquivos.
Não há exclusão nem restauração automática de abas arquivadas nesta versão.

Revisar 005/006, destino, chaves estrangeiras e compatibilidade MySQL. Preparar
backup consistente de banco/uploads/chave e ensaiar recuperação antes de ativar.
Nenhuma execução em banco persistente foi autorizada por esta implementação.
DDL MySQL pode ficar parcial: inspecionar o estado antes de qualquer repetição.
Sem as três tabelas, MS02 continua disponível; esquema parcial bloqueia os acessos
de conteúdo para não contornar a restrição de abas arquivadas. Startup não cria
tabelas. Rollback preserva tabelas/arquivos; código MS02 anterior ao MS03 não deve
ser usado após ativação sem revisão, pois não conhece a restrição de arquivamento.
Evidências: `Documentos/testes/ABAS_DISCIPLINA_2026-11-19.md`.

## Espaço da disciplina — 005 pendente de revisão

`005_espaco_disciplina.sql` propõe `estudo_conteudos` e `estudo_auditoria` para
avisos, links e arquivos de estudo por oferta turma/disciplina. Não foi executado
em bancos persistentes. O SQL foi compilado offline a partir dos modelos e não
altera matrículas, permissões, documentos pessoais ou dados históricos.

O professor prepara rascunhos; publicação passa por solicitação administrativa.
Materiais publicados são preservados, e arquivar revoga a leitura pelo aluno sem
excluir o histórico. Aluno precisa de vínculo com a turma **e** a disciplina.
Turmas sob gestão explícita exigem atribuição docente ativa, sem herdar combinações
dos pares legados. Os arquivos ficam cifrados em `uploads/materiais_estudo`.

Revisar SQL, destino e esquema anterior; conferir `usuarios`,
`turmas_disciplinas`, idempotência e aprovações existentes. Fazer backup consistente
de banco/uploads e preservar `DATA_ENCRYPTION_KEY`. Ensaiar recuperação antes da
ativação. Não reexecutar o SQL após falha parcial sem inspecionar o estado: DDL
MySQL tem commits implícitos. Não há `IF NOT EXISTS`, conversão ou limpeza de dados.

Sem as tabelas opcionais, o módulo responde 503 e a aplicação mantém seus acessos
existentes; o startup não as cria. Tabelas opcionais já presentes continuam sendo
verificadas na validação de produção. Não iniciar contra esquema parcial incompatível.
Após revisão do usuário e ativação explícita por instalação, conferir rascunho,
publicação, recusa de outro aluno e download. Reverter código não deve apagar as
tabelas nem arquivos. Relatório: `Documentos/testes/ESPACO_DISCIPLINA_2026-11-16.md`.

## Frequência e atestados — 004 pendente de revisão

Atualização de comportamento em 16/11: novas chamadas são confirmadas diretamente
pelo professor autorizado, sem mudança de esquema. O estado técnico `aprovada` é
preservado; chamadas antigas pendentes não são convertidas. A análise de atestados
continua administrativa. Consulte `Documentos/testes/CHAMADA_DIRETA_2026-11-16.md`.
A descrição de aprovação abaixo registra a proposta original; o SQL continua
pendente de revisão e não deve ser executado automaticamente.

`004_frequencia.sql` propõe quatro tabelas: chamadas versionadas, marcações por
aluno, atestados e auditoria. Foi gerado pelos modelos, sem conectar ou executar
SQL nos bancos das escolas. Não cria presença histórica nem altera contas,
permissões, notas ou vínculos. As chamadas docentes aguardam decisão de admin.
Atestado aceito apenas justifica a falta; não abona nem conta como presença.

Antes de aplicar: revisar SQL, conferir esquema/tipos das chaves referenciadas,
verificar ausência de tabelas homônimas, salvar banco/uploads e preservar
`DATA_ENCRYPTION_KEY`. Os anexos e motivos ficam cifrados. Rever acesso e retenção
de documentos com a escola. Não executar às cegas ou reexecutar após falha parcial:
DDL MySQL tem commits implícitos. A aplicação não executa esta migration ao iniciar.

O módulo responde 503 se não encontrar as quatro tabelas, mantendo os fluxos
existentes. Depois de revisão e autorização explícita, aplicar separadamente por
instalação e validar permissões, chamada/aprovação, relatório, atestado e download.
Rollback de aplicação preserva as tabelas; não executar DROP automaticamente.
Guia e evidências: `Documentos/testes/FREQUENCIA_2026-11-12.md`.

## Restauração funcional — 003 pendente de revisão

`003_restauracao_educafast.sql` propõe 24 tabelas novas para identidade institucional,
calendário, políticas, cursos, diário/boletim e privacidade. Não altera nem remove
as tabelas existentes e não deduz vínculos acadêmicos históricos. Não foi executada
em banco existente. Revisar a lista e eventuais tabelas homônimas antes de aplicar:
o SQL não deve ser reexecutado às cegas nem substituir tabelas de outra versão.

O iniciador restaurado usa um volume novo e cria somente esquema vazio via metadata,
em projeto separado; isso não migra o volume anterior. Para bancos existentes,
revisar 001/002/003, fazer backup de banco/uploads e guardar DATA_ENCRYPTION_KEY.
O modelo de privacidade cifra novos textos; essa chave não deve ser derivada da
senha pública de demonstração nem rotacionada sem plano de recifragem.

## Aprovações e permissões — 002 também pendente

`002_aprovacoes_e_permissoes.sql` adiciona estado da conta, permissão limitada de
revisor, versão de autenticação e solicitações auditáveis. Não foi executada no banco
existente. Os testes criam apenas esquemas novos e descartáveis via metadata.

O legado não prova quais professores foram admitidos por administrador: a proposta
de SQL coloca professores existentes em revisão. Antes de executar, revisar com o
responsável a lista de contas e evidências de aprovação. Não promover automaticamente,
não apagar usuários e não conceder superadmin por compatibilidade. Fazer backup e
ensaiar restauração de banco e uploads; DDL MySQL não oferece rollback transacional.

Superadmin novo: `flask --app 'app:create_app()' create-admin --super-admin`.
Só um operador com acesso ao servidor pode executar esse provisionamento; não há
autoinscrição de admin ou superadmin. Admin existente continua com seu papel.

`001_concorrencia.sql` é uma proposta para revisão, não executada no banco existente.
O aplicativo deixou de executar `CREATE/ALTER TABLE` ao iniciar. Não implantar esta
versão sobre o esquema antigo antes de aprovar e aplicar a mudança explicitamente.

1. Definir `EDUFAST_REVIEW_DB_URL` e executar `python schema_preflight.py` em `Códigos`.
   O relatório consulta metadados e conta grupos duplicados, sem expor CPF ou e-mail.
2. Conferir todas as constraints declaradas, não apenas as novas. `create_all` antigo
   não garantia sua presença em tabelas legadas.
3. Se houver duplicados, interromper a criação da constraint. Preparar uma tabela de
   correspondência entre IDs, revisar com o proprietário e planejar remapeamento das
   referências, preservação de histórico e arquivamento. Não apagar automaticamente.
4. Revisar o SQL e um backup recuperável de banco e arquivos. Ensaiar em cópia sintética.
5. Parar gravações durante a migração aprovada. DDL MySQL faz commits implícitos;
   em falha parcial, inspecionar o esquema antes de retomar, sem reexecutar às cegas.
6. Aplicar apenas após aprovação humana, conferir preflight novamente e fazer smoke.

As versões existentes começam em 1. Formulários antigos sem versão/chave recebem 428;
recarregar a página produz os campos necessários. Integrações precisam enviar os
novos parâmetros. Não remover registros de idempotência enquanto houver possibilidade
de repetição: isso permitiria executar novamente uma chave já processada.

Instalação vazia: após revisão, o esquema pode ser criado explicitamente com
`python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(engine)"`.
Esse comando cria tabelas novas e não atualiza um esquema existente.

Rollback: manter as colunas e a tabela adicionadas ao reverter o aplicativo; não
executar DROP automaticamente. Uma versão anterior volta a permitir as corridas.
Para desfazer dados, restaurar banco e uploads de um ponto consistente, considerando
as gravações posteriores ao backup com o responsável pela instalação.

# Migração de concorrência — revisão pendente

## Frequência e atestados — 004 pendente de revisão

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

# Migração de concorrência — revisão pendente

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

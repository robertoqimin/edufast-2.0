# Integração e migração

[Início da revisão](README.md)

Os testes executam SQL e transações reais em SQLite e MySQL descartáveis. Os casos concorrentes usam MySQL; SQLite em memória não representa a concorrência do servidor de produção.

## Cenários de integração

| ID | Preparação / ação | Resultado exigido |
| --- | --- | --- |
| INT-001 | Migrar banco vazio | Todas as tabelas e campos do contrato institucional disponíveis |
| INT-002 | Migrar legado sem indicar escola proprietária | Erro `legacy_owner_required`, sem alterar tabelas ou registros |
| INT-003 | Migrar legado indicando instituição | Preservar usuários, hashes, matrícula, nota e referência de arquivo; dados associados à instituição correta |
| INT-004 | Aplicar a migração novamente | Mesmo estado dos dados, sem duplicações |
| INT-005 | Executar `dry_run` no legado | Relatório de mudanças pendentes, sem mudar esquema ou dados |
| INT-006 | Inserir matrícula com aluno de outra escola diretamente no banco | Restrição de integridade rejeita a gravação |
| INT-007 | Inserir segunda matrícula ativa para o mesmo vínculo | Banco rejeita duplicidade |
| INT-008 | Mesma identidade com cadastro de aluno em duas escolas | Dois perfis locais válidos, sem unicidade global indevida |
| INT-009 | Inserir atribuição com professor de outra escola diretamente no banco | Restrição de integridade rejeita a gravação |
| INT-010 | Registrar notas da mesma disciplina em períodos/ofertas diferentes | Duas notas persistem, sem sobrescrita pelo contrato antigo aluno/disciplina |

Interface futura proposta: `app.migrations.upgrade(engine, legacy_school=None, dry_run=False)`. Deve executar migrações versionadas, não um segundo esquema criado apenas para os testes. Falhas de migração usam `MigrationError.code`. A escolha de biblioteca de migração fica para a implementação.

O legado é reconstruído a partir de snapshots SQL de SQLite/MySQL capturados do código do commit `1f034fa`. Os arquivos estão em [legacy](../../../.github/cicd/next/legacy). A massa inclui uma conta administrativa, aluno, professor, turma, disciplina, nota e referência de documento. Não deriva dos modelos novos, evitando que uma mudança futura altere silenciosamente o cenário legado.

Vínculos legados ambíguos não podem conceder novas atribuições docentes automaticamente. A migração deve registrar pendências de revisão quando não houver uma relação inequívoca. O teste de preservação de nota não autoriza inferir acesso docente futuro a partir de dados históricos.

## Concorrência HTTP no MySQL

| ID | Execução | Resultado |
| --- | --- | --- |
| API-078 | Duas matrículas simultâneas para o mesmo vínculo | Uma resposta 201 e uma 409; exatamente um registro |
| API-079 | Dois aceites simultâneos do mesmo convite | Uma resposta 200 e uma 409; exatamente uma participação |

Os clientes começam por uma barreira de sincronização e consultam o mesmo banco real. Não são duas chamadas sequenciais nem duas respostas simuladas.

Esses dois casos não são descobertos no perfil SQLite. O manifesto informa o banco de cada cenário; isso não é `skip` convertido em aprovação. A execução MySQL permanece obrigatória para validar essa parte do contrato.

## Recuperação e arquivos

O CI existente já exercita dump/restauração MySQL e backup/restauração de uploads descartáveis. Estes testes novos acrescentam a migração de conteúdo e as referências aos arquivos. O ensaio de restauração em um servidor real continua necessário antes do uso operacional.

## Limites e evolução

SQLite precisa ter verificação de chaves estrangeiras habilitada durante os ensaios de integridade. MySQL é a referência final de concorrência e DDL. A implementação não pode contornar testes de integridade desligando restrições.

Ao descobrir uma estrutura legada adicional ou ambígua, acrescentar uma fixture e o cenário correspondente. O snapshot atual representa o esquema existente, mas a massa inicial não cobre todas as combinações possíveis de uma instalação em uso.

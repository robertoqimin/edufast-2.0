# A5 — Revisão das migrations com o usuário

Data: 23/11/2026. Branch `feature/melhoria-dezembro`, commit «fix: corrige achados de seguranca S1-S7».
Etapa A5 do [plano de melhoria](PLANO_MELHORIA_2026-11-22.md).

**Aprovar não executa nada.** Aprovar um arquivo significa: o conteúdo está correto e pode ser
usado pelo aplicador revisado (`aplicar_migracoes.py`) quando houver um banco de destino. Toda
aplicação real continua exigindo, antes, backup de banco, uploads e chave, e o plano mostrado
pelo aplicador.

## Contexto

- **Não há banco real esperando estas migrations.** Os ambientes PostgreSQL existentes (manual
  e escolas Teste 01/02) nasceram pela base v8. Os bancos antigos eram MySQL, com dados fictícios.
- **Cliente novo** recebe o **esquema base v8** (um arquivo). **Banco antigo** (por exemplo, dados
  importados de uma instalação anterior) usa a sequência 001–008.
- Todos os arquivos são **PostgreSQL 17, transacionais** (uma falha desfaz o arquivo inteiro) e
  **congelados** em `api/migrations/checksums.json`: depois de aprovados, não mudam.
- **Volta atrás** é a mesma para todos, e foi ensaiada: recriar o banco vazio e restaurar o
  backup feito antes (guia em `api/migrations/README.md`). Não há scripts de "desfazer"
  por migration: restaurar o backup é mais seguro que desfazer estrutura com dados novos.

Evidências comuns: regressão de 304 testes em PostgreSQL; teste que aplica 001–008 sobre o
legado e compara com os modelos; teste que exige base idêntica à sequência; ensaio legado com
dados → backup → 001–008 → aplicação funcionando → volta atrás
([relatório da A4](../testes/APLICADOR_ENSAIO_2026-11-22.md)).

## Fichas

### Base v8 — `base/esquema_v8.sql` (checksum `223c64b6e11b…`)

| | |
| --- | --- |
| Para quê | Criar o banco completo de uma escola **nova** de uma vez |
| Cria | 54 tabelas, 7 índices; registra as versões 1–8 como `aplicada` por este arquivo |
| Dados | Nenhum dado escolar; só o registro de versões |
| Exige | Banco **vazio** (o aplicador recusa qualquer outro) |
| Riscos | Baixos: estrutura idêntica à sequência 001–008 (verificado tabela por tabela) |
| Já em uso | Iniciador local e escolas Teste 01/02 |

### 001 — concorrência (`146c191bf476…`)

| | |
| --- | --- |
| Para quê | Impedir que dois envios simultâneos sobrescrevam um ao outro; impedir envio repetido |
| Cria / altera | Tabela `idempotencias`; coluna `versao` em `alunos`, `professores` e `notas` (valor inicial 1) |
| Dados | Nenhum dado é alterado além do valor inicial das colunas novas |
| Riscos | Baixos. Restrições únicas antigas ausentes no banco legado exigem conferência pelo preflight antes |

### 002 — aprovações e permissões (`a9de71b0884b…`) — **exige decisão**

| | |
| --- | --- |
| Para quê | Estado da conta (ativo/pendente), revisor de materiais, revogação de sessões, solicitações auditáveis |
| Cria / altera | Tabela `solicitacoes_alteracoes`; colunas `estado`, `revisor_materiais` e `auth_version` em `usuarios` |
| **Dados** | **Coloca todos os professores existentes em quarentena** (estado `pendente`) e cria uma solicitação de cadastro para cada um. O banco antigo não registra se o professor foi admitido por um administrador ou se se cadastrou sozinho |
| Efeito prático | Professores não entram até um administrador aprovar (o ensaio confirmou: 403 até a aprovação) |
| Riscos | Médio para a operação: no primeiro dia após a atualização, professores ficam sem acesso até a aprovação |
| Decisão pedida | Manter a quarentena geral, **ou** fornecer uma lista de professores confiáveis a manter ativos (exige ajuste revisado, com a lista, antes de aplicar) |

### 003 — restauração funcional (`7885b09eb995…`)

| | |
| --- | --- |
| Para quê | Identidade da escola, calendário, políticas, períodos, avaliações, notas por período, cursos, privacidade, limite de login |
| Cria | 24 tabelas novas, 2 índices (inclui `limites_login`, usada pelo limitador de login desde 23/11, e `educafast_migracoes`) |
| Dados | Nenhum dado existente é alterado; não deduz vínculos acadêmicos antigos |
| Riscos | Baixos; conferir ausência de tabelas homônimas no banco alvo (o plano do aplicador acusa) |

### 004 — frequência e atestados (`8d5e80045484…`)

| | |
| --- | --- |
| Cria | 4 tabelas (`frequencia_chamadas`, `frequencia_presencas`, `frequencia_atestados`, `frequencia_auditoria`), 1 índice |
| Dados | Nenhum; não cria presença histórica. Anexos e motivos de atestado ficam cifrados (precisam da `DATA_ENCRYPTION_KEY`) |
| Riscos | Baixos; guardar a chave de criptografia junto do backup |

### 005 — espaço da disciplina (`0ff993f8a0e3…`)

| | |
| --- | --- |
| Cria | 2 tabelas (`estudo_conteudos`, `estudo_auditoria`), 1 índice |
| Dados | Nenhum; materiais futuros ficam cifrados em `uploads/materiais_estudo` |
| Riscos | Baixos |

### 006 — abas docentes (`639e1bb3a412…`)

| | |
| --- | --- |
| Cria | 3 tabelas (`estudo_secoes`, `estudo_conteudo_secao`, `estudo_secao_auditoria`), 2 índices |
| Exige | 005 |
| Riscos | Baixos |

### 007 — cursos modulares MS04 (`5ae00b3cf9b0…`)

| | |
| --- | --- |
| Cria / altera | 4 tabelas (versões, conteúdo de aula, retomada, recursos), 1 índice; `curso_aulas.video_id` passa a aceitar vazio (aulas só de texto) |
| Dados | Nenhum; IDs, títulos e conclusões anteriores preservados |
| Riscos | Baixos. Depois de aplicada, uma release anterior não entende aula sem vídeo: não voltar a release sem restaurar o backup |

### 008 — registro de versões (`3ae39cc85f7f…`)

| | |
| --- | --- |
| Cria / altera | Colunas `descricao`, `arquivo`, `checksum`, `aplicada_em` e `origem` em `educafast_migracoes` |
| Dados | Registra como `detectada` cada proposta 001–007 com estrutura completa; registra a si mesma |
| Efeito | A aplicação passa a recusar iniciar com banco mais novo que o código ou arquivo divergente |
| Riscos | Baixos |

### Painel central — `control_plane/migrations/001_central.sql`

| | |
| --- | --- |
| Para quê | Banco **exclusivo** do painel Supremo (proprietário da plataforma) |
| Cria | 5 tabelas: `platform_owner`, `platform_schools`, `platform_people`, `platform_movements`, `platform_audit` |
| Exige | Banco central **vazio**; nunca aplicar em banco de escola |
| Riscos | Baixos; o banco central guarda nomes, e-mails e lançamentos financeiros: backup protegido |

## Decisão transversal — e-mails com maiúsculas

O login compara e-mails em minúsculas. Um banco antigo pode ter contas como `Ana@Escola.com`,
que deixariam de entrar (o ensaio da A4 confirmou). Hoje nenhum banco real tem isso. Opções:
nova proposta 009 que normaliza os e-mails (alteração de dados; recusa se houver duas contas que
só diferem por maiúsculas), **ou** tratar manualmente quando houver importação (o aplicador já avisa).

## Registro das decisões

Decisões do usuário em 23/11/2026:

| Arquivo | Decisão | Data |
| --- | --- | --- |
| Base v8 | **Aprovada** | 23/11/2026 |
| 001 | **Aprovada** | 23/11/2026 |
| 002 (quarentena) | **Aprovada com a quarentena geral**: todo professor de banco antigo fica pendente até aprovação administrativa. Sem lista de exceções | 23/11/2026 |
| 003 | **Aprovada** | 23/11/2026 |
| 004 | **Aprovada** | 23/11/2026 |
| 005 | **Aprovada** | 23/11/2026 |
| 006 | **Aprovada** | 23/11/2026 |
| 007 | **Aprovada** | 23/11/2026 |
| 008 | **Aprovada** | 23/11/2026 |
| Painel central 001 | **Aprovada** | 23/11/2026 |
| E-mails com maiúsculas | **Tratar na importação**: sem migration nova agora; o aplicador avisa, e a normalização é decidida quando houver dados reais | 23/11/2026 |

**O que a aprovação permite:** usar estes arquivos, pelo `aplicar_migracoes.py`, em bancos de
destino reais (cliente novo pela base; banco antigo pela sequência), **sempre** com backup de
banco, uploads e chave antes, e com o plano mostrado e conferido. Nenhuma aplicação foi feita.

**Por que os arquivos ainda dizem "PENDENTE DE REVISÃO" no topo:** estão congelados por
checksum. Editar até um comentário mudaria o hash e faria a aplicação recusar bancos que já os
aplicaram. A aprovação vale por este registro.

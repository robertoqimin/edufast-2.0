# A3 — Esquema base para banco novo

Data: 22/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«feat: propoe migration 008 de registro de versoes (A2)».
Etapa A3 do [plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).
**Estado: pronto para revisão. Nenhum banco persistente de cliente foi alterado.**

## Problema

Não havia um SQL revisável para criar o banco de uma escola do zero. As propostas 001–008
só funcionam sobre o esquema legado (usuários, alunos, turmas, notas…), que não existe em
nenhum arquivo SQL: nascia do `create_all` do SQLAlchemy, usado pelo iniciador e pelas demos.

## O que foi feito

| Item | Descrição |
| --- | --- |
| `api/migrations/base/esquema_v8.sql` | Cria o banco completo (54 tabelas, 7 índices) numa transação e registra as versões 1–8 em `educafast_migracoes` com origem `aplicada` e `arquivo = base/esquema_v8.sql`. Só para banco vazio |
| `api/migrations/gerar_postgresql.py` | Gera 001–008 e a base **numa passada**, a partir do conteúdo recém-gerado (antes, a 008 era calculada a partir dos arquivos gravados e podia exigir duas execuções) |
| `api/schema_base.py` | `criar_esquema_base(engine)`: executa a base no PostgreSQL; no SQLite (só testes/demos em memória) usa `create_all` com o mesmo registro. Recusa banco com qualquer tabela. Também é a fonte única do nome do arquivo base e das linhas de registro |
| Executor de arquivos SQL | `executar_arquivo_postgresql()` passou a existir num só lugar e os testes o reutilizam. Ele devolve a conexão ao pool sem autocommit e sem `search_path` alterado, inclusive em erro (ponto onde houve defeito na troca para PostgreSQL) |
| Iniciador local | Banco novo criado pela base em vez de `create_all` |
| Escolas Teste 01/02 | Idem. O registro de versões não conta mais como "dados da escola" ao retomar uma preparação interrompida |
| Documentação | Guia de migrations (seção "Banco novo"), guia de execução, README, plano |

Decisões do usuário: registro com `arquivo = base/esquema_v8.sql` (diz por qual caminho o
banco nasceu); iniciador e escolas de teste já usando a base nesta etapa.

**Bases antigas nunca são apagadas.** Quando surgir a 009, o gerador cria `esquema_v9.sql`
e mantém a v8: bancos criados por ela continuam apontando para o arquivo no registro.

## Revisão de código

Feita depois da primeira bateria, com três correções aplicadas e retestadas:

1. Gerador em uma passada (ver tabela acima).
2. Executor de arquivos SQL unificado.
3. Regra de não apagar bases antigas documentada e coberta por teste.

## Validação

**Testes novos ou ampliados:**

| Arquivo | Casos | O que garante |
| --- | --- | --- |
| `test_migrations_postgresql.py` | +2 | **Equivalência em PostgreSQL real:** banco legado + 001–008 em sequência e banco criado pela base têm estrutura idêntica (tabelas, colunas, tipos, nulidade, PK, únicas, índices, FKs, CHECKs) e registro esperado. A base aplicada em banco vazio passa no inventário sem alertas, é aceita pela inicialização de produção, recusa segunda execução e não deixa a conexão alterada |
| `test_schema_base.py` | 8 | Arquivo base corresponde à última proposta; bases antigas mantidas; registro cobre todas as versões; SQL cria todas as tabelas; SQLite cria esquema completo e registrado; banco com tabela é recusado sem alteração; produção aceita banco criado pela base; escola de teste retoma preparação interrompida |
| `test_registro_migracoes.py` | ajustado | Sincronia agora cobre 001–008 **e a base** |
| `test_concurrency.py` | corrigido | Ver abaixo |

**Teste de concorrência intermitente corrigido.** Na primeira bateria, o `ci.py` falhou em
`test_concurrent_unique_registrations_and_links`. Causa: o teste criava a disciplina `D2`
com dois pedidos simultâneos e depois usava o id **2** fixo. Numa criação concorrente, o
pedido perdedor consome um valor da sequência, e o vencedor pode ficar com id 3; os dois
vínculos recebiam "disciplina não encontrada". Não é defeito da aplicação (sequências têm
lacunas também no MySQL). O teste passou a buscar os ids reais por código (`D2`, `T2`). Após
a correção: 15 de 15 execuções repetidas aprovadas, e a suíte de concorrência inteira (28).

**Bateria completa no código final** (`.ci-results/a3-esquema-base-2026-11-22/`):

| Etapa | Resultado |
| --- | --- |
| Regressão | SQLite 276 ✓ (35 ign.), **PostgreSQL 276 ✓ (2 ign., os mesmos de sempre)**, HTTP 117 ✓ |
| `ci.py` | Imagem de produção, deploy 11 ✓, SQLite 276 ✓, PostgreSQL 276 ✓, HTTPS/login, backup/restauração ✓ |
| Piloto de duas escolas | ✓ |
| API de frequência | SQLite, PostgreSQL e HTTP 117 ✓ |
| Painel central | 18/18 ✓ |
| Postman | SQLite e PostgreSQL: 57 requisições, 65 asserções, 0 falhas |

**Execução real, com Docker de verdade (não simulado):**

| Ambiente | Verificado |
| --- | --- |
| `.\iniciar-educafast.ps1 -SemNavegador` (novo `edufast-manual-postgres`) | Banco criado pela base: 54 tabelas, versões 1–8 `aplicada` por `base/esquema_v8.sql`; inventário com `versao_estrutural` 8 e nenhum alerta; `/healthz` ok; login 200 com `admin@teste.local` e com `Admin@Teste.LOCAL`; senha errada 401. Parado depois, com os dados preservados |
| `node infra/demo.cjs start` (Teste 01 e 02) | Cada banco com 8 versões registradas pela base, 20 alunos e 5 professores; login 200 nas duas escolas; conta da escola 01 recusada na escola 02 (404); volumes MySQL antigos intactos. Paradas depois, com os dados preservados |

Também aprovados: unitários (inclusive sem pacotes externos), teste do iniciador com Docker
simulado, sincronia de 001–008 e base com o gerador.

## Limites

- A base e as propostas continuam **pendentes de revisão** para uso em cliente real.
- Os ambientes locais criados nesta validação (`edufast-manual-postgres` e os volumes
  `postgres-teste01/02`) ficaram preservados, com dados fictícios.
- O checksum continua vazio no registro; será gravado pelo aplicador da A4.

## Próxima etapa

A4 do plano.

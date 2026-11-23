# A4 — Aplicador revisado e ensaio de atualização

Data: 22/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«feat: adiciona esquema base para banco novo (A3)».
Etapa A4 do [plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).
**Nenhum banco persistente de cliente foi alterado.**

## Redefinição combinada com o usuário

O plano original previa aplicar 002–008 numa cópia dos bancos Teste 01/02 e do central.
Depois da troca para PostgreSQL, esses bancos nascem na versão 8 pelo esquema base: não há o
que atualizar neles. A A4 passou a ser:

1. o **aplicador revisado**, peça que A2 e A3 deixaram pendente (grava o checksum);
2. um **ensaio completo de atualização**: banco legado com dados → backup → 001–008 →
   aplicação funcionando → volta atrás pela restauração.

## Aplicador — `Codigos/aplicar_migracoes.py`

| Comportamento | Detalhe |
| --- | --- |
| Padrão seguro | Sem opções, só mostra o plano. Aplica apenas com `--aplicar --confirmar <nome exato do banco>`. Banco só por `EDUFAST_APPLY_DB_URL`, nunca pelo `.env` |
| Banco vazio | Cria pelo esquema base, gravando registro e checksum na mesma transação |
| Banco existente | Aplica em ordem as propostas que faltam; `--ate N` permite atualizar em etapas |
| Atomicidade | Cada proposta roda numa transação junto com o registro da versão e o SHA-256 do arquivo. Uma falha desfaz só aquela proposta |
| Recusas | Proposta parcial, ordem quebrada, registro incompatível com a release, banco não PostgreSQL, outra aplicação simultânea (trava consultiva no banco) e plano desatualizado |
| Avisos | E-mails legados com maiúsculas e professores que a 002 coloca em quarentena |
| Registro | Aplicadas pela ferramenta: `aplicada` com checksum. Aplicadas antes da 008 existir: `detectada` (a 008 as encontra) |

O esquema base criado por `criar_esquema_base` (iniciador e escolas de teste) também passou
a gravar o checksum. As funções comuns ficam em `schema_base.py`: corpo transacional do
arquivo e literais do registro, validados por formato, sem entrada livre no SQL.

## Arquivos congelados

Com checksum gravado nos bancos, alterar uma proposta já aplicada faria a inicialização
recusar esses bancos. Por isso:

- o gerador **só cria arquivos novos** e nunca reescreve 001–008 nem bases existentes;
- `Codigos/migrations/checksums.json` registra o SHA-256 de cada arquivo, e um teste falha se
  algum mudar ou se aparecer arquivo fora do manifesto;
- outro teste compara a base mais recente com a gerada dos modelos atuais: um modelo alterado
  sem nova proposta é apontado antes de chegar a qualquer banco.

## Ensaio de atualização — `.github/cicd/run_ensaio_atualizacao.py`

Containers e volumes descartáveis, papel da aplicação sem superusuário, imagem aprovada pelo
CI. Resultado na bateria final (imagem `edufast-ci-…:tested`, cerca de 37 s ao todo):

| Passo | Resultado |
| --- | --- |
| Banco legado com dados | 15 tabelas, versão 0: 4 contas (uma com maiúsculas no e-mail), aluna, aluno, professor, turma, disciplina, vínculos, nota e documento com arquivo |
| Backup | `pg_dump --clean --if-exists --no-owner --no-privileges` (cerca de 40 KB), uploads em tar e SHA-256 da chave de criptografia registrado |
| Plano | 001–008 pendentes, nenhum bloqueio, 2 avisos corretos |
| Aplicação | 8 propostas em cerca de 0,16 s |
| Depois | Versão 8, 54 tabelas, nenhum alerta, **dados idênticos aos de antes**, inicialização de produção aceita |
| Aplicação sobre o banco atualizado | `/healthz` 200; login do admin e da aluna 200; **download do documento com bytes idênticos**; professor 403 (quarentena da 002, esperado); conta legada `Misto@Legado.test` 404 (é o caso do aviso de maiúsculas) |
| Volta atrás | Banco recriado vazio e restaurado do dump; uploads restaurados: **dados iguais aos de antes**, versão 0, 15 tabelas, documento idêntico |
| Limpeza | Nenhum container ou volume do ensaio restante |

O ensaio também mostrou que a restauração **não** deve ser feita por cima do banco atualizado:
as tabelas criadas pelas propostas não estão no dump e continuariam lá. O procedimento correto
(recriar o banco vazio e restaurar) está documentado no guia de migrations.

O ensaio entrou no workflow `cloud-instances.yml`, com a imagem aprovada pelo CI.

## Revisão de código

- **Plano desatualizado:** o plano era calculado antes da trava, então outro operador poderia
  mudar o banco no intervalo. Agora o aplicador replaneja já com a trava e recusa se o plano
  mudou. Daí surgiu a opção oficial `--ate N`, porque testes que aplicavam parte do plano
  editado à mão passaram a ser recusados, como deveriam.
- **Detecção estrutural:** a proposta que completa o registro é identificada pela leitura do
  SQL (a coluna `checksum` acrescentada a `educafast_migracoes`), não por busca de texto.
- **Falso bloqueio:** antes da 008, o registro é naturalmente incompleto; esse alerta do
  inventário não bloqueia a atualização que justamente o corrige.
- **Ensaio:** o orquestrador roda no Python do host, sem dependências da aplicação; os dados de
  verificação passaram a vir das etapas no container. O volume de uploads monta em
  `/app/uploads`, que pertence ao usuário sem privilégios da imagem.

## Validação

**Testes novos:**

| Arquivo | Casos | Cobertura |
| --- | --- | --- |
| `unit/test_aplicador.py` | 6 | Corpo transacional (formatos válidos e 5 inválidos), literais seguros e recusa de valores que escapariam do SQL. Roda sem pacotes externos |
| `test_aplicador_postgresql.py` | 8 | Legado com dados atualizado preservando tudo e com checksums; banco vazio pela base; falha no meio desfaz só a proposta e nova execução completa; estado parcial bloqueia sem alterar; trava contra execução simultânea; plano desatualizado recusado; atualização em etapas com `--ate`; linha de comando exige alvo e confirmação exata |
| `test_registro_migracoes.py` | ajustado | Manifesto de arquivos congelados e base igual aos modelos atuais |
| `legacy_fixture.py` | apoio | Banco legado com dados, compartilhado por testes e ensaio |

**Bateria completa** (`.ci-results/a4-aplicador-ensaio-2026-11-22/`):

| Etapa | Resultado |
| --- | --- |
| Regressão | SQLite 291 ✓ (43 ign.), **PostgreSQL 291 ✓ (2 ign., os mesmos de sempre)**, HTTP 117 ✓ |
| `ci.py` | Deploy 11 ✓, SQLite 291 ✓, PostgreSQL 291 ✓, HTTPS/login e backup/restauração ✓ |
| Ensaio de atualização | ✓ (detalhes acima) |
| Piloto de duas escolas, API de frequência, painel central (18/18) | ✓ |
| Postman | SQLite e PostgreSQL: 57 requisições, 65 asserções, 0 falhas |

Também aprovados: unitários (inclusive sem pacotes externos) e actionlint.

## Para a revisão (A5)

- A ferramenta de aplicação existe, mas **nada foi aplicado em banco real**.
- **E-mails legados com maiúsculas:** não há banco legado real em PostgreSQL hoje, mas uma
  futura importação de dados do MySQL traria esse caso. Decisão para a A5: normalizar esses
  e-mails numa proposta própria (alteração de dados, exige revisão) ou tratá-los manualmente.
- A quarentena de professores da 002 continua exigindo a lista de professores confiáveis.

## Próxima etapa

A5: sessão de revisão com o usuário, com uma ficha por proposta.

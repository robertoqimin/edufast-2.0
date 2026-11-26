# Troca do banco de dados: MySQL 8.4 → PostgreSQL 17

Data: 22/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit «feat: adiciona inventario somente leitura das migrations (A1)».
Pedido do usuário: fazer a transição de forma segura, trocar todas as instâncias para
PostgreSQL e validar com testes de API e regressão antes de seguir para a A2 do
[plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).

## Resumo

Toda a aplicação, o painel Supremo, o gerador de instâncias por escola, os backups,
o deploy, o CI e os testes passaram a usar **PostgreSQL 17** (`postgres:17-alpine`)
com o driver **psycopg 3.2.10**. A regressão completa, a coleção Postman, o painel
central e as verificações de infraestrutura foram executados em PostgreSQL
descartável e comparados com uma linha de base em MySQL do mesmo commit de partida.

Nenhum banco persistente foi alterado. Os ambientes locais em MySQL foram
preservados com seus volumes. Nenhuma migration foi executada fora de bancos
descartáveis de teste.

## Resultados

Ambiente: Windows 11, Docker 29.4.0, imagem de teste com Python 3.12, SQLAlchemy 2.0.44,
psycopg 3.2.10 e PostgreSQL 17.12. Execuções em bancos descartáveis (tmpfs ou volumes
removidos ao final), com o papel da aplicação sem superusuário.

**Linha de base MySQL**, no commit de partida «feat: adiciona inventario somente leitura das migrations (A1)», numa cópia separada (worktree)
para não misturar com as alterações: `python .github/cicd/run_cursos_backend.py --suite regressao`.

| Verificação | MySQL (linha de base) | PostgreSQL (versão final) |
| --- | --- | --- |
| Regressão em SQLite | 243 aprovados, 27 ignorados | 252 aprovados, 31 ignorados |
| Regressão em banco real, com concorrência real | 243 aprovados, 2 ignorados | **252 aprovados, 2 ignorados** |
| HTTP real (JWT, multipart, download: frequência, estudos, cursos) | 117 verificações | **117 verificações** |

Os 9 testes a mais são novos: 4 de migrations/sequências (só PostgreSQL, por isso
ignorados no SQLite) e 5 de caminhos de arquivos. Os 2 ignorados no banco real são os
mesmos nas duas colunas: concorrência do painel central, coberta pelo runner próprio abaixo.

**Bateria final** (código final, já com `api/`), uma etapa por comando:

| Etapa | Comando | Resultado |
| --- | --- | --- |
| Regressão completa | `run_cursos_backend.py --suite regressao` | SQLite 252 ✓ (31 ign.), PostgreSQL 252 ✓ (2 ign.), HTTP 117 ✓; fonte inalterada durante a execução; limpeza ok |
| CI completo | `python .github/cicd/ci.py` | Imagem de produção, guardas de deploy (11 ✓), SQLite 252 ✓, PostgreSQL 252 ✓, HTTPS/CA/HSTS/login, **backup `pg_dump` e restauração** e uploads persistentes ✓ |
| Piloto de duas escolas | `node infra/smoke_cloud.cjs` | HTTPS, login, rejeição cruzada de JWT/cookie, rede PostgreSQL de B inacessível por A, backup e persistência ✓ |
| API de frequência | `run_frequencia_api.cjs --image …` | SQLite ✓, PostgreSQL com concorrência real ✓, HTTP 117 ✓ |
| Painel central | `run_platform_api.cjs …` | 18/18 ✓, incluindo as 2 concorrências reais (nenhum ignorado) |
| Postman (fluxos HTTP por perfil) | `run_postman.py` e `--database postgresql` | SQLite: 57 requisições, 65 asserções, 0 falhas. **PostgreSQL: 57, 65, 0 falhas**; registros e arquivos conferidos |

Também aprovados: unitários (`unit/`, inclusive sem pacotes externos), testes de
`infra/` (20), `infra/verify.sh` (Compose gerado, revisões incrementais, Nginx),
actionlint e shellcheck, protocolo estático de design, proteção de envio (4),
contratos futuros (`next_stage.py --check`: 90 API, 47 unitários), iniciador com Docker
simulado e caracterização do CI.

### Problemas encontrados durante a troca, todos corrigidos e retestados

1. Primeira rodada em PostgreSQL: 32 falhas em 5 arquivos. 30 eram colisões de chave
   primária causadas por IDs explícitos (sequência sem avançar). Corrigido com a paridade
   de sequências acima; `test_concurrency` passou de 17 problemas para 0.
2. 3 erros de `SAVEPOINT` vinham do teste novo `test_migrations_postgresql.py`, que
   devolvia ao pool uma conexão em modo autocommit. Defeito do teste, não da aplicação;
   corrigido.
3. A proteção "nunca recuar" das sequências falhou no primeiro teste (consulta via
   `pg_sequences`); trocada por leitura direta da sequência e coberta por teste.
4. `001_central.sql` precisava ser idêntico ao SQL gerado pelos modelos do painel: regenerado.

Evidências locais (fora do Git): `.ci-results/migracao-postgresql-2026-11-22/`
(`final/` com um log por etapa, `regressao/`, resumos do CI e do Postman).

## Decisões de segurança

| Tema | Decisão |
| --- | --- |
| Usuário do banco | O superusuário `postgres` só administra o servidor (`POSTGRES_ADMIN_PASSWORD`, antes `MYSQL_ROOT_PASSWORD`). Um script de inicialização embutido no Compose cria o papel da aplicação **sem superusuário**, dono apenas do banco da escola, como era o usuário MySQL. Verificado: `rolsuper = f`, dono do banco, cria tabelas; senha com `$` preservada |
| Testes com as permissões reais | Os runners de teste usam esse mesmo papel sem privilégios: um teste que dependesse de superusuário falharia |
| Ambientes existentes | O iniciador local passou a usar `.ci-results/manual-postgres` (projeto `edufast-manual-postgres`). Os ambientes MySQL `manual` e `manual-restaurado` não foram tocados; `-Ambiente Atual` só informa isso. As escolas Teste 01/02 recebem volume novo `postgres-<id>`; os volumes `mysql-<id>` continuam intactos |
| Backups | `pg_dump --clean --if-exists --no-owner --no-privileges` com o papel da aplicação por TCP e senha (nunca acesso local sem senha). Restauração com `psql -v ON_ERROR_STOP=1 --single-transaction` |
| Migrations | Cada proposta roda entre `BEGIN`/`COMMIT`: uma falha desfaz tudo, sem o estado parcial que o DDL do MySQL podia deixar. Continuam **pendentes de revisão** |
| Imagem de teste anterior | A imagem local `edufast-platform:test` foi reconstruída; a anterior ficou como `edufast-platform:mysql-anterior` |

## Diferenças de comportamento tratadas

| Diferença | Risco | Tratamento |
| --- | --- | --- |
| MySQL compara textos sem diferenciar maiúsculas; PostgreSQL diferencia | Login com `Ana@Escola` deixaria de achar `ana@escola`; contas duplicadas por caixa | Validador em `UsuarioModel` grava todo e-mail em minúsculas; login, cadastro e `create-admin` comparam com o valor normalizado (usa o índice) |
| `INSERT … ON DUPLICATE KEY UPDATE` (idempotência de envios) | Sem equivalente direto | `INSERT … ON CONFLICT DO NOTHING` + leitura com bloqueio, já usada no SQLite. Em READ COMMITTED a leitura vê o vencedor confirmado |
| MySQL avança `AUTO_INCREMENT` após ID explícito; a sequência do PostgreSQL não | Próximo ID automático colide (`duplicate key … _pkey`). Atingiu massas de teste e existe no código (`ConfiguracaoModel(id=1)`) | Ajuste em `app/database.py`: ao gravar ID explícito pelo ORM numa tabela com sequência, a sequência avança até o maior ID, **nunca recuando** (respeita valores já entregues a outras sessões). Teste dedicado |
| Valor padrão booleano `0` | PostgreSQL recusa | `server_default=false()` |
| `DATETIME(fsp=6)` do MySQL no painel central | Tipo inexistente | `TIMESTAMP` do PostgreSQL já guarda microssegundos |
| Erro de CHECK: MySQL 3819 (`OperationalError`) | Teste esperava código MySQL | PostgreSQL reporta SQLSTATE `23514` como `IntegrityError` |

## Caminhos de arquivos (pedido do usuário)

**Defeito encontrado:** com `UPLOAD_FOLDER` relativo (padrão `uploads`, usado no Compose
de desenvolvimento), a gravação de arquivos resolvia o caminho a partir da pasta em que
o processo foi iniciado (`os.path.abspath`, `Path`), mas o download de anexos de
aprovação (`send_from_directory` em `aprovacoes_routes.py`) resolvia a partir de `app/`,
por regra do Flask. O arquivo era salvo em `/app/uploads` e procurado em
`/app/app/uploads`: download com 404. Em produção não ocorria, porque o caminho já era
absoluto (`/app/uploads`).

**Correção:** `config.caminho_uploads()` ancora caminhos relativos em `api/` (onde
ficam o código e o volume do Docker) e mantém absolutos como estão. `Config.UPLOAD_FOLDER`
já sai absoluto, e os 13 pontos de gravação/leitura (documentos, foto de perfil, anexos de
aprovação, materiais de estudo, atestados e materiais de curso) passam pela função.
`test_upload_paths.py` cobre: resolução igual a partir de qualquer pasta, caminho absoluto
preservado, arquivo gravado encontrado pelo download (e reprodução do erro anterior), e
uma verificação que falha se algum código voltar a ler `UPLOAD_FOLDER` sem a âncora.

## Pasta `Códigos/` renomeada para `api/` (pedido do usuário)

O nome com acento aparecia corrompido (`C�digos`) em tracebacks do Windows, e o
iniciador montava o nome caractere a caractere para contornar isso. A pasta foi
renomeada e 48 arquivos tiveram as referências atualizadas: Dockerfile, workflows,
runners, scripts, iniciador e documentação, incluindo relatórios anteriores (somente o
caminho; resultados e datas não mudaram).

Não foram alterados: as capturas de `docs/design/referencias/` (o `AGENTS.md`
proíbe sobrescrevê-las; seus manifestos citam o caminho da época), o pacote histórico
`docs/arquivo/ci2/`, que tem a própria pasta `Códigos`, e a pasta `docs/prototipo/`,
fora do pedido.

**Ambiente virtual local:** `Códigos/backend/venv` (fora do Git) é o `python` ativo no
terminal do usuário e guarda caminhos absolutos. Para não quebrá-lo, ele foi mantido em
`Códigos/backend/venv`; essa é a única coisa que restou na pasta antiga. Recomendação:
recriar o ambiente em `api/backend/venv` quando for conveniente e depois remover a
pasta antiga.

**Efeito no Compose de desenvolvimento:** sem `-p`, o Docker Compose nomeia o projeto
pela pasta. Rodar `docker compose` em `api/` cria volumes novos (`codigos_*`); os
volumes antigos não são apagados. O iniciador e os ambientes gerados usam nomes de
projeto explícitos e não são afetados.

## O que mudou

**Aplicação** (`api/`): `config.py` (URL `postgresql+psycopg`, porta 5432),
`requirements.txt` (psycopg no lugar de PyMySQL), `app/database.py` (pool e paridade de
sequências), `app/concurrency.py`, `app/models/usuario_model.py`, `auth_controller.py`,
`commands.py`, guardas das massas de teste (`manual_test_data.py`,
`two_school_test_data.py`) e painel central (`control_plane/`).

**Migrations**: propostas 001–007 e `control_plane/migrations/001_central.sql` em SQL
PostgreSQL. As da escola são geradas por `migrations/gerar_postgresql.py` a partir dos
modelos, mantendo a lista e a ordem das tabelas das originais e o estado original de
`curso_aulas.video_id` (obrigatório na 003, opcional na 007). As versões MySQL estão em
`legado-mysql/`. O inventário da A1 reconhece `ALTER COLUMN … DROP NOT NULL`.

**Infraestrutura**: Compose de desenvolvimento e produção, gerador de instâncias
(`max_connections=30`, `shared_buffers=128MB`, equivalentes aos limites MySQL),
backup por cliente (`manage.cjs`), deploy (`deploy.sh`), demos, piloto `smoke_cloud`,
iniciador local e `.env.example`.

**CI e testes**: runners de regressão, painel central, frequência, revisão de mutações e
contratos futuros (`next/`), `compose.test.yml`/`compose.next.yml`, verificação de
backup, workflows (`ci.yml` ganhou a coleção Postman também em PostgreSQL).
Condições de banco real dos testes passaram de `mysql` para `postgresql`.

**Testes novos**: `test_migrations_postgresql.py` aplica 001–007 sobre o esquema legado
e compara com os modelos (colunas, tipos, nulos, chaves, índices, FKs, CHECKs), confere
a quarentena de dados da 002, prova que migration com falha não deixa estado parcial e
valida a paridade de sequências. `run_postman.py --database postgresql` executa a
coleção HTTP contra PostgreSQL descartável.

**Documentação**: README, arquitetura, execução, CI, testes, infra, migrations, segurança,
Postman e contratos da próxima versão. Relatórios e planos datados anteriores
continuam descrevendo o MySQL da época, como registro histórico.

## Mantido como histórico

- `api/migrations/legado-mysql/` e `control_plane/migrations/legado-mysql/`.
- `.github/cicd/next/legacy/mysql.json` e `capture_legacy.py`: captura congelada do
  esquema do commit `1f034fa`, com verificação de origem.

## Pendências e limites

- **Migrations continuam pendentes de revisão do usuário.** Os testes aplicaram 001–007 e
  `001_central.sql` só em bancos descartáveis. Nenhum banco persistente existe ainda em
  PostgreSQL.
- **Dados antigos em MySQL não foram convertidos.** Todos eram sintéticos (ambiente manual,
  escolas Teste 01/02). Os volumes MySQL foram preservados; removê-los é decisão do usuário.
  As novas instalações começam com banco PostgreSQL vazio e massa recriada pelos scripts.
- **Comparação de desempenho MySQL × PostgreSQL não foi medida.** A regressão em PostgreSQL
  levou cerca de 180 s, contra cerca de 209 s em MySQL na mesma máquina; isso não é um teste
  de carga.
- **Inspeção visual não foi refeita:** não houve mudança de telas, templates ou CSS.
- **Workflows do GitHub** foram validados com actionlint e reproduzidos localmente, mas só
  rodam de fato no GitHub após o push.
- **Ambiente virtual local** do usuário permanece em `Códigos/backend/venv` (ver seção da
  renomeação).
- Os contratos futuros (`tdd.yml`) continuam vermelhos de propósito; só o banco do executor
  mudou.

## Próxima etapa

A2 do plano: propor a migration 008 (registro de versão em `educafast_migracoes`),
agora em PostgreSQL. Proposta apenas; execução somente após revisão.

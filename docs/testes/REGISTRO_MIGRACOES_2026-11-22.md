# A2 — Registro de versões do esquema (proposta 008)

Data: 22/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit «feat: troca o banco para PostgreSQL 17, corrige caminhos de arquivos e renomeia api».
Etapa A2 do [plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).
**Estado: proposta para revisão. Nenhum SQL foi executado em banco persistente.**

## Problema

O [inventário da A1](INVENTARIO_ESQUEMA_2026-11-22.md) mostrou que o registro de versões
não é confiável: `educafast_migracoes` (criada pela 003) tem só a coluna `versao`, e as
propostas 004–007 não gravam nela. Não dá para saber com segurança em que versão cada escola
está, e nada impede uma release antiga de rodar sobre um banco mais novo.

## O que a proposta 008 faz

`api/migrations/008_registro_migracoes.sql`, em PostgreSQL, entre `BEGIN`/`COMMIT`:

1. **Completa a tabela** com `descricao`, `arquivo`, `checksum` (SHA-256, 64 caracteres),
   `aplicada_em` e `origem` (`aplicada` ou `detectada`), com CHECKs para os dois últimos.
2. **Registra o passado sem adivinhar:** cada proposta 001–007 só é registrada como
   `detectada` se **toda** a sua estrutura existir (tabelas, colunas, índices e nulidade). As
   condições são geradas por `gerar_postgresql.py` a partir das mesmas assinaturas que o
   inventário usa, então não há lista mantida à mão. Uma proposta parcial não é registrada
   e continua aparecendo no inventário como parcial.
3. **Preserva registros existentes:** uma linha já gravada mantém sua origem; só `descricao`
   e `arquivo` são completados.
4. **Registra a si mesma** como versão 8, origem `aplicada`.

**Por que o checksum fica vazio:** um arquivo não pode conter o próprio hash, porque incluí-lo
muda o conteúdo. O checksum será gravado por um aplicador revisado (A4) no momento da
aplicação. Quando existe, é comparado com o arquivo da release, com quebras de linha
normalizadas (o Git no Windows pode trocar LF por CRLF).

**Diferença em relação ao texto original da A2:** o plano previa "fazer cada migration
registrar sua linha". Isso não é possível para 001 e 002, que rodam antes de a tabela existir,
nem para o checksum de nenhuma delas. A 008 resolve o passado por detecção estrutural e
deixa o registro com checksum para o aplicador da A4.

## Proteções na aplicação

| Onde | Comportamento |
| --- | --- |
| `database.init_db` (só produção) | **Recusa iniciar** se o banco registra migration mais nova que a última conhecida pela release ("use a release correspondente ao banco"), se uma migration registrada com checksum tem conteúdo diferente do arquivo, ou se o arquivo registrado não existe. Recusa também uma release sem a pasta `migrations/` |
| `database.init_db` | **Aceita** instalações que ainda não aplicaram a 008: as colunas novas de `educafast_migracoes` são opcionais até a revisão |
| `schema_inventory.py` | Mostra as mesmas inconsistências como alertas, sem bloquear; a 008 aparece como `aplicada` quando suas colunas existem |
| `MigracaoSchemaModel` | Modelo atualizado com as colunas e CHECKs da 008 |
| `gerar_postgresql.py` | Gera 001–008; mantém a forma original da tabela na 003 (só `versao`), para que 001–007 não mudem |

As regras ficam numa função pura (`problemas_registro`), usada pela inicialização e pelo inventário.

## Validação

Ambiente: Windows 11, Docker 29.4.0, imagem de teste com Python 3.12 e PostgreSQL 17.12,
bancos descartáveis com o papel da aplicação sem superusuário.

**Testes novos (14):**

| Arquivo | Casos | O que garante |
| --- | --- | --- |
| `unit/test_registro_migracoes.py` | 5 | Versão mais nova recusada; checksum igual aceito mesmo com CRLF; checksum diferente e arquivo ausente recusados; registro sem checksum aceito. Roda sem pacotes externos |
| `test_registro_migracoes.py` | 7 | Propostas commitadas idênticas ao gerador (001–008); a 008 cobre todas as anteriores; inicialização de produção aceita banco sem a 008 e recusa banco mais novo; checksum divergente recusado e alertado pelo inventário |
| `test_migrations_postgresql.py` | +2 | Em PostgreSQL real: 001–008 em sequência registram 1–7 como `detectada` e 8 como `aplicada`, sem alertas; com a 006 incompleta, ela não é registrada, a linha manual da 003 é preservada e o inventário acusa a parcial |

O teste que já existia, de 001–008 em sequência resultando exatamente no esquema dos modelos,
agora cobre também a 008 (colunas, tipos, nulidade e CHECKs de `educafast_migracoes`).

**Bateria completa no código final** (`.ci-results/a2-registro-migracoes-2026-11-22/`):

| Etapa | Resultado |
| --- | --- |
| Regressão (`run_cursos_backend.py --suite regressao`) | SQLite 266 ✓ (33 ign.), **PostgreSQL 266 ✓ (2 ign., os mesmos de sempre)**, HTTP 117 ✓ |
| `ci.py` | Imagem de produção, deploy 11 ✓, SQLite 266 ✓, PostgreSQL 266 ✓, HTTPS/login e backup/restauração ✓. A inicialização de produção com a nova verificação subiu normalmente |
| Piloto de duas escolas (`smoke_cloud.cjs`) | Aplicações de produção iniciaram com a verificação; isolamento, JWT cruzado e backup ✓ |
| API de frequência | SQLite ✓, PostgreSQL ✓, HTTP 117 ✓ |
| Painel central | 18/18 ✓ |
| Postman | SQLite e PostgreSQL: 57 requisições, 65 asserções, 0 falhas |

Durante o desenvolvimento, a primeira rodada em PostgreSQL falhou porque a preparação do
teste removia colunas da 008 de uma tabela não legada (`educafast_migracoes`). Defeito da
preparação do teste, corrigido antes da bateria.

## Para a revisão (A5)

- Pré-requisito da 008: proposta 003 aplicada (a tabela de registro nasce nela).
- Conferir no banco alvo, antes, com `schema_inventory.py`: propostas parciais não serão
  registradas e precisam de decisão própria.
- A 008 só altera `educafast_migracoes`. Nenhuma outra tabela, conta ou dado escolar é tocado.
- Releases anteriores a esta não conhecem a verificação e continuariam iniciando sobre um
  banco com a 008 (colunas extras não as impedem). A proteção vale desta release em diante.

## Próxima etapa

A3 do plano: esquema base único para banco novo, equivalente a 001–008 aplicadas em
sequência, com comparação automática em PostgreSQL.

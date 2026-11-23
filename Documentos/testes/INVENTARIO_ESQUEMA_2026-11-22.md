# A1 — Inventário de esquema somente leitura

Data: 22/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit «docs: atualiza README com estado atual do produto».
Etapa A1 do [plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).

## Objetivo

Saber, sem alterar nada, quais das migrations propostas (001–007 da escola e
001 do banco central) estão presentes em cada banco: aplicadas, parciais ou
ausentes. Isso é pré-requisito para revisar e ativar as migrations (A2–A5) com
segurança em várias escolas.

## O que mudou

| Arquivo | Mudança |
| --- | --- |
| `Codigos/schema_inventory.py` | Novo. Lê `migrations/NNN_*.sql`, extrai tabelas, colunas adicionadas, índices e colunas que passam a aceitar nulo; compara com a estrutura real do banco |
| `Codigos/schema_preflight.py` | O relatório passa a incluir a chave `migrations` com o inventário |
| `.github/cicd/tests/unit/test_schema_inventory.py` | Novo. 9 testes sem banco: leitura dos SQL e classificação |
| `.github/cicd/tests/test_schema_inventory.py` | Novo. 4 testes SQLite + 2 MySQL (somente no runner descartável) |

### Como funciona

- A lista do que procurar vem **dos próprios arquivos SQL**. Uma migration nova
  (por exemplo, a 008) entra no inventário sem editar o código.
- Situação por migration: `aplicada` (tudo presente), `parcial` (com a lista
  `faltando`) ou `ausente`.
- `versao_estrutural`: maior versão N em que todas as migrations de 1 até N estão aplicadas.
- Alertas: migration parcial (inspecionar antes de repetir, pois DDL MySQL não tem
  rollback), migration aplicada fora de ordem e divergência entre a estrutura detectada
  e as versões gravadas em `educafast_migracoes`.
- Somente leitura: usa reflexão do SQLAlchemy e um `SELECT` em `educafast_migracoes`.
  Exige `EDUFAST_REVIEW_DB_URL` explícito; nunca usa o `.env`.

### Uso

```bash
cd Codigos
EDUFAST_REVIEW_DB_URL='mysql+pymysql://usuario:senha@host/banco' python schema_inventory.py
EDUFAST_REVIEW_DB_URL='mysql+pymysql://usuario:senha@host/edufast_platform' python schema_inventory.py --central
EDUFAST_REVIEW_DB_URL='...' python schema_preflight.py   # relatório completo, agora com "migrations"
```

Use um usuário de banco com permissão apenas de leitura.

## Validação executada

Ambiente: Windows 11, Python 3.14.3; ambiente virtual temporário com
`Codigos/requirements.txt` (Flask 3.1.0, SQLAlchemy 2.0.44). Docker Desktop
não estava em execução.

| Comando | Resultado |
| --- | --- |
| `PYTHONPATH=Codigos python -m unittest discover -s .github/cicd/tests/unit -v` | 12 testes, todos aprovados (9 novos + 3 existentes) |
| `PYTHONPATH=Codigos python -S -m unittest discover -s .github/cicd/tests/unit` | Aprovado sem pacotes externos, como exige a pasta `unit/` |
| `python -m unittest test_schema_inventory -v` (SQLite em memória) | 4 aprovados, 2 ignorados (MySQL) |
| `schema_inventory.py` num SQLite com todas as tabelas menos `estudo_secoes` e `curso_retomadas` | 001–005 aplicadas, 006 e 007 parciais com a falta listada, `versao_estrutural` 5, alerta de registro divergente |
| `schema_inventory.py --central` no mesmo banco | `001_central.sql` ausente, como esperado |
| `schema_preflight.py` no mesmo banco | Relatório anterior preservado (54 tabelas) com a nova chave `migrations` |

Um teste confirma que os modelos atuais correspondem a **todas** as migrations
propostas: se alguém alterar um modelo sem atualizar o SQL (ou o contrário), o
teste falha.

## Não executado

- Os 2 testes MySQL (reflexão completa e detecção da 007 com `video_id NOT NULL`)
  não rodaram localmente. Rodam no CI (`ci.py`) ou com Docker ativo via
  `python .github/cicd/run_cursos_backend.py --suite regressao`.
- O inventário não foi executado contra bancos persistentes (escolas Teste 01/02
  ou o ambiente manual). Isso pode ser feito, por ser somente leitura, quando você autorizar.
- A regressão completa não foi repetida; nenhum código da aplicação em execução foi alterado.

## Constatações

1. **O registro de versões não é confiável hoje.** A simulação mostrou estrutura
   na versão 5 e `educafast_migracoes` vazia. A tabela só é criada pela 003 e as
   migrations 004–007 não gravam nela. Confirma o diagnóstico D2 e motiva a A2.
2. **Mudanças só de dados não são detectáveis.** A 002 coloca professores antigos
   em quarentena via `UPDATE`; o inventário só vê as colunas. A revisão A5 precisa
   tratar isso à parte.
3. **Documentação:** [PAINEL_SUPREMO_2026-11-12.md](../planejamento/PAINEL_SUPREMO_2026-11-12.md)
   diz que `001_central.sql` cria seis tabelas; o SQL e os modelos têm **cinco**
   (`platform_owner`, `platform_schools`, `platform_people`, `platform_movements`,
   `platform_audit`).

## Próxima etapa

A2 — propor a migration 008 para completar `educafast_migracoes` (descrição,
checksum, data de aplicação) e fazer cada migration registrar sua versão.
Proposta apenas; execução somente após a revisão A5.

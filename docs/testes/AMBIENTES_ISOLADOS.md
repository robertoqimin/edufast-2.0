# Preparação de ambientes independentes — 04/11/2026

Este é o registro da primeira rodada. A [revisão pré-commit](REVISAO_PRE_COMMIT_2026-11-04.md)
registra as verificações posteriores com Docker disponível e a revisão manual solicitada.

Base: `fb840c6`, com alterações locais desta entrega, sem commit novo e sem deploy.
Escopo: gerador de instalações por escola, gateway, limites de recursos/HTTP,
pool de conexões e arquitetura local/nuvem/híbrida. Guia: [`infra/README.md`](../../infra/README.md).

## Execuções desta versão

| Verificação | Resultado |
| --- | --- |
| `node --test infra/test_environments.cjs .github/cicd/test_submission.cjs` | 8 testes aprovados |
| Compose gerado com duas escolas, `docker compose ... config --quiet` | Aprovado, sem iniciar containers |
| `python -m unittest discover -s .github/cicd/tests -v` | 99 testes: 84 aprovados, 15 ignorados por exigirem MySQL |
| Suíte `test_runtime_limits.py`, após reforçar teste com esgotamento real de QueuePool | 3 aprovados; pool volta a atender após liberar conexão |
| Compilação dos Python alterados e novos | Aprovada |
| `python api/tests/verificar_protocolo_design.py` | Aprovado; sem alteração de interface |
| `git diff --check` | Aprovado |

Ambiente Python local: 3.14.3, venv descartável em `.ci-results/runtime-venv`,
SQLite em memória e chave sintética. Dependências instaladas do requirements.
Produção usa Python 3.12, portanto não tratar esta execução como homologação da imagem.
A regressão emitiu avisos existentes de `datetime.utcnow()` e conexão SQLite não
fechada; não impediram a execução. Log local: `.ci-results/runtime-tests.log`,
ignorado pelo Git. Não foi lido nem alterado banco existente.

Os testes verificam separação declarada de redes/volumes/segredos, ausência de
portas publicadas em apps/bancos, rejeição de entrada malformada, recusa de
sobrescrita de segredos, resposta 503 em pool esgotado e rejeição 413 de corpo
acima do limite. Não equivalem a tráfego real entre duas escolas implantadas.

## Verificações ainda necessárias

- Docker daemon não estava em execução. Não foram executados `nginx -t` em
  container, MySQL, imagem Linux/Gunicorn, TLS real ou aplicação da frota.
- `infra/verify.sh` foi incorporado ao CI para validar Compose e Nginx com TLS
  sintético em runner com Docker. Essa nova execução remota ainda não ocorreu.
- Nenhum ensaio de carga, p95/p99 de tráfego acadêmico, esgotamento real de RAM/disco,
  perda de host ou restauração híbrida foi realizado. A sonda `load.cjs` é ferramenta
  preparada, não evidência de capacidade.
- Imagem da aplicação deve ser produzida e aprovada com estes arquivos antes de
  gerar instalação real. Não usar digest antigo que não contenha a configuração.
- Provisionamento/migrations continuam exigindo revisão humana. Não foram executados.
- Certificados, renovação, backups externos, inventário, monitoramento e promoção
  de contingência dependem de configuração do ambiente; não estão automatizados.

O híbrido entregue nesta etapa é o modelo de implantação e procedimento de
recuperação com único escritor. Não há sincronização bidirecional nem failover
automático. A topologia continua sujeita à falha comum do servidor/gateway.

#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
project="${EDUCAFAST_CI_PROJECT:-educafast-ci}"
[[ "$project" =~ ^educafast-ci(-[a-z0-9-]+)?$ ]] || { echo 'Use um projeto Docker exclusivo com prefixo educafast-ci.' >&2; exit 2; }
compose=(docker compose -p "$project" -f "$root/Códigos/docker-compose.test.yml")
cleanup() { "${compose[@]}" down --remove-orphans; }
trap cleanup EXIT
"${compose[@]}" build testes
"${compose[@]}" run --rm --no-deps testes python tests/verificar_protocolo_design.py
for task in executar_regressao.py executar_postman.py; do
  "${compose[@]}" run --rm --no-deps -e EDUCAFAST_TEST_MYSQL=0 -e EDUCAFAST_REPORTS_DIR=ci/sqlite testes python "tests/$task"
done
"${compose[@]}" up -d --wait --wait-timeout 180 mysql_test
for task in executar_regressao.py executar_postman.py; do
  "${compose[@]}" run --rm -e EDUCAFAST_REPORTS_DIR=ci/mysql testes python "tests/$task"
done
python3 Códigos/tests/comparar_resultados.py --baseline Documentos/testes/baselines/pre-2.0 --resultados Documentos/testes/resultados/ci/sqlite
python3 Códigos/tests/comparar_resultados.py --baseline Documentos/testes/baselines/pre-2.0/mysql --resultados Documentos/testes/resultados/ci/mysql
docker build --tag educafast-security-app Códigos
python3 Códigos/tests/validar_transporte.py --directory "$root/.cache/ci-tls"

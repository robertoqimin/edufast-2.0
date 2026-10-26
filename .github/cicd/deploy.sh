#!/usr/bin/env bash
# Executado no servidor Linux. Nunca remove volumes ou restaura dados automaticamente.
set -Eeuo pipefail
directory="${1:-}"; commit="${2:-}"; image="${3:-}"; public_url="${4:-}"
[[ "$directory" =~ ^/[a-zA-Z0-9/_-]+$ && "$directory" != / ]] || exit 2
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || exit 2
[[ "$image" =~ ^ghcr\.io/samucau1/edufast-2\.0@sha256:[a-f0-9]{64}$ ]] || exit 2
[[ "$public_url" =~ ^https://[a-zA-Z0-9.-]+(:[0-9]+)?/?$ ]] || exit 2
cd "$directory"
umask 077
[[ -f .env.production && -f "releases/$commit/compose.production.yml" ]] || { echo 'Provisione o servidor antes do CD.' >&2; exit 2; }
mkdir -p backups
exec 9>backups/.deploy.lock
flock -n 9 || { echo 'Outra implantação está em andamento.' >&2; exit 2; }
export EDUFAST_IMAGE="$image"
compose=(docker compose -p edufast-production --env-file "$directory/.env.production" -f "$directory/releases/$commit/compose.production.yml")
"${compose[@]}" config --quiet
container="$("${compose[@]}" ps -q app)"
[[ -n "$container" ]] || { echo 'Execute a primeira instalação assistida antes de atualizar pelo CD.' >&2; exit 2; }
previous="$(docker inspect --format '{{.Config.Image}}' "$container")"
[[ "$previous" =~ ^ghcr\.io/samucau1/edufast-2\.0@sha256:[a-f0-9]{64}$ ]] || { echo 'Imagem anterior precisa estar fixada por digest.' >&2; exit 2; }
"${compose[@]}" pull app
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$commit"
phase=backup
recover() {
  if [[ "$phase" == backup ]]; then
    export EDUFAST_IMAGE="$previous"
    "${compose[@]}" up -d --no-deps --no-build app || true
  else
    echo "Falha após iniciar a nova versão. Não houve downgrade de esquema. Revise logs e backups/$stamp antes de recuperar." >&2
  fi
}
trap recover ERR
"${compose[@]}" stop app
# As variáveis são expandidas dentro do container, não no shell do servidor.
# shellcheck disable=SC2016
"${compose[@]}" exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump --single-transaction --no-tablespaces --set-gtid-purged=OFF -u"$MYSQL_USER" "$MYSQL_DATABASE"' > "backups/$stamp.sql.partial"
EDUFAST_IMAGE="$previous" "${compose[@]}" run --rm --no-deps --entrypoint tar app -czf - -C /app uploads > "backups/$stamp-uploads.tar.gz.partial"
[[ -s "backups/$stamp.sql.partial" && -s "backups/$stamp-uploads.tar.gz.partial" ]]
gzip -t "backups/$stamp-uploads.tar.gz.partial"
mv "backups/$stamp.sql.partial" "backups/$stamp.sql"
mv "backups/$stamp-uploads.tar.gz.partial" "backups/$stamp-uploads.tar.gz"
printf 'previous=%s\nnew=%s\ncommit=%s\n' "$previous" "$image" "$commit" > "backups/$stamp-release.txt"
phase=started
"${compose[@]}" up -d --no-deps --no-build --wait --wait-timeout 180 app
"${compose[@]}" up -d --no-deps --force-recreate proxy
ready=false
for _ in {1..30}; do
  if response="$(curl --fail --silent --show-error --max-time 10 "${public_url%/}/healthz")" && python3 -c 'import json,sys; r=json.loads(sys.argv[1]); sys.exit(0 if r.get("status")=="ok" and r.get("release")==sys.argv[2] else 1)' "$response" "$image"; then
    ready=true; break
  fi
  sleep 2
done
[[ "$ready" == true ]]
ln -sfn "$directory/releases/$commit" "$directory/current"
trap - ERR
printf 'Implantação verificada por HTTPS: %s\n' "$image"

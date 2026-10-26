#!/usr/bin/env bash
# Executado no futuro servidor Linux via SSH. Nunca recria volumes nem restaura backups automaticamente.
set -Eeuo pipefail
directory="${1:-}"; image="${2:-}"; public_url="${3:-}"
[[ "$directory" =~ ^/[a-zA-Z0-9/_-]+$ && "$directory" != / ]] || { echo 'Diretório de produção inválido.' >&2; exit 2; }
[[ "$image" =~ ^ghcr\.io/samucau1/edufast-2\.0@sha256:[a-f0-9]{64}$ ]] || { echo 'Imagem fora do repositório/digest permitido.' >&2; exit 2; }
[[ "$public_url" =~ ^https://[a-zA-Z0-9.-]+(:[0-9]+)?/?$ ]] || { echo 'URL HTTPS inválida.' >&2; exit 2; }
cd "$directory"
[[ -f .env.production && -f Códigos/docker-compose.production.yml ]] || { echo 'Provisione o servidor e .env.production antes do CD.' >&2; exit 2; }
umask 077
mkdir -p backups
exec 9>backups/.deploy.lock
flock -n 9 || { echo 'Outra implantação está em andamento.' >&2; exit 2; }
export EDUCAFAST_IMAGE="$image"
compose=(docker compose -p educafast-production --env-file "$directory/.env.production" -f "$directory/Códigos/docker-compose.production.yml")
"${compose[@]}" config --quiet
container="$("${compose[@]}" ps -q app)"
[[ -n "$container" ]] || { echo 'Faça a primeira instalação assistida antes de usar atualizações pelo CD.' >&2; exit 2; }
previous="$(docker inspect --format '{{.Config.Image}}' "$container")"
"${compose[@]}" pull app
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
phase=backup
recover() {
  if [[ "$phase" == backup ]]; then
    export EDUCAFAST_IMAGE="$previous"
    "${compose[@]}" up -d --no-build app || true
  else
    echo 'Implantação falhou após iniciar a versão nova. Não houve downgrade de esquema nem restauração automática. Confira os logs e o backup no servidor.' >&2
  fi
}
trap recover ERR
"${compose[@]}" stop app
"${compose[@]}" exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump --single-transaction --no-tablespaces --set-gtid-purged=OFF -u"$MYSQL_USER" "$MYSQL_DATABASE"' > "backups/$stamp.sql"
EDUCAFAST_IMAGE="$previous" "${compose[@]}" run --rm --no-deps --entrypoint tar app -czf - -C /app uploads > "backups/$stamp-uploads.tar.gz"
[[ -s "backups/$stamp.sql" && -s "backups/$stamp-uploads.tar.gz" ]]
printf 'anterior=%s\nnova=%s\n' "$previous" "$image" > "backups/$stamp-release.txt"
phase=migracao
"${compose[@]}" up -d --no-build --wait --wait-timeout 180 app
ready=false
for attempt in {1..30}; do
  if curl --fail --silent --show-error --max-time 10 "$public_url" >/dev/null; then ready=true; break; fi
  sleep 2
done
[[ "$ready" == true ]]
trap - ERR
printf 'Implantação concluída: %s\n' "$image"

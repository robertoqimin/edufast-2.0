#!/usr/bin/env bash
# Somente configurações descartáveis: nenhum banco ou app é iniciado.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
node --test infra/test_environments.cjs infra/test_manage.cjs
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
node -e 'const fs=require("fs");const m={image:"ghcr.io/samucau1/edufast-2.0@sha256:"+"a".repeat(64),schools:[{id:"escola-a",host:"a.example.test"},{id:"escola-b",host:"b.example.test"}]};fs.writeFileSync(process.argv[1],JSON.stringify(m))' "$work/manifest.json"
node infra/generate.cjs "$work/manifest.json" "$work/generated"
docker compose -p edufast-config-check --env-file "$work/generated/.env" -f "$work/generated/compose.json" config --quiet
node -e 'const fs=require("fs");const m=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));m.project="edufast-config-check";fs.writeFileSync(process.argv[1],JSON.stringify(m))' "$work/manifest.json"
node infra/manage.cjs prepare "$work/manifest.json" "$work/revision-1"
node infra/manage.cjs prepare "$work/manifest.json" "$work/revision-2" "$work/revision-1"
node infra/manage.cjs run "$work/revision-2" validate
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=a.example.test' \
  -keyout "$work/generated/tls/privkey.pem" -out "$work/generated/tls/fullchain.pem" 2>/dev/null
docker run --rm --mount "type=bind,source=$work/generated/nginx.conf,target=/etc/nginx/nginx.conf,readonly" \
  --mount "type=bind,source=$work/generated/tls,target=/etc/nginx/tls,readonly" nginx:1.30.6-alpine nginx -t

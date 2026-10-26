#!/usr/bin/env bash
# Runner GitHub: valida tudo antes de abrir SSH, envia configuração do commit testado.
set -Eeuo pipefail
python .github/cicd/check_deploy.py
umask 077
work="$(mktemp -d)"
trap 'rm -f -- "$work/key" "$work/known_hosts" "$work/release.tar.gz"; rmdir -- "$work"' EXIT
printf '%s\n' "$SSH_KEY" > "$work/key"
printf '%s\n' "$KNOWN_HOSTS" > "$work/known_hosts"
ssh_args=(-i "$work/key" -o "UserKnownHostsFile=$work/known_hosts" -o StrictHostKeyChecking=yes -o BatchMode=yes -p "$DEPLOY_PORT")
remote="$DEPLOY_USER@$DEPLOY_HOST"
release="$DEPLOY_DIR/releases/$RELEASE_SHA"
tar -czf "$work/release.tar.gz" -C .github/cicd compose.production.yml Caddyfile deploy.sh
# Caminho validado localmente e enviado como literal ao shell remoto.
# shellcheck disable=SC2029
ssh "${ssh_args[@]}" "$remote" "mkdir -p '$release'"
scp -i "$work/key" -o "UserKnownHostsFile=$work/known_hosts" -o StrictHostKeyChecking=yes -o BatchMode=yes -P "$DEPLOY_PORT" "$work/release.tar.gz" "$remote:$release/release.tar.gz"
# shellcheck disable=SC2029
ssh "${ssh_args[@]}" "$remote" "tar -xzf '$release/release.tar.gz' -C '$release'"
image="ghcr.io/samucau1/edufast-2.0@$IMAGE_DIGEST"
ssh "${ssh_args[@]}" "$remote" bash -s -- "$DEPLOY_DIR" "$RELEASE_SHA" "$image" "$PUBLIC_URL" < .github/cicd/deploy.sh

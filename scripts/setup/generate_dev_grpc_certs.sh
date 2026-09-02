#!/bin/bash
# Generate a self-signed dev CA + mTLS server/client certificate pair for
# the docker-compose gRPC stack (security audit finding A02 -- transport
# TLS for gRPC). Dev/local only: a single shared cert covers every known
# compose service hostname via SAN, which is fine for a local, disposable
# CA but must never be reused beyond a dev machine.
#
# Output: certs/grpc-dev/{ca.crt,server.crt,server.key,client.crt,client.key}
# Mounted read-only into every gRPC server/client container by
# docker-compose.yml at /certs/grpc, referenced via GRPC_TLS_* env vars
# (see libs/flask_core/flask_core/grpc_tls.py).
#
# Idempotent: skips regeneration if the CA already exists, so `make dev`
# can depend on this target without forcing new certs (and therefore new
# TLS trust) on every run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERT_DIR="${REPO_ROOT}/certs/grpc-dev"
DAYS_VALID=825  # ~2.25 years; well under CA/Browser Forum caps, plenty for local dev

if [ -f "${CERT_DIR}/ca.crt" ] && [ -f "${CERT_DIR}/server.crt" ] && [ -f "${CERT_DIR}/client.crt" ]; then
  echo "[grpc-dev-certs] ${CERT_DIR} already populated -- skipping (delete the dir to force regeneration)"
  exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "[grpc-dev-certs] ERROR: openssl is required but not found on PATH" >&2
  exit 1
fi

mkdir -p "${CERT_DIR}"
# 755, not 700: this dir is bind-mounted read-only into containers running
# as `appuser` (a different UID than the host user generating these certs).
# A 700 directory blocks traversal for any non-owner UID regardless of the
# files' own permissions inside it -- see the matching *.key chmod below for
# why the files themselves are 644 too.
chmod 755 "${CERT_DIR}"

# Every compose service/container name known to run or dial a gRPC server,
# both spellings where router_module's Config defaults disagree with the
# actual compose container_name (pre-existing drift, out of scope to fix
# here -- both are included so a TLS cert mismatch is never the cause of a
# failed handshake regardless of which name resolves).
SAN="DNS:localhost,IP:127.0.0.1"
for host in \
  action-discord action-slack action-twitch action-youtube action-lambda action-gcp-functions \
  action-googlechat action-mattermost action-teams action-openwhisk interactive-translate \
  core-identity core-browser-source core-workflow core-reputation core-router core-data \
  discord-action slack-action twitch-action youtube-action lambda-action gcp-functions-action \
  openwhisk-action reputation workflow-core browser-source identity-core hub \
  ; do
  SAN="${SAN},DNS:${host}"
done

echo "[grpc-dev-certs] generating dev CA + server/client certs in ${CERT_DIR}"

# --- CA -----------------------------------------------------------------
openssl genrsa -out "${CERT_DIR}/ca.key" 4096 2>/dev/null
openssl req -x509 -new -nodes \
  -key "${CERT_DIR}/ca.key" \
  -sha256 -days "${DAYS_VALID}" \
  -subj "/O=WaddleBot Dev/CN=waddlebot-dev-grpc-ca" \
  -out "${CERT_DIR}/ca.crt"

# --- Server cert (multi-SAN, covers every compose gRPC server) ----------
openssl genrsa -out "${CERT_DIR}/server.key" 2048 2>/dev/null
openssl req -new \
  -key "${CERT_DIR}/server.key" \
  -subj "/O=WaddleBot Dev/CN=waddlebot-grpc-server" \
  -out "${CERT_DIR}/server.csr"
openssl x509 -req \
  -in "${CERT_DIR}/server.csr" \
  -CA "${CERT_DIR}/ca.crt" -CAkey "${CERT_DIR}/ca.key" -CAcreateserial \
  -days "${DAYS_VALID}" -sha256 \
  -extfile <(printf "subjectAltName=%s\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth" "${SAN}") \
  -out "${CERT_DIR}/server.crt"

# --- Client cert (mTLS -- presented by every gRPC-dialing service) ------
openssl genrsa -out "${CERT_DIR}/client.key" 2048 2>/dev/null
openssl req -new \
  -key "${CERT_DIR}/client.key" \
  -subj "/O=WaddleBot Dev/CN=waddlebot-grpc-client" \
  -out "${CERT_DIR}/client.csr"
openssl x509 -req \
  -in "${CERT_DIR}/client.csr" \
  -CA "${CERT_DIR}/ca.crt" -CAkey "${CERT_DIR}/ca.key" -CAcreateserial \
  -days "${DAYS_VALID}" -sha256 \
  -extfile <(printf "keyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=clientAuth") \
  -out "${CERT_DIR}/client.crt"

rm -f "${CERT_DIR}"/*.csr "${CERT_DIR}/ca.srl"
# 644, not 600: these are bind-mounted read-only into containers running as
# `appuser` (a different UID than the host user that generated them), so a
# owner-only 600 key is unreadable inside the container and every gRPC
# server/client fails TLS setup at startup. Dev-only, disposable CA (see
# header comment) -- world-readable key files are an acceptable tradeoff
# here and must never be replicated for a real/production CA.
chmod 644 "${CERT_DIR}"/*.key
chmod 644 "${CERT_DIR}"/*.crt

echo "[grpc-dev-certs] done: $(ls "${CERT_DIR}")"

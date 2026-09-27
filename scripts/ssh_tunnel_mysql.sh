#!/usr/bin/env bash
set -euo pipefail

SERVER_IP="${SERVER_IP:-141.148.172.198}"
SSH_USER="${SSH_USER:-ubuntu}"
LOCAL_PORT="${LOCAL_PORT:-3307}"
REMOTE_HOST="${REMOTE_HOST:-127.0.0.1}"
REMOTE_PORT="${REMOTE_PORT:-3306}"

echo "Opening SSH tunnel: localhost:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT} on ${SSH_USER}@${SERVER_IP}"
exec ssh -N -L "${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}" "${SSH_USER}@${SERVER_IP}"

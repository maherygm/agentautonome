#!/usr/bin/env bash
# Lance API FastAPI (:8000) + UI Vite (:5173). Ctrl+C arrête les deux.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-5173}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  echo "Python introuvable. Installe Python 3.10+."
  exit 1
fi
PYTHON="$(command -v python3 2>/dev/null || command -v python)"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm introuvable. Installe Node.js 18+."
  exit 1
fi

if [[ ! -d web/node_modules ]]; then
  echo "→ Installation des deps web (npm install)…"
  (cd web && npm install)
fi

OLLAMA_BASE="${OLLAMA_URL:-http://localhost:11434/api/chat}"
OLLAMA_ORIGIN="$(echo "$OLLAMA_BASE" | sed -E 's#(https?://[^/]+).*#\1#')"
if command -v curl >/dev/null 2>&1; then
  if ! curl -sf -m 2 "$OLLAMA_ORIGIN/api/tags" >/dev/null; then
    echo "⚠ Ollama ne répond pas sur $OLLAMA_ORIGIN — lance 'ollama serve' si besoin."
  else
    echo "✓ Ollama OK ($OLLAMA_ORIGIN)"
  fi
fi

PIDS=()

cleanup() {
  echo ""
  echo "Arrêt des services…"
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ API  http://${API_HOST}:${API_PORT}"
"$PYTHON" -m uvicorn server.app:app --reload --host "$API_HOST" --port "$API_PORT" &
PIDS+=($!)

echo "→ UI   http://${WEB_HOST}:${WEB_PORT}"
(
  cd web
  npm run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
PIDS+=($!)

echo ""
echo "AgentAutonome lancé. Ctrl+C pour tout arrêter."
wait

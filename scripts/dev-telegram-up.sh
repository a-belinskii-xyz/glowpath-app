#!/usr/bin/env bash
# Quick Cloudflare tunnels for local Telegram Mini App + bot webhook.
# Usage:
#   ./scripts/dev-telegram-up.sh        # start tunnels, patch .env, recreate app/bot
#   ./scripts/dev-telegram-up.sh --stop # stop tunnels started by this script
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT}/.local/telegram-tunnels"
BOT_ENV="${ROOT}/backend/.env"
FRONTEND_ENV="${ROOT}/frontend/.env"
BOT_LOG="${STATE_DIR}/bot.log"
FRONTEND_LOG="${STATE_DIR}/frontend.log"
BOT_PID_FILE="${STATE_DIR}/bot.pid"
FRONTEND_PID_FILE="${STATE_DIR}/frontend.pid"
WAIT_SECONDS="${TELEGRAM_TUNNEL_WAIT_SECONDS:-60}"
# ngrok for the bot webhook (Telegram's API cannot resolve trycloudflare from this network).
# cloudflared HTTP/2 for the Mini App (phone WebView).
CLOUDFLARED_PROTOCOL="${CLOUDFLARED_PROTOCOL:-http2}"

read_env_value() {
  local file="$1" key="$2" default="${3:-}"
  if [[ -f "$file" ]]; then
    local line
    line="$(grep -E "^${key}=" "$file" | tail -n1 || true)"
    if [[ -n "$line" ]]; then
      printf '%s' "${line#*=}"
      return 0
    fi
  fi
  printf '%s' "$default"
}

BOT_PORT="$(read_env_value "${ROOT}/.env" TELEGRAM_BOT_PORT 8081)"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

usage() {
  cat <<EOF
Start an ngrok tunnel for the Telegram bot webhook (:${BOT_PORT}) and a Cloudflare
tunnel for the Vite Mini App (:${FRONTEND_PORT}), write the public URLs into
backend/.env (and empty VITE_API_BASE_URL), then recreate app + telegram-bot.

Usage: $(basename "$0") [--stop]

  --stop   Kill tunnels started by this script (does not stop Docker / Vite)

trycloudflare hostnames are not accepted by Telegram setWebhook on this network
(local DNS is hijacked; Bot API returns "Failed to resolve host").
EOF
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

port_open() {
  python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket()
sock.settimeout(0.4)
try:
    sock.connect(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
}

pid_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

stop_pid_file() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "$pid_file" || true)"
  if pid_running "$pid"; then
    kill "$pid" 2>/dev/null || true
    sleep 0.3
    if pid_running "$pid"; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$pid_file"
}

stop_tunnels() {
  mkdir -p "$STATE_DIR"
  stop_pid_file "$BOT_PID_FILE"
  stop_pid_file "$FRONTEND_PID_FILE"
  echo "Stopped Telegram tunnels."
}

set_env_key() {
  python3 - "$1" "$2" "$3" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text().splitlines() if path.exists() else []
prefix = f"{key}="
export_prefix = f"export {prefix}"
found = False
out = []
for line in lines:
    if line.startswith(prefix) or line.startswith(export_prefix):
        if not found:
            out.append(f"{key}={value}")
            found = True
        continue
    out.append(line)
if not found:
    if out and out[-1] != "":
        out.append("")
    out.append(f"{key}={value}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(out) + "\n")
PY
}

merge_cors() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
extra = sys.argv[2].rstrip("/")
text = path.read_text() if path.exists() else ""
current = ""
for line in text.splitlines():
    if line.startswith("CORS_ORIGINS="):
        current = line.split("=", 1)[1]
origins = []
seen = set()
for raw in current.split(","):
    origin = raw.strip().rstrip("/")
    if not origin or origin.endswith(
        (".trycloudflare.com", ".ngrok-free.app", ".ngrok.io", ".loca.lt")
    ):
        continue
    if origin not in seen:
        origins.append(origin)
        seen.add(origin)
for origin in ("http://localhost:5173", "http://127.0.0.1:5173", extra):
    if origin not in seen:
        origins.append(origin)
        seen.add(origin)
# inline set_env_key to keep CORS as one assignment
prefix = "CORS_ORIGINS="
lines = text.splitlines() if text else []
found = False
out = []
value = ",".join(origins)
for line in lines:
    if line.startswith(prefix) or line.startswith("export CORS_ORIGINS="):
        if not found:
            out.append(prefix + value)
            found = True
        continue
    out.append(line)
if not found:
    if out and out[-1] != "":
        out.append("")
    out.append(prefix + value)
path.write_text("\n".join(out) + "\n")
PY
}

wait_for_tunnel_url() {
  local log="$1"
  local label="$2"
  local pid_file="$3"
  local kind="$4"
  local i=0
  local url=""
  local registered=0
  while (( i < WAIT_SECONDS )); do
    if [[ -f "$log" ]]; then
      url="$(grep -oE 'https://[a-zA-Z0-9.-]+\.(trycloudflare\.com|ngrok-free\.app|ngrok\.io)' "$log" | tail -n1 || true)"
      if [[ "$kind" == "ngrok" ]]; then
        if [[ -n "$url" ]]; then
          printf '%s' "$url"
          return 0
        fi
      else
        if grep -q 'Registered tunnel connection' "$log" 2>/dev/null; then
          registered=1
        fi
        if [[ -n "$url" && "$registered" -eq 1 ]]; then
          printf '%s' "$url"
          return 0
        fi
      fi
    fi
    if ! pid_running "$(cat "${pid_file}" 2>/dev/null || true)"; then
      echo "${label} tunnel exited before becoming ready. Last log:" >&2
      tail -n 40 "$log" >&2 || true
      return 1
    fi
    sleep 1
    i=$((i + 1))
  done
  echo "Timed out waiting for ${label} tunnel (${WAIT_SECONDS}s)." >&2
  tail -n 40 "$log" >&2 || true
  return 1
}

start_ngrok_tunnel() {
  local name="$1" port="$2" log="$3" pid_file="$4"
  : >"$log"
  nohup ngrok http "$port" --log=stdout --log-format=json >"$log" 2>&1 &
  echo $! >"$pid_file"
  echo "Started ${name} tunnel (pid $(cat "$pid_file"), ngrok) → http://127.0.0.1:${port}"
}

start_cloudflared_tunnel() {
  local name="$1" target="$2" log="$3" pid_file="$4"
  : >"$log"
  nohup cloudflared tunnel --no-autoupdate --protocol "$CLOUDFLARED_PROTOCOL" \
    --edge-ip-version 4 --url "$target" >"$log" 2>&1 &
  echo $! >"$pid_file"
  echo "Started ${name} tunnel (pid $(cat "$pid_file"), cloudflared ${CLOUDFLARED_PROTOCOL}) → ${target}"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--stop" ]]; then
  stop_tunnels
  exit 0
fi

if [[ -n "${1:-}" ]]; then
  usage >&2
  exit 1
fi

need_cmd ngrok
need_cmd cloudflared
need_cmd docker
need_cmd python3

if [[ ! -f "$BOT_ENV" ]]; then
  echo "Missing ${BOT_ENV}. Copy backend/.env.example first." >&2
  exit 1
fi

mkdir -p "$STATE_DIR"
stop_tunnels >/dev/null
trap 'echo "Failed — stopping tunnels."; stop_tunnels >/dev/null' ERR

echo "Ensuring Docker Compose stack is up…"
docker compose -f "${ROOT}/docker-compose.yml" up -d

if ! port_open "$BOT_PORT"; then
  echo "Nothing is listening on localhost:${BOT_PORT} (telegram-bot). Is Compose up?" >&2
  exit 1
fi
if ! port_open "$FRONTEND_PORT"; then
  echo "Nothing is listening on localhost:${FRONTEND_PORT} (Vite). Start it with: make frontend-dev" >&2
  exit 1
fi

start_ngrok_tunnel "bot" "$BOT_PORT" "$BOT_LOG" "$BOT_PID_FILE"
start_cloudflared_tunnel "frontend" "http://127.0.0.1:${FRONTEND_PORT}" "$FRONTEND_LOG" "$FRONTEND_PID_FILE"

echo "Waiting for public tunnel URLs…"
BOT_URL="$(wait_for_tunnel_url "$BOT_LOG" "bot" "$BOT_PID_FILE" ngrok)"
FRONTEND_URL="$(wait_for_tunnel_url "$FRONTEND_LOG" "frontend" "$FRONTEND_PID_FILE" cloudflared)"
echo "Bot webhook:  ${BOT_URL}"
echo "Mini App:     ${FRONTEND_URL}"

set_env_key "$BOT_ENV" TELEGRAM_WEBHOOK_URL "$BOT_URL"
set_env_key "$BOT_ENV" TELEGRAM_MINI_APP_URL "$FRONTEND_URL"
merge_cors "$BOT_ENV" "$FRONTEND_URL"

if [[ -f "$FRONTEND_ENV" ]]; then
  set_env_key "$FRONTEND_ENV" VITE_API_BASE_URL ""
else
  printf 'VITE_API_BASE_URL=\n' >"$FRONTEND_ENV"
fi

echo "Recreating app and telegram-bot so they load the new .env…"
docker compose -f "${ROOT}/docker-compose.yml" up -d --force-recreate --no-deps app telegram-bot

echo "Waiting for Telegram to accept the webhook…"
webhook_ok=0
for _ in $(seq 1 40); do
  if docker compose -f "${ROOT}/docker-compose.yml" logs --since 2m telegram-bot 2>/dev/null \
    | grep -q 'Telegram webhook registered:'; then
    webhook_ok=1
    break
  fi
  sleep 1
done
if [[ "$webhook_ok" -ne 1 ]]; then
  echo "Telegram webhook did not register. Recent telegram-bot logs:" >&2
  docker compose -f "${ROOT}/docker-compose.yml" logs --tail 40 telegram-bot >&2 || true
  exit 1
fi

echo
echo "Tunnels are running in the background. Stop with: make telegram-down"
echo "BotFather → Menu Button / Main Mini App must be: ${FRONTEND_URL}"
echo "If Vite was already running, restart it so it picks up empty VITE_API_BASE_URL."
echo "Logs: ${BOT_LOG}  ${FRONTEND_LOG}"

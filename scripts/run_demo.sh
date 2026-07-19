#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
api_port=${API_PORT:-8000}
web_port=${WEB_PORT:-3000}

case "$api_port:$web_port" in
  *[!0-9:]*|*:|:*)
    echo "API_PORT and WEB_PORT must be numeric." >&2
    exit 1
    ;;
esac
if [ "$api_port" = "$web_port" ]; then
  echo "API_PORT and WEB_PORT must be different." >&2
  exit 1
fi

if [ ! -x "$repo_root/.venv/bin/python" ]; then
  echo "Missing .venv. Run ./scripts/setup.sh first." >&2
  exit 1
fi
if [ ! -d "$repo_root/frontend/node_modules" ]; then
  echo "Missing frontend dependencies. Run ./scripts/setup.sh first." >&2
  exit 1
fi

log_dir="$repo_root/.cache/logs"
mkdir -p "$log_dir"
stamp=$(date +%Y%m%d-%H%M%S)
api_out="$log_dir/api-$stamp.out.log"
api_err="$log_dir/api-$stamp.err.log"
web_out="$log_dir/web-$stamp.out.log"
web_err="$log_dir/web-$stamp.err.log"
api_pid=
web_pid=

cleanup() {
  if [ -n "$api_pid" ]; then kill "$api_pid" 2>/dev/null || true; fi
  if [ -n "$web_pid" ]; then kill "$web_pid" 2>/dev/null || true; fi
  if [ -n "$api_pid" ]; then wait "$api_pid" 2>/dev/null || true; fi
  if [ -n "$web_pid" ]; then wait "$web_pid" 2>/dev/null || true; fi
}
on_signal() {
  trap - EXIT INT TERM
  cleanup
  exit 130
}
trap cleanup EXIT
trap on_signal INT TERM

(cd "$repo_root/backend" && "$repo_root/.venv/bin/python" -m uvicorn causalpilot.main:app --host 127.0.0.1 --port "$api_port") >"$api_out" 2>"$api_err" &
api_pid=$!
(cd "$repo_root/frontend" && npm run dev -- -p "$web_port") >"$web_out" 2>"$web_err" &
web_pid=$!

wait_for_service() {
  name=$1
  url=$2
  pid=$3
  error_log=$4
  attempt=1
  while [ "$attempt" -le 60 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "$name exited during startup. Last error lines:" >&2
      tail -n 20 "$error_log" >&2 || true
      exit 1
    fi
    if "$repo_root/.venv/bin/python" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1).read(1)' "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done
  echo "$name did not become ready at $url within 60 seconds. See $error_log" >&2
  exit 1
}

wait_for_service "API" "http://127.0.0.1:$api_port/health" "$api_pid" "$api_err"
wait_for_service "Web app" "http://127.0.0.1:$web_port" "$web_pid" "$web_err"

echo "CausalPilot API: http://127.0.0.1:$api_port/docs"
echo "Control room:   http://127.0.0.1:$web_port"
echo "Service logs:   $log_dir"
echo "Press Ctrl+C to stop both services."

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done

echo "A service exited unexpectedly. Inspect $log_dir" >&2
exit 1

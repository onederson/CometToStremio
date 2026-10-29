#!/system/bin/sh
# Comet - watchdog (/data/comet/watchdog.sh)
# Sobe o Comet e o Caddy (dentro do chroot Debian) se nao estiverem rodando e verifica a cada 30 s.

BASE=/data/comet
LOG=$BASE/watchdog.log
OUT=$BASE/comet.log

# Evita dois watchdogs ao mesmo tempo
PIDFILE=$BASE/watchdog.pid
OLDPID=$(cat "$PIDFILE" 2>/dev/null)
if [ -n "$OLDPID" ] && grep -q comet/watchdog.sh "/proc/$OLDPID/cmdline" 2>/dev/null; then
  exit 0
fi
echo $$ > "$PIDFILE"

log() {
  echo "$(date '+%F %T') $1" >> "$LOG"
  if [ "$(wc -l < "$LOG")" -gt 1000 ]; then
    tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  fi
}

start_comet() {
  nohup /system/bin/sh "$BASE/chroot.sh" -c 'cd /opt/comet && exec /opt/comet/.venv/bin/python -m comet.main' \
    >> "$OUT" 2>&1 < /dev/null &
}

# Caddy (HTTPS a71comet.duckdns.org -> 127.0.0.1:8000). O chroot.sh limpa o ambiente (env -i),
# entao o token do DuckDNS e carregado dentro do chroot.
start_caddy() {
  nohup /system/bin/sh "$BASE/chroot.sh" -c 'DUCKDNS_TOKEN=$(cat /etc/caddy/duckdns.token) exec /usr/local/bin/caddy run --config /etc/caddy/Caddyfile' \
    >> "$CADDY_OUT" 2>&1 < /dev/null &
}

# Limita um log a ~5 MB (arquivo aberto em modo append, truncar e seguro)
cap_log() {
  if [ "$(stat -c %s "$1" 2>/dev/null || echo 0)" -gt 5242880 ]; then
    : > "$1"
    log "$(basename "$1") truncado"
  fi
}

CADDY_OUT=$BASE/caddy.log

log "watchdog iniciado (pid $$)"
while true; do
  if ! pgrep -f 'python -m comet.main' > /dev/null; then
    log "Comet nao esta rodando, iniciando"
    start_comet
  fi
  if ! pgrep -f 'caddy run --config /etc/caddy/Caddyfile' > /dev/null; then
    log "Caddy nao esta rodando, iniciando"
    start_caddy
  fi
  cap_log "$OUT"
  cap_log "$CADDY_OUT"
  sleep 30
done


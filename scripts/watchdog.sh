#!/system/bin/sh
# Comet - watchdog (/data/comet/watchdog.sh)
# Sobe o StremThru, o Prowlarr, o Comet, o Caddy e o FlareSolverr (dentro do chroot Debian) se nao estiverem rodando e verifica a cada 30 s.

BASE=/data/comet
LOG=$BASE/watchdog.log
OUT=$BASE/comet.log
CADDY_OUT=$BASE/caddy.log
STREMTHRU_OUT=$BASE/stremthru.log
PROWLARR_OUT=$BASE/prowlarr.log
FLARESOLVERR_OUT=$BASE/flaresolverr.log

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

set_oom() {
  _p="$1"
  _val="$2"
  [ -z "$_p" ] && return
  [ -d "/proc/$_p" ] || return
  _cur=$(cat "/proc/$_p/oom_score_adj" 2>/dev/null)
  if [ "$_cur" != "$_val" ]; then
    echo "$_val" > "/proc/$_p/oom_score_adj" 2>/dev/null || true
  fi
}

protect() {
  set_oom $$ -1000

  for p in $(pgrep -f '^/usr/local/bin/stremthru$') \
           $(pgrep -f '^/opt/prowlarr/Prowlarr -nobrowser -data=/var/lib/prowlarr$') \
           $(pgrep -f 'caddy run --config /etc/caddy/Caddyfile') \
           $(pgrep -f '/data/adguard/AdGuardHome/AdGuardHome') \
           $(pgrep -f '/data/adguard/watchdog.sh'); do
    set_oom "$p" -1000
  done

  for p in $(pgrep -f 'python -m comet.main') \
           $(pgrep -f '/opt/comet/.venv') \
           $(pgrep -f 'multiprocessing.forkserver'); do
    set_oom "$p" -1000
    for child in $(pgrep -P "$p" 2>/dev/null); do
      set_oom "$child" -1000
      for gchild in $(pgrep -P "$child" 2>/dev/null); do
        set_oom "$gchild" -1000
      done
    done
  done

  for p in $(pgrep -f 'flaresolverr.py') \
           $(pgrep -f 'chromium'); do
    set_oom "$p" 200
    for child in $(pgrep -P "$p" 2>/dev/null); do
      set_oom "$child" 200
    done
  done
}

LAST_KILL=0
FREE_MEM_THRESHOLD=600

free_mem() {
  avail_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
  [ -z "$avail_kb" ] && return
  avail_mb=$((avail_kb / 1024))
  if [ "$avail_mb" -lt "$FREE_MEM_THRESHOLD" ]; then
    now=$(date +%s)
    if [ $((now - LAST_KILL)) -ge 300 ]; then
      log "memoria baixa (${avail_mb} MB), am kill-all"
      am kill-all
      LAST_KILL=$now
    fi
  fi
}

check_flaresolverr_mem() {
  _fs_pids=$( (pgrep -f 'flaresolverr.py'; pgrep -f 'chromium') | sort -u )
  [ -z "$_fs_pids" ] && return
  # PSS e nao RSS: os processos do Chromium compartilham memoria e a soma de RSS
  # conta o mesmo bloco varias vezes (pico real ~750 MB por pagina resolvida).
  _pss_kb=0
  for _pid in $_fs_pids; do
    _val=$(awk '/^Pss:/ {print $2}' "/proc/$_pid/smaps_rollup" 2>/dev/null)
    if [ -n "$_val" ]; then
      _pss_kb=$((_pss_kb + _val))
    fi
  done
  _pss_mb=$((_pss_kb / 1024))
  if [ "$_pss_mb" -gt 1200 ]; then
    log "FlareSolverr excedeu limite de memoria (${_pss_mb} MB > 1200 MB), matando"
    for _pid in $_fs_pids; do
      kill -9 "$_pid" 2>/dev/null || true
    done
  fi
}

start_comet() {
  nohup /system/bin/sh "$BASE/chroot.sh" -c 'cd /opt/comet && exec /opt/comet/.venv/bin/python -m comet.main' \
    >> "$OUT" 2>&1 < /dev/null &
  COMET_JUST_STARTED=1
  COMET_START_TIME=$(date +%s)
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

run_smoke() {
  if [ -f /data/debian/opt/comet/data/smoke.disable ]; then
    return
  fi
  touch /data/debian/var/tmp/comet.log
  grep -q " /data/debian/var/tmp/comet.log " /proc/mounts || mount -o bind "$OUT" /data/debian/var/tmp/comet.log 2>/dev/null || true
  _offset=$(stat -c %s "$OUT" 2>/dev/null || echo 0)
  _out=$(timeout 150 /system/bin/sh "$BASE/chroot.sh" -c "/opt/comet/.venv/bin/python /opt/comet-tools/smoke.py --log-file /var/tmp/comet.log --log-offset $_offset" 2>&1)
  _code=$?
  tail -c +$((_offset + 1)) "$OUT" > /data/debian/var/tmp/smoke_log.txt 2>/dev/null || true
  if echo "$_out" | grep -q "RESTAURADO"; then
    log "RESTAURADO"
  fi
  if [ "$_code" -eq 0 ]; then
    log "SMOKE OK"
  else
    _fail=$(echo "$_out" | grep '^SMOKE FALHOU' | tail -n 1)
    if [ -n "$_fail" ]; then
      log "$_fail"
    else
      log "SMOKE FALHOU"
    fi
  fi
}

# StremThru local (127.0.0.1:8080): ponte Comet -> Real-Debrid. A instancia publica
# falhava ao adicionar magnets nao cacheados ("provider is currently unavailable").
start_stremthru() {
  nohup /system/bin/sh "$BASE/chroot.sh" -c 'cd /var/lib/stremthru && STREMTHRU_ENV=prod STREMTHRU_LISTEN_ADDR=127.0.0.1:8080 STREMTHRU_PORT=8080 STREMTHRU_BASE_URL=https://a71comet.duckdns.org:8443 STREMTHRU_DATA_DIR=/var/lib/stremthru STREMTHRU_DATABASE_URI="sqlite:///var/lib/stremthru/stremthru.db?max_conns=2" STREMTHRU_STORE_TUNNEL="*:false" STREMTHRU_FEATURE=torz,stremio_store exec /usr/local/bin/stremthru' \
    >> "$STREMTHRU_OUT" 2>&1 < /dev/null &
}

# Prowlarr local (127.0.0.1:9696): indexadores BR (BeTor) e gerais para o Comet.
start_prowlarr() {
  nohup /system/bin/sh "$BASE/chroot.sh" -c 'cd /opt/prowlarr && DOTNET_EnableDiagnostics=0 exec /opt/prowlarr/Prowlarr -nobrowser -data=/var/lib/prowlarr' \
    >> "$PROWLARR_OUT" 2>&1 < /dev/null &
}

start_flaresolverr() {
  nohup /system/bin/sh "$BASE/chroot.sh" -c 'cd /opt/flaresolverr && HOST=127.0.0.1 PORT=8191 LOG_LEVEL=info HEADLESS=true TZ=America/Sao_Paulo exec /opt/flaresolverr/.venv/bin/python src/flaresolverr.py' \
    >> "$FLARESOLVERR_OUT" 2>&1 < /dev/null &
}

log "watchdog iniciado (pid $$)"
LAST_SMOKE_RUN=$(date +%s)
COMET_JUST_STARTED=1
COMET_START_TIME=$(date +%s)

while true; do
  protect
  free_mem
  check_flaresolverr_mem
  if ! pgrep -f '^/usr/local/bin/stremthru$' > /dev/null; then
    log "StremThru nao esta rodando, iniciando"
    start_stremthru
  fi
  if ! pgrep -f '^/opt/prowlarr/Prowlarr -nobrowser -data=/var/lib/prowlarr$' > /dev/null; then
    log "Prowlarr nao esta rodando, iniciando"
    start_prowlarr
  fi
  if ! pgrep -f 'python -m comet.main' > /dev/null; then
    log "Comet nao esta rodando, iniciando"
    start_comet
  fi
  if ! pgrep -f 'caddy run --config /etc/caddy/Caddyfile' > /dev/null; then
    log "Caddy nao esta rodando, iniciando"
    start_caddy
  fi
  if ! pgrep -f 'flaresolverr.py' > /dev/null; then
    log "FlareSolverr nao esta rodando, iniciando"
    start_flaresolverr
  fi
  protect

  now=$(date +%s)
  if [ "$COMET_JUST_STARTED" = "1" ] && [ $((now - COMET_START_TIME)) -ge 180 ]; then
    COMET_JUST_STARTED=0
    LAST_SMOKE_RUN=$now
    run_smoke
  elif [ $((now - LAST_SMOKE_RUN)) -ge 3600 ]; then
    LAST_SMOKE_RUN=$now
    run_smoke
  fi

  cap_log "$OUT"
  cap_log "$CADDY_OUT"
  cap_log "$STREMTHRU_OUT"
  cap_log "$PROWLARR_OUT"
  cap_log "$FLARESOLVERR_OUT"
  sleep 30
done

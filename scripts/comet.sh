#!/system/bin/sh
# Comet (addon Stremio) - script de boot (Magisk /data/adb/service.d/comet.sh)
# Espera o AdGuard subir (ele ja aplica wakelock/Doze/phantom) e inicia o watchdog do Comet.
sleep 45
nohup /system/bin/sh /data/comet/watchdog.sh > /dev/null 2>&1 < /dev/null &


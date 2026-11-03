#!/system/bin/sh
# Instala o rootfs Debian e os scripts do Comet no A71 (rodar como root).
# Pre-requisito: adb push de rootfs.tar.xz, chroot.sh, watchdog.sh e setup_comet.sh para /data/local/tmp/
set -e
BB=/data/adb/magisk/busybox
ROOT=/data/debian
T=/data/local/tmp

if [ ! -x "$ROOT/bin/bash" ]; then
  mkdir -p "$ROOT"
  echo "Extraindo rootfs em $ROOT ..."
  $BB xz -dc "$T/rootfs.tar.xz" | $BB tar -x -C "$ROOT"
  echo "rootfs extraido"
fi

# DNS: AdGuard local + Quad9 de reserva
rm -f "$ROOT/etc/resolv.conf"
# Quad9 primeiro: em 03/11/2026 o 1.1.1.1 ficou lento/sem resposta nesta rede e derrubou os catálogos do TMDB
printf 'nameserver 9.9.9.9\nnameserver 8.8.8.8\nnameserver 1.1.1.1\noptions timeout:2 attempts:2\n' > "$ROOT/etc/resolv.conf"
printf '127.0.0.1 localhost\n::1 localhost\n127.0.1.1 a71 a71.lan\n' > "$ROOT/etc/hosts"
echo a71 > "$ROOT/etc/hostname"

mkdir -p /data/comet
cp "$T/chroot.sh" "$T/watchdog.sh" /data/comet/
chmod 755 /data/comet/*.sh
cp "$T/setup_comet.sh" "$ROOT/root/setup_comet.sh"
chmod 755 "$ROOT/root/setup_comet.sh"
echo "OK"


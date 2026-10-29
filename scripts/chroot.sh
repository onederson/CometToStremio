#!/system/bin/sh
# Comet - helper do chroot Debian (/data/comet/chroot.sh)
# Monta /proc, /sys, /dev, /dev/pts e /dev/shm no rootfs Debian e entra no chroot.
#   sh /data/comet/chroot.sh                -> shell interativo (bash)
#   sh /data/comet/chroot.sh -c 'comando'   -> roda um comando
#   sh /data/comet/chroot.sh /root/x.sh     -> roda um script de dentro do chroot

ROOT=/data/debian

is_mounted() { grep -q " $1 " /proc/mounts; }

mkdir -p "$ROOT/proc" "$ROOT/sys" "$ROOT/dev" "$ROOT/tmp"
is_mounted "$ROOT/proc"    || mount -t proc proc "$ROOT/proc"
is_mounted "$ROOT/sys"     || mount -t sysfs sysfs "$ROOT/sys"
is_mounted "$ROOT/dev"     || mount -o bind /dev "$ROOT/dev"
is_mounted "$ROOT/dev/pts" || mount -o bind /dev/pts "$ROOT/dev/pts"
# Python (multiprocessing/semaforos) precisa de /dev/shm, que nao existe no Android
[ -d /dev/shm ] || mkdir -p /dev/shm
is_mounted "$ROOT/dev/shm" || mount -t tmpfs -o size=128m,mode=1777 tmpfs "$ROOT/dev/shm"
chmod 1777 "$ROOT/tmp"

exec chroot "$ROOT" /usr/bin/env -i \
  HOME=/root TERM=xterm-256color LANG=C.UTF-8 TZ=America/Sao_Paulo \
  PATH=/root/.local/bin:/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /bin/bash "$@"


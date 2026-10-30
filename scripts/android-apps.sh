#!/system/bin/sh
# Gerenciamento de apps secundarios do Android no A71

PACKAGES="
io.chaldeaprjkt.gamespace
org.omnirom.omnijaws
com.android.settings.intelligence
com.android.emergency
"

case "$1" in
  disable)
    for pkg in $PACKAGES; do
      if pm list packages | grep -q "^package:$pkg$"; then
        pm disable-user --user 0 "$pkg"
      fi
    done
    ;;
  enable)
    for pkg in $PACKAGES; do
      if pm list packages | grep -q "^package:$pkg$"; then
        pm enable "$pkg"
      fi
    done
    ;;
  *)
    echo "Uso: $0 {disable|enable}"
    exit 1
    ;;
esac

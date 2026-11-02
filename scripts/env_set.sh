# uso: sh cc_env_add.sh CHAVE  (o valor vem de /data/local/tmp/cc_val.txt)
E=/data/debian/opt/comet/.env
K="$1"
V="$(cat /data/local/tmp/cc_val.txt)"
rm -f /data/local/tmp/cc_val.txt
before=$(grep -c . "$E")
grep -v "^$K=" "$E" > /data/local/tmp/cc_env.new
printf '%s=%s\n' "$K" "$V" >> /data/local/tmp/cc_env.new
after=$(grep -c . /data/local/tmp/cc_env.new)
had=$(grep -c "^$K=" "$E")
if [ "$after" -eq $((before - had + 1)) ]; then
  cat /data/local/tmp/cc_env.new > "$E"; chmod 600 "$E"; echo "ok: $K gravada ($before -> $after linhas)"
else
  echo "ABORTADO: contagem inesperada ($before -> $after)"
fi
rm -f /data/local/tmp/cc_env.new

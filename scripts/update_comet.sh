#!/bin/sh
# Atualiza o Comet do A71 para a versão nova do projeto original (g0ldyy/comet)
# mantendo as nossas modificações. Roda DENTRO do chroot.
#   sh update_comet.sh check            -> só diz se há versão nova
#   sh update_comet.sh prepare [REF]     -> guarda estado, atualiza e reaplica as modificações (sem reiniciar)
#   sh update_comet.sh rollback          -> volta exatamente ao estado guardado
#   sh update_comet.sh finish            -> apaga o estado guardado (depois dos testes passarem)
set -u
cd /opt/comet || exit 1
STATE=/opt/comet/data/update_state
REF="${2:-origin/main}"

save_state() {
  mkdir -p "$STATE"
  git rev-parse HEAD > "$STATE/old_head"
  git add -N . 2>/dev/null
  git diff --binary HEAD > "$STATE/ours.patch"
  git reset -q 2>/dev/null
  cp pyproject.toml "$STATE/pyproject.old" 2>/dev/null
  echo "estado guardado: $(cut -c1-8 "$STATE/old_head"), patch $(wc -c < "$STATE/ours.patch") bytes"
}

restore_state() {
  [ -f "$STATE/old_head" ] || { echo "sem estado guardado"; return 1; }
  git merge --abort 2>/dev/null
  git reset -q --hard "$(cat "$STATE/old_head")"
  git clean -q -fd comet
  git apply --binary "$STATE/ours.patch" && echo "ROLLBACK OK: voltou para $(cut -c1-8 "$STATE/old_head")"
}

case "${1:-check}" in
  check)
    timeout 90 git fetch -q origin || { echo "falha no fetch"; exit 2; }
    n=$(git rev-list --count HEAD.."$REF")
    echo "commits novos em $REF: $n"
    [ "$n" -gt 0 ] && git log --format="  %h %ad %s" --date=short HEAD.."$REF" | head -20
    exit 0 ;;
  prepare)
    timeout 90 git fetch -q origin || { echo "falha no fetch"; exit 2; }
    n=$(git rev-list --count HEAD.."$REF")
    if [ "$n" -eq 0 ]; then echo "JA_ATUALIZADO"; exit 0; fi
    save_state
    git stash push -q -u -m comet-update || { echo "falha ao guardar modificações"; exit 3; }
    if ! git merge -q --ff-only "$REF"; then
      echo "CONFLITO: o original divergiu (não é fast-forward)"; git stash pop -q; restore_state; exit 4
    fi
    if ! git stash pop -q; then
      echo "CONFLITO ao reaplicar as nossas modificações:"; git diff --name-only --diff-filter=U | sed 's/^/  /'
      git checkout -q -- . ; git stash drop -q; restore_state; exit 5
    fi
    if ! cmp -s pyproject.toml "$STATE/pyproject.old"; then
      echo "pyproject mudou: atualizando dependências"
      if ! timeout 280 .venv/bin/python -m pip install -q -e . ; then
        echo "falha nas dependências"; restore_state; exit 6
      fi
    fi
    find comet -name "*.py" -newer "$STATE/old_head" | head -400 | xargs -r .venv/bin/python -m py_compile || { echo "erro de sintaxe"; restore_state; exit 7; }
    echo "PREPARADO: $(git rev-parse --short HEAD) com as nossas modificações; falta reiniciar e testar"
    exit 0 ;;
  rollback) restore_state; exit $? ;;
  finish) rm -rf "$STATE"; echo "estado de atualização apagado"; exit 0 ;;
  *) echo "uso: check | prepare [REF] | rollback | finish"; exit 1 ;;
esac

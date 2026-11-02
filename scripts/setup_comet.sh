#!/bin/bash
# Comet - instalacao DENTRO do chroot Debian (copiado para /root/setup_comet.sh)
# Rodar com: su -c 'sh /data/comet/chroot.sh /root/setup_comet.sh'
# Idempotente: pode ser executado de novo se falhar no meio.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Android "paranoid network": so processos do grupo inet (3003) ou root abrem sockets.
# O apt baixa como usuario _apt, entao forcamos o sandbox do apt a usar root.
echo 'APT::Sandbox::User "root";' > /etc/apt/apt.conf.d/01-android-sandbox

echo "== [1/5] apt =="
apt-get update
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-dev git curl ca-certificates \
  gcc g++ make libc6-dev pkg-config libmimalloc3 tzdata procps

echo "== [2/5] rust (rustup, necessario para compilar o torrent-parse-rank) =="
if [ ! -x /root/.cargo/bin/cargo ]; then
  curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
. /root/.cargo/env
rustc --version

echo "== [3/5] uv =="
if [ ! -x /root/.local/bin/uv ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH=/root/.local/bin:$PATH
uv --version

echo "== [4/5] codigo do Comet =="
cd /opt
if [ ! -d comet/.git ]; then
  git clone --depth 1 https://github.com/g0ldyy/comet.git
else
  git -C comet pull --ff-only
fi
cd /opt/comet
git log -1 --format='commit %h (%cd)'

echo "== [5/5] dependencias Python (uv sync) =="
export CARGO_BUILD_JOBS=6
export UV_PYTHON_PREFERENCE=only-system
uv sync --frozen --no-install-project --no-dev
# Pillow: capas montadas dos catalogos (Top 10 e capa deitada com logo), comet/services/artwork.py
uv pip install --python .venv/bin/python pillow==11.3.0
# uvloop + httptools: motor de rede e leitor HTTP rápidos (o uvicorn usa sozinho se estiverem instalados)
uv pip install --python .venv/bin/python uvloop httptools

mkdir -p /opt/comet/data
echo "== OK: Comet instalado em /opt/comet =="


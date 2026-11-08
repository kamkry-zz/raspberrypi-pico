#!/usr/bin/env bash
# Build MicroPython v1.23.0 for RPI_PICO_W with the dashboard frozen in.
#
#   firmware/build.sh            # -> firmware/out/firmware-dashboard.uf2
#
# Runs in Docker (Debian bookworm, gcc-arm-none-eabi); nothing is installed on
# the host.  The MicroPython checkout and submodules are cached in
# firmware/.cache (gitignored, ~1 GB) so rebuilds take about a minute.
set -euo pipefail
cd "$(dirname "$0")/.."

MPY_TAG=v1.23.0
BOARD=RPI_PICO_W
IMAGE=pico-mpy-build:bookworm
mkdir -p firmware/.cache firmware/out

docker build -q -t "$IMAGE" - <<'EOF' >/dev/null
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      git make cmake python3 build-essential ca-certificates \
      gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib \
    && rm -rf /var/lib/apt/lists/*
EOF

docker run --rm \
  -v "$PWD:/src:ro" \
  -v "$PWD/firmware/.cache:/cache" \
  -v "$PWD/firmware/out:/out" \
  "$IMAGE" bash -euo pipefail -c "
    cd /cache
    if [ ! -d micropython ]; then
      git clone --quiet --depth 1 --branch $MPY_TAG https://github.com/micropython/micropython.git
    fi
    cd micropython
    test \"\$(git describe --tags)\" = $MPY_TAG
    make -s -C mpy-cross -j\$(nproc)
    make -s -C ports/rp2 BOARD=$BOARD submodules
    make -C ports/rp2 BOARD=$BOARD FROZEN_MANIFEST=/src/firmware/manifest.py -j\$(nproc) >/tmp/build.log 2>&1 \
      || { tail -40 /tmp/build.log; exit 1; }
    grep -E 'FLASH|RAM' /tmp/build.log | tail -4 || true
    cp ports/rp2/build-$BOARD/firmware.uf2 /out/firmware-dashboard.uf2
  "

sha=$(shasum -a 256 firmware/out/firmware-dashboard.uf2 | cut -c1-16)
echo "firmware/out/firmware-dashboard.uf2 ($(wc -c < firmware/out/firmware-dashboard.uf2) bytes, sha256 $sha...)"

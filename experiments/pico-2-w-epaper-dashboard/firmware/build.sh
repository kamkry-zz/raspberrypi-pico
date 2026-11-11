#!/usr/bin/env bash
# Build MicroPython with the dashboard frozen in.  Default: v1.29.0 for the
# Pico 2 W (RP2350).  The old Pico W build is still reproducible:
#
#   firmware/build.sh                                   # Pico 2 W (default)
#   MPY_TAG=v1.23.0 BOARD=RPI_PICO_W firmware/build.sh  # old Pico W
#   -> firmware/out/firmware-dashboard-<BOARD>.uf2
#
# Runs in Docker (Debian bookworm, gcc-arm-none-eabi); nothing is installed on
# the host.  The MicroPython checkout and submodules are cached per tag in
# firmware/.cache/<tag> (gitignored, ~1 GB each) so rebuilds take a minute.
set -euo pipefail
cd "$(dirname "$0")/.."

MPY_TAG=${MPY_TAG:-v1.29.0}
BOARD=${BOARD:-RPI_PICO2_W}
IMAGE=pico-mpy-build:bookworm
OUT=firmware/out/firmware-dashboard-$BOARD.uf2
mkdir -p "firmware/.cache/$MPY_TAG" firmware/out

docker build -q -t "$IMAGE" - <<'DOCKERFILE' >/dev/null
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      git make cmake python3 build-essential ca-certificates \
      gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib \
    && rm -rf /var/lib/apt/lists/*
DOCKERFILE

docker run --rm \
  -v "$PWD:/src:ro" \
  -v "$PWD/firmware/.cache/$MPY_TAG:/cache" \
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
    cp ports/rp2/build-$BOARD/firmware.uf2 /out/$(basename "$OUT")
  "

sha=$(shasum -a 256 "$OUT" | cut -c1-16)
echo "$OUT ($(wc -c < "$OUT") bytes, sha256 $sha...)"

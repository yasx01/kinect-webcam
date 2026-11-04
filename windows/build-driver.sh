#!/usr/bin/env bash
# Build a library and our Kinect-only helper; never ship or run Zadig.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/build-tools/windows-driver"
OUT="$ROOT/windows/native"
mkdir -p "$WORK" "$OUT/licenses"
git clone --no-checkout https://github.com/pbatard/libwdi.git "$WORK/libwdi"
git -C "$WORK/libwdi" checkout --detach 9b23b82a2dd1cbffc16d46c212f92c6bf8c0c602
for kind in bin src; do
    curl -fsSL --retry 3 "https://downloads.sourceforge.net/project/libusbk/libusbK-release/3.1.0.0/libusbK-3.1.0.0-$kind.7z" -o "$WORK/$kind.7z"
done
printf '%s  %s\n' 38605d8d5a86f408a4b7bec60f6d4a096050eee72f89a63a8d5be125252d3fe7 "$WORK/bin.7z" e10210802d234d2ba3ad233089bb4e94a3b9e1ec5d38fc887868d3c7a6e7d477 "$WORK/src.7z" | sha256sum -c -
"/c/Program Files/7-Zip/7z.exe" x -y "$(cygpath -w "$WORK/bin.7z")" "-o$(cygpath -w "$WORK/binaries")" > /dev/null
"/c/Program Files/7-Zip/7z.exe" x -y "$(cygpath -w "$WORK/src.7z")" "-o$(cygpath -w "$WORK/source")" > /dev/null
DRIVERS="$WORK/binaries/libusbK-3.1.0.0-bin/bin"
# libusbK redistributes KMDF 1.9 with a leading zero in its file name.
sed -i 's/WdfCoInstaller" STR(WDF_VER)/WdfCoInstaller0" STR(WDF_VER)/g' "$WORK/libwdi/libwdi/embedder_files.h"
(
    cd "$WORK/libwdi"
    ./bootstrap.sh
    ./configure --host=x86_64-w64-mingw32 --disable-32bit --disable-examples-build --disable-debug \
        --with-libusbk="$(cygpath -m "$DRIVERS")" --with-wdfver=1009
    make -j2
)
cp "$WORK/libwdi/libwdi/.libs/libwdi.dll" "$OUT/libwdi.dll"
gcc -O2 -Wall -Wextra -municode -I"$WORK/libwdi/libwdi" "$ROOT/windows/kinect-driver.c" \
    -L"$WORK/libwdi/libwdi/.libs" -lwdi -lshell32 -lole32 -luuid -o "$OUT/kinect-driver.exe"
"$OUT/kinect-driver.exe" --self-test
cp "$WORK/libwdi/COPYING" "$OUT/licenses/libwdi-GPL3.txt"
cp "$WORK/libwdi/COPYING-LGPL" "$OUT/licenses/libwdi-LGPL3.txt"
cp -R "$WORK/source/libusbK-3.1.0.0-src/license" "$OUT/licenses/libusbK"
git -C "$WORK/libwdi" archive --format=zip --output="$(cygpath -m "$OUT/licenses/libwdi-source.zip")" HEAD
git -C "$WORK/libwdi" diff > "$OUT/licenses/libwdi-build.patch"
cp "$WORK/src.7z" "$OUT/licenses/libusbK-source.7z"
cp "$ROOT/windows/build-driver.sh" "$OUT/licenses/build-driver.sh"
printf '%s\n' 'libwdi v1.5.1 commit 9b23b82a2dd1cbffc16d46c212f92c6bf8c0c602; libusbK 3.1.0.0; signed libusbK and KMDF runtime redistributables only, no Microsoft SDK/firmware.' >> "$OUT/ORIGIN.txt"

#!/usr/bin/env bash
# Runs only in the disposable GitHub Windows runner's UCRT64 environment.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/build-tools/windows-native"
PREFIX="${MINGW_PREFIX:-/ucrt64}"
OUT="$ROOT/windows/native"
mkdir -p "$WORK" "$OUT/licenses"
git clone --no-checkout https://github.com/OpenKinect/libfreenect.git "$WORK/libfreenect"
git -C "$WORK/libfreenect" checkout --detach 09a1f098040d00e6070c18174904547ec31d2774
cmake -S "$WORK/libfreenect" -B "$WORK/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_REDIST_PACKAGE=ON -DBUILD_EXAMPLES=OFF \
  -DBUILD_FAKENECT=OFF -DBUILD_CPP=OFF -DBUILD_C_SYNC=ON \
  -DLIBUSB_1_INCLUDE_DIR="$PREFIX/include/libusb-1.0" \
  -DLIBUSB_1_LIBRARY="$PREFIX/lib/libusb-1.0.dll.a" \
  -DTHREADS_PTHREADS_INCLUDE_DIR="$PREFIX/include" \
  -DTHREADS_PTHREADS_WIN32_LIBRARY="$PREFIX/lib/libwinpthread.dll.a"
cmake --build "$WORK/build" --parallel 2
find "$WORK/build" -name '*freenect*.dll' -exec cp '{}' "$OUT/" \;
for name in libusb-1.0.dll libwinpthread-1.dll libgcc_s_seh-1.dll; do
  cp "$PREFIX/bin/$name" "$OUT/"
done
# Windows port: bounded USB transfers; missing USB device must never return success.
sed -e 's/\&transferred, 0)/\&transferred, 5000)/g' \
    -e 's/ret = -errno;/ret = LIBUSB_ERROR_NO_DEVICE;/' \
    "$ROOT/v15/vendor/kinect-audio-setup/kinect_upload_fw.c" > "$WORK/kinect_upload_fw.c"
gcc -O2 -Wall -I"$ROOT/windows/compat" -I$PREFIX/include/libusb-1.0 \
    "$WORK/kinect_upload_fw.c" -L$PREFIX/lib -lusb-1.0 -o "$OUT/kinect_upload_fw.exe"
cp "$WORK/libfreenect/APACHE20" "$OUT/licenses/libfreenect-APACHE20.txt"
cp "$WORK/libfreenect/GPL2" "$OUT/licenses/libfreenect-GPL2.txt"
cp "$WORK/libfreenect/CONTRIB" "$OUT/licenses/libfreenect-CONTRIB.txt"
cp "$ROOT/v15/licenses/kinect_upload_fw-BSD-2-Clause.txt" "$OUT/licenses/"
for folder in $PREFIX/share/licenses/libusb* $PREFIX/share/licenses/winpthreads* $PREFIX/share/licenses/gcc*; do
  if [ -d "$folder" ]; then cp -R "$folder" "$OUT/licenses/"; fi
done
printf '%s\n' 'libfreenect v0.7.5 commit 09a1f098040d00e6070c18174904547ec31d2774' > "$OUT/ORIGIN.txt"

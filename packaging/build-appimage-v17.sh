#!/usr/bin/env bash
# Fedora x86_64 build; no system install. Explicit allowlist; no MSI/SDK copying.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/v17"
TOOL="$ROOT/build-tools/appimagetool-1.9.1-x86_64.AppImage"
RUNTIME="$ROOT/build-tools/runtime-20251108-x86_64"
mkdir -p "$ROOT/dist"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
APPDIR="$WORK/KinectWebcam.AppDir"
mkdir -p "$APPDIR/usr/bin/payload" "$APPDIR/usr/bin/licenses" "$APPDIR/usr/bin/vendor/kinect-audio-setup"
# Compile from the vendored, BSD-licensed C source; never copy the installed binary.
read -r -a USB_FLAGS <<< "$(pkg-config --cflags --libs libusb-1.0)"
cc -O2 -Wall -Wextra "$SRC/vendor/kinect-audio-setup/kinect_upload_fw.c" \
    -o "$WORK/kinect_upload_fw" "${USB_FLAGS[@]}"
install -m 755 "$WORK/kinect_upload_fw" "$APPDIR/usr/bin/payload/kinect_upload_fw"
FILES=(kinect_facecam_process_v17.py kinect_facecam_media_v17.py kinect-facecam-firefox-permission-v17.py kinect-facecam-gui-v17.py kinect-facecam-setup-v17.py
       kinect-facecam-bridge-v17.py kinect-facecam-bridge-pipewire-v17.py
       kinect-facecam-start-v17 kinect-facecam-stop-v17
       kinect-facecam-pw-start-v17 kinect-facecam-pw-stop-v17 kinect-facecam-bootstrap-v17)
for name in "${FILES[@]}"; do install -m 755 "$SRC/$name" "$APPDIR/usr/bin/$name"; done
install -m 644 "$SRC/kinect-facecam-icon-v17.png" "$APPDIR/usr/bin/kinect-facecam-icon-v17.png"
install -m 644 "$SRC/licenses/"*.txt "$APPDIR/usr/bin/licenses/"
install -m 644 "$SRC/vendor/kinect-audio-setup/"* "$APPDIR/usr/bin/vendor/kinect-audio-setup/"
install -m 755 "$ROOT/packaging/v17/AppRun" "$APPDIR/AppRun"
install -m 644 "$ROOT/packaging/v17/kinect-facecam.desktop" "$APPDIR/kinect-facecam.desktop"
install -m 644 "$SRC/kinect-facecam-icon-v17.png" "$APPDIR/kinect-facecam.png"
ln -s kinect-facecam.png "$APPDIR/.DirIcon"
python3 -B - "$APPDIR/usr/bin/payload" <<'PYCODE'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1])
manifest={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ('kinect_upload_fw',)}
(p/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PYCODE
if find "$APPDIR" \( -iname '*.msi' -o -iname 'UACFirmware*' \) -print -quit | grep -q .; then
    echo 'HATA: Microsoft firmware veya SDK/MSI pakete giremez.' >&2
    exit 1
fi
# Also retain the build output for source-tree setup checks and reproducible inspection.
install -m 755 "$WORK/kinect_upload_fw" "$SRC/payload/kinect_upload_fw"
install -m 644 "$APPDIR/usr/bin/payload/manifest.json" "$SRC/payload/manifest.json"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --runtime-file "$RUNTIME" "$APPDIR" "$ROOT/dist/KinectWebcam-v17-x86_64.AppImage"
sha256sum "$ROOT/dist/KinectWebcam-v17-x86_64.AppImage"

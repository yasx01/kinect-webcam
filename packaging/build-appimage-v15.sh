#!/usr/bin/env bash
# Fedora x86_64 build; no system install. Explicit allowlist; no MSI/SDK copying.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/v15"
FIRMWARE="${KINECT_FIRMWARE_PATH:-$SRC/payload/UACFirmware}"
if [ ! -f "$FIRMWARE" ]; then
    echo 'Firmware bulunamadı. Kullanım hakkına sahip olduğun yerel dosyayı KINECT_FIRMWARE_PATH ile belirt.' >&2
    exit 1
fi
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
install -m 644 "$FIRMWARE" "$APPDIR/usr/bin/payload/UACFirmware"
FILES=(kinect_facecam_process_v15.py kinect_facecam_media_v15.py kinect-facecam-firefox-permission-v15.py kinect-facecam-gui-v15.py kinect-facecam-setup-v15.py
       kinect-facecam-bridge-v15.py kinect-facecam-bridge-pipewire-v15.py
       kinect-facecam-start-v15 kinect-facecam-stop-v15
       kinect-facecam-pw-start-v15 kinect-facecam-pw-stop-v15 kinect-facecam-bootstrap-v15)
for name in "${FILES[@]}"; do install -m 755 "$SRC/$name" "$APPDIR/usr/bin/$name"; done
install -m 644 "$SRC/kinect-facecam-icon-v15.png" "$APPDIR/usr/bin/kinect-facecam-icon-v15.png"
install -m 644 "$SRC/licenses/"*.txt "$APPDIR/usr/bin/licenses/"
install -m 644 "$SRC/vendor/kinect-audio-setup/"* "$APPDIR/usr/bin/vendor/kinect-audio-setup/"
install -m 755 "$ROOT/packaging/v15/AppRun" "$APPDIR/AppRun"
install -m 644 "$ROOT/packaging/v15/kinect-facecam.desktop" "$APPDIR/kinect-facecam.desktop"
install -m 644 "$SRC/kinect-facecam-icon-v15.png" "$APPDIR/kinect-facecam.png"
ln -s kinect-facecam.png "$APPDIR/.DirIcon"
python3 -B - "$APPDIR/usr/bin/payload" <<'PYCODE'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1])
manifest={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ('UACFirmware','kinect_upload_fw')}
if manifest['UACFirmware']!='efd1dd2fd2610f69d07af7aeff56b26551ac6ec4251159c50027769545b6f7a5':
    raise SystemExit('Firmware özeti eşleşmedi.')
(p/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PYCODE
if find "$APPDIR" -iname '*.msi' -print -quit | grep -q .; then
    echo 'HATA: SDK/MSI pakete giremez.' >&2
    exit 1
fi
# Also retain the build output for source-tree setup checks and reproducible inspection.
install -m 755 "$WORK/kinect_upload_fw" "$SRC/payload/kinect_upload_fw"
install -m 644 "$APPDIR/usr/bin/payload/manifest.json" "$SRC/payload/manifest.json"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --runtime-file "$RUNTIME" "$APPDIR" "$ROOT/dist/KinectWebcam-v15-x86_64.AppImage"
sha256sum "$ROOT/dist/KinectWebcam-v15-x86_64.AppImage"

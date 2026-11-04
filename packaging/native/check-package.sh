#!/usr/bin/env bash
# Only run inside the disposable CI container, never against a user's host.
set -euo pipefail
if [ "${GITHUB_ACTIONS:-}" != true ] || [ ! -f /.dockerenv ]; then
    echo 'This system-changing check is restricted to a disposable GitHub Actions container.' >&2
    exit 1
fi
format="$1"
if [ "$format" = rpm ]; then
    rpm -qpl dist/*.rpm > /tmp/kinect-native-contents.txt
    dnf install -y --setopt=install_weak_deps=False dist/*.rpm
else
    dpkg-deb --contents ./dist/*.deb > /tmp/kinect-native-contents.txt
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ./dist/*.deb
fi
export QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
for test in tests/v19/test_*.py; do
    if [[ "$test" == *test_portal_integration.py ]]; then
        dbus-run-session -- env KINECT_PRIVATE_BUS_TEST=1 python3 -B "$test"
    else
        python3 -B "$test"
    fi
done
python3 -B packaging/native/check-installed.py "$format"
if [ "$format" = rpm ]; then
    rpm -e kinect-webcam
else
    dpkg --purge kinect-webcam
fi
test ! -e /usr/bin/kinect-webcam
test ! -e /usr/libexec/kinect-webcam/kinect-facecam-gui-v19.py
python3 - "$format" <<'PYCODE'
import json,sys
from pathlib import Path
p=Path('dist/native-'+sys.argv[1]+'-verification.json')
report=json.loads(p.read_text());report['package_removed']=True
p.write_text(json.dumps(report,indent=2)+'\n')
PYCODE

#!/usr/bin/env bash
# Each GUI test gets its own QApplication. The portal test uses a private D-Bus.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export QT_QPA_PLATFORM=offscreen
export PYTHONDONTWRITEBYTECODE=1
for test in tests/v18/test_*.py; do
    echo "Test: $test"
    if [[ "$test" == *test_portal_integration.py ]]; then
        dbus-run-session -- env KINECT_PRIVATE_BUS_TEST=1 python3 -B "$test"
    else
        python3 -B "$test"
    fi
done

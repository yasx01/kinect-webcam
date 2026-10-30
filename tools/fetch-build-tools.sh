#!/usr/bin/env bash
# Downloads only into this project; no sudo or system installation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/build-tools"
fetch() {
    local name="$1" url="$2" expected="$3" temporary
    temporary="$(mktemp "$ROOT/build-tools/.download-XXXXXX")"
    if ! curl --fail --location --proto '=https' --tlsv1.2 "$url" -o "$temporary"; then
        rm -f "$temporary"; return 1
    fi
    if ! printf '%s  %s\n' "$expected" "$temporary" | sha256sum --check --status; then
        rm -f "$temporary"; echo 'İndirme SHA-256 doğrulaması başarısız.' >&2; return 1
    fi
    chmod 755 "$temporary"
    mv "$temporary" "$ROOT/build-tools/$name"
}
fetch appimagetool-1.9.1-x86_64.AppImage https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
fetch runtime-20251108-x86_64 https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64 2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d

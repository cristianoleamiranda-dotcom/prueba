#!/usr/bin/env bash
# Descarga los links de tmpfiles.org a incoming/ desde TU maquina.
#
# tmpfiles entrega una pagina HTML con un enlace directo /dl/<token>/<archivo>.
# Este script resuelve esa pagina y guarda el archivo real (HEIC incluido).
#
# Uso:
#   bash scripts/fetch_links.sh                 # usa links.txt
#   bash scripts/fetch_links.sh mis_links.txt
set -uo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
LIST="${1:-$DIR/links.txt}"
OUT="$DIR/incoming"
mkdir -p "$OUT"

[ -f "$LIST" ] || { echo "No existe $LIST"; exit 1; }

ok=0; fail=0
while IFS= read -r url; do
  url="$(echo "$url" | tr -d '\r' | xargs)"
  case "$url" in ''|\#*) continue ;; esac

  name="$(basename "${url%%\?*}")"
  # tmpfiles: /wXXXX/file.jpg  ->  pagina con el link /dl/<token>/wXXXX/file.jpg
  page="$(curl -fsSL --max-time 30 -A "Mozilla/5.0" "$url" || true)"
  direct="$(printf '%s' "$page" | grep -oE 'https://tmpfiles\.org/dl/[^"]+' | head -1)"

  if [ -n "$direct" ]; then
    if curl -fsSL --max-time 120 -A "Mozilla/5.0" -e "$url" -o "$OUT/$name" "$direct"; then
      echo "  ok   $name  ($(du -h "$OUT/$name" | cut -f1))"
      ok=$((ok+1)); continue
    fi
  fi
  # fallback: algunos mirrors aceptan la URL tal cual
  if curl -fsSL --max-time 120 -A "Mozilla/5.0" -o "$OUT/$name" "$url" \
     && python3 - "$OUT/$name" <<'PY'
import sys
head = open(sys.argv[1], "rb").read(16)
ok = (head[4:12].startswith(b"ftyp") or head[:3] == b"\xff\xd8\xff"
      or head[:8] == b"\x89PNG\r\n\x1a\n" or head[:4] in (b"II*\x00", b"MM\x00*")
      or head[:4] == b"RIFF")
sys.exit(0 if ok else 1)
PY
  then
    echo "  ok*  $name  (directo)"
    ok=$((ok+1))
  else
    echo "  FAIL $name  <- $url"
    rm -f "$OUT/$name"
    fail=$((fail+1))
  fi
done < "$LIST"

echo
echo "Descargadas: $ok   Fallidas: $fail   -> $OUT"
[ "$ok" -gt 0 ] && echo "Siguiente paso:  python3 scripts/retouch.py incoming --out out/feed --preset editorial --logo assets/brand/abyss_knockout.png --logo-pos auto --logo-width 0.20 --crop 1080x1350"
exit 0

#!/usr/bin/env python3
"""
prepare_brand.py — convierte el logo del cliente en un kit de marca listo para fotografia.

Entrada: un PNG con transparencia (la insignia circular del estudio).
Salida en assets/brand/:
  abyss_color.png    insignia original, recortada y centrada (uso principal sobre negro)
  abyss_line.png     solo lineas (crema) con el disco transparente: version ligera
  abyss_ink.png      monocromo oscuro: para fondos claros / papel / membretes
  abyss_512.png / abyss_256.png / abyss_128.png   avatar, favicon, sello de story

Reglas que aplica:
  - respeta el diseño original: no recolorea la insignia principal
  - recorta por alfa y rellena a cuadrado exacto (evita descuadres al escalar)
  - el recorte deja 2% de aire (sangrado) para que el antialias no se corte

Uso:
  python3 scripts/prepare_brand.py --src /ruta/logo.png --name abyss
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "brand")
CREAM = np.array([0.945, 0.925, 0.890], dtype=np.float32)   # hueso del logo
DARK = np.array([0.075, 0.072, 0.065], dtype=np.float32)    # tinta


def _square(im: Image.Image, pad_frac: float = 0.02) -> Image.Image:
    """Recorta al contenido con alfa y rellena a cuadrado con margen uniforme."""
    a = np.asarray(im.convert("RGBA"))
    ys, xs = np.where(a[..., 3] > 8)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    im = im.crop((x0, y0, x1, y1))
    side = int(max(im.size) * (1 + 2 * pad_frac))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def _mono_line(im: Image.Image, color: np.ndarray, lo: float, hi: float) -> Image.Image:
    """Convierte la insignia en lineas de un solo color, con el disco transparente.

    alpha_nuevo = alpha_original * smoothstep(lo, hi, luminancia)
    Asi el fondo oscuro del disco desaparece y quedan craneo, tipografia y filetes.
    """
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255.0
    L = a[..., :3].mean(axis=2)
    t = np.clip((L - lo) / max(hi - lo, 1e-6), 0, 1)
    t = t * t * (3 - 2 * t)
    alpha = a[..., 3] * t
    out = np.zeros_like(a)
    out[..., :3] = color
    out[..., 3] = alpha
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


def _knockout(im: Image.Image, lo: float, hi: float) -> Image.Image:
    """Quita el disco/placa de fondo y CONSERVA los colores originales del arte.

    alpha_nuevo = alpha * smoothstep(lo, hi, luminancia)
    El crema y el verde sobreviven; el marron oscuro de la placa desaparece. Es la
    variante que mejor se integra en fotografia: no hay 'sticker' ni caja visible.
    """
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255.0
    L = a[..., :3].mean(axis=2)
    t = np.clip((L - lo) / max(hi - lo, 1e-6), 0, 1)
    t = t * t * (3 - 2 * t)
    out = a.copy()
    out[..., 3] = a[..., 3] * t
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


def _solid(im: Image.Image, color: np.ndarray) -> Image.Image:
    """Silueta monocroma solida (mantiene el alfa original): sello para fondos claros."""
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255.0
    out = np.zeros_like(a)
    out[..., :3] = color
    out[..., 3] = a[..., 3]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="PNG del logo con transparencia")
    ap.add_argument("--name", default="abyss")
    ap.add_argument("--size", type=int, default=1200, help="lado del master exportado")
    ap.add_argument("--threshold", type=float, nargs=2, default=(0.34, 0.52),
                    help="rango de luminancia para extraer las lineas")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    base = _square(Image.open(args.src).convert("RGBA"))

    master = base.resize((args.size, args.size), Image.LANCZOS)
    master.save(os.path.join(OUT_DIR, f"{args.name}_color.png"))
    print("escrito:", f"assets/brand/{args.name}_color.png", master.size)

    line = _mono_line(base, CREAM, *args.threshold).resize((args.size, args.size), Image.LANCZOS)
    line.save(os.path.join(OUT_DIR, f"{args.name}_line.png"))
    print("escrito:", f"assets/brand/{args.name}_line.png", line.size)

    # monocromo oscuro de LINEAS (no silueta): sirve sobre papel, membretes y fondos claros
    knock = _knockout(base, *args.threshold).resize((args.size, args.size), Image.LANCZOS)
    knock.save(os.path.join(OUT_DIR, f"{args.name}_knockout.png"))
    print("escrito:", f"assets/brand/{args.name}_knockout.png", knock.size)

    ink = _mono_line(base, DARK, *args.threshold).resize((args.size, args.size), Image.LANCZOS)
    ink.save(os.path.join(OUT_DIR, f"{args.name}_ink.png"))
    print("escrito:", f"assets/brand/{args.name}_ink.png", ink.size)

    for s in (512, 256, 128):
        master.resize((s, s), Image.LANCZOS).save(os.path.join(OUT_DIR, f"{args.name}_{s}.png"))
        print("escrito:", f"assets/brand/{args.name}_{s}.png")

    # copia del original intacto (fuente de verdad del cliente)
    base.resize((args.size, args.size), Image.LANCZOS).save(
        os.path.join(OUT_DIR, f"{args.name}_original.png"))


if __name__ == "__main__":
    main()

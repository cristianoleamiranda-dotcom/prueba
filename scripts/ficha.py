#!/usr/bin/env python3
"""
ficha.py — arma la "FICHA" de marca/estudio en una sola imagen.

En el flujo de comerciales con IA, la ficha es el paso que evita que la marca cambie
entre tomas: se genera una vez y se adjunta como referencia a TODAS las generaciones
posteriores. Este script la construye con material real ya editado del estudio
(`entregas/`), para no depender de generar la ficha desde cero.

Layout (igual al de la guia de referencia):
  [ hero grande 3/4 ]  [ 4 vistas: frente / perfil / detalle / entorno ]
  [ 3 macro detalles ] [ franja de swatches con hex ]

Uso:
  python3 scripts/ficha.py                        # arma entregas/ficha_abyss.jpg
  python3 scripts/ficha.py --out mi_ficha.jpg
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H = 2000, 2600
BG = (14, 14, 15)
INK = (240, 236, 228)
MUTED = (150, 146, 138)


def _f(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def _cover(im: Image.Image, w: int, h: int) -> Image.Image:
    """Recorta cubriendo el marco (sin deformar)."""
    r = max(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 3
    return im.crop((x, y, x + w, y + h))


def _label(d: ImageDraw.ImageDraw, xy, text: str, size: int = 22, fill=MUTED,
           max_w: int | None = None):
    txt = text.upper()
    f = _f(size)
    if max_w:
        while d.textlength(txt, font=f) > max_w and len(txt) > 4:
            txt = txt[:-2]
    d.text(xy, txt, font=f, fill=fill)


NICE = {
    "trabajo_hombro_real": "hombro · realismo",
    "lobo_samurai": "lobo samurái",
    "craneo": "cráneo",
    "cristo": "cristo",
    "trabajo_lobo_luna": "lobo luna",
    "payaso": "payaso",
    "vitrina": "vitrina de joyería",
    "proceso_hombro": "en proceso",
    "septum": "septum · titanio",
    "helice": "hélix · titanio",
    "plate_p05_color_anime": "color · anime",
    "goku": "goku · color",
}


def _pretty(path: str) -> str:
    stem = os.path.basename(path).replace("_retouched.jpg", "")
    return NICE.get(stem, stem.replace("plate_", "").replace("_", " ")[:18])


def _palette(logo_path: str, k: int = 5) -> list[tuple[int, int, int]]:
    """Extrae los colores dominantes de la insignia (excluye el alfa bajo)."""
    a = np.asarray(Image.open(logo_path).convert("RGBA").resize((160, 160)))
    m = a[..., 3] > 200
    px = a[m][:, :3].reshape(-1, 3)
    if len(px) == 0:
        return [(240, 236, 228)] * k
    q = (px // 24 * 24).astype(np.int32)
    keys, counts = np.unique(q, axis=0, return_counts=True)
    order = np.argsort(-counts)
    out = []
    for i in order:
        c = tuple(int(v) for v in keys[i])
        if all(sum(abs(c[j] - o[j]) for j in range(3)) > 45 for o in out):
            out.append(c)
        if len(out) == k:
            break
    while len(out) < k:
        out.append(out[-1])
    return out


def build(photos: dict, logo: str, out_path: str, title: str = "ABYSS · TATTOO Y PIERCING"):
    canvas = Image.new("RGB", (W, H + 400), BG)
    d = ImageDraw.Draw(canvas)
    m = 56

    # --- encabezado ---
    d.text((m, 46), title, font=_f(46, True), fill=INK)
    d.text((m, 104), "FICHA DE MARCA · REFERENCIA PARA GENERACIÓN DE TOMAS",
           font=_f(21), fill=MUTED)
    lg = Image.open(logo).convert("RGBA")
    ls = int(W * 0.11)
    lg = lg.resize((ls, int(lg.height * ls / lg.width)), Image.LANCZOS)
    canvas.paste(lg, (W - m - ls, 40), lg)
    d.line([(m, 168), (W - m, 168)], fill=(60, 60, 62), width=2)

    # --- hero ---
    hy = 200
    hw, hh = int(W * 0.52) - m // 2, 980
    hero = _cover(Image.open(photos["hero"]).convert("RGB"), hw, hh)
    canvas.paste(hero, (m, hy))
    _label(d, (m + 16, hy + hh - 44), "01 · hero 3/4", 22, (235, 232, 225))

    # --- 4 vistas ---
    gx = m + hw + 24
    gw = W - m - gx
    gy = hy
    gh = (hh - 24) // 2
    views = photos["views"][:4]
    for i, p in enumerate(views):
        col, row = i % 2, i // 2
        x, y = gx + col * (gw // 2 + 12), gy + row * (gh + 24)
        w_, h_ = gw // 2 - 6, gh
        canvas.paste(_cover(Image.open(p).convert("RGB"), w_, h_), (x, y))
        _label(d, (x + 10, y + h_ - 34), f"0{i + 2} · {_pretty(p)}", 19,
               (235, 232, 225), max_w=w_ - 90)

    # --- macros ---
    my = hy + hh + 40
    d.text((m, my - 6), "DETALLE Y TEXTURA", font=_f(24, True), fill=INK)
    my += 42
    n = max(1, len(photos["macros"][:3]))
    mw = (W - 2 * m - (n - 1) * 24) // n
    mh = 620
    for i, p in enumerate(photos["macros"][:3]):
        x = m + i * (mw + 24)
        canvas.paste(_cover(Image.open(p).convert("RGB"), mw, mh), (x, my))
        _label(d, (x + 10, my + mh - 34), f"0{i + 6} · {_pretty(p)}", 19,
               (235, 232, 225), max_w=mw - 90)

    # --- swatches ---
    sy = my + mh + 56
    d.text((m, sy - 6), "PALETA DE MARCA", font=_f(24, True), fill=INK)
    sy += 44
    cols = _palette(logo)
    sw = (W - 2 * m - (len(cols) - 1) * 18) // len(cols)
    for i, c in enumerate(cols):
        x = m + i * (sw + 18)
        d.rectangle([x, sy, x + sw, sy + 130], fill=c)
        d.text((x, sy + 140), "#%02X%02X%02X" % c, font=_f(20), fill=INK)

    # --- reglas de consistencia ---
    ry = sy + 200
    d.line([(m, ry - 18), (W - m, ry - 18)], fill=(60, 60, 62), width=2)
    rules = [
        "Misma insignia, misma tipografía, mismo trazo: nada se rediseña entre tomas.",
        "Entorno fijo: estudio oscuro, pared texturada, luz lateral suave y cálida.",
        "Piel real con poro visible; el tatuaje conserva su negro y su gris.",
        "Sin texto agregado. La única marca es la insignia.",
    ]
    for i, r in enumerate(rules):
        d.text((m, ry + i * 38), f"—  {r}", font=_f(24), fill=(196, 192, 184))

    bottom = ry + len(rules) * 38 + 40
    canvas = canvas.crop((0, 0, W, min(canvas.height, bottom)))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    canvas.save(out_path, quality=94, subsampling=1)
    return out_path


def pick_defaults() -> dict:
    base = os.path.join(ROOT, "entregas", "feed")
    piel = os.path.join(ROOT, "entregas", "piel")
    files = {os.path.basename(p): p for p in glob.glob(os.path.join(base, "*_retouched.jpg"))}
    files.update({os.path.basename(p): p for p in glob.glob(os.path.join(piel, "*_retouched.jpg"))})

    def pick(*names):
        for n in names:
            for k, v in files.items():
                if n in k:
                    return v
        return None

    hero = pick("trabajo_hombro_real", "lobo_samurai", "craneo")
    views = [pick("cristo"), pick("trabajo_lobo_luna"), pick("payaso"), pick("plate_p08_vitrina", "vitrina")]
    macros = [pick("plate_p03", "proceso_hombro"), pick("plate_p07", "septum"), pick("plate_p06", "helice")]
    views = [v for v in views if v]
    macros = [v for v in macros if v]
    if not hero or not views or not macros:
        raise SystemExit("faltan entregas: corre `make paquete` antes de armar la ficha")
    return {"hero": hero, "views": views, "macros": macros}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "entregas", "ficha_abyss.jpg"))
    ap.add_argument("--logo", default=os.path.join(ROOT, "assets", "brand", "abyss_source.png"))
    ap.add_argument("--json", default=os.path.join(ROOT, "workflow", "ficha.json"),
                    help="donde dejar el registro de fotos usadas")
    args = ap.parse_args()

    photos = pick_defaults()
    out = build(photos, args.logo, args.out)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"ficha": os.path.relpath(out, ROOT),
                   "fotos": {k: (os.path.relpath(v, ROOT) if isinstance(v, str)
                                 else [os.path.relpath(x, ROOT) for x in v])
                             for k, v in photos.items()}},
                  fh, indent=2, ensure_ascii=False)
    print("ficha:", os.path.relpath(out, ROOT))
    print("registro:", os.path.relpath(args.json, ROOT))


if __name__ == "__main__":
    main()

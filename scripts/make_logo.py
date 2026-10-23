#!/usr/bin/env python3
"""
Genera el logotipo del estudio en PNG (RGBA, alta resolucion) + un SVG editable.

La marca se dibuja con primitivas vectoriales (PIL) sobre un lienzo 8x y se
reduce con Lanczos, de modo que los bordes quedan limpios a cualquier escala.

Uso:
    python3 scripts/make_logo.py                     # todas las variantes
    python3 scripts/make_logo.py --name "ESTUDIO TINTA" --sub "SANTIAGO · CHILE"

Salida: assets/brand/logo_<variante>.png  +  assets/brand/logo.svg
"""
from __future__ import annotations

import argparse
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "brand")

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

SS = 8  # supersampling

# Paleta de marca
PALETTE = {
    "ivory": (245, 242, 235, 255),   # hueso: sobre fondo oscuro
    "gold": (198, 166, 116, 255),    # laton/oro viejo: acento premium
    "ink": (16, 16, 16, 255),        # tinta: sobre fondo claro
}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _text_tracked(draw: ImageDraw.ImageDraw, xy, text: str, font, fill,
                  tracking: float = 0.0, anchor_mid: bool = True) -> tuple[float, float]:
    """Dibuja texto con tracking manual (letter-spacing) y devuelve el bbox."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_mid:
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    return total, y


def _measure_tracked(draw, text, font, tracking=0.0):
    widths = [draw.textlength(ch, font=font) for ch in text]
    return sum(widths) + tracking * (len(text) - 1)


def _mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill, lw: float):
    """Marca: rombo/extasis de aguja dentro de un circulo fino.

    Lectura: una aguja (vertical) atraviesa un rombo: tinta + precision.
    Trazo fino, geometria dura -> legible a 40 px de ancho.
    """
    # circulo exterior fino
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=fill, width=int(max(1, lw)))
    # rombo interior (90 grados)
    d = r * 0.52
    draw.polygon([(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)], outline=fill, width=int(max(1, lw)))
    # aguja: vertical que sobresale del circulo por arriba (punta) y apenas abajo
    top, bot = cy - r * 1.30, cy + r * 1.06
    draw.line([(cx, top), (cx, bot)], fill=fill, width=int(max(1, lw)))
    # punta de aguja (pequeno triangulo arriba)
    t = r * 0.15
    draw.polygon([(cx, top - t * 1.7), (cx - t, top), (cx + t, top)], fill=fill)


def build_mark(color: tuple, width_px: int = 1200) -> Image.Image:
    """Solo la marca (sin texto): uso en favicon, sello de agua, esquinas apretadas."""
    size = width_px
    img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _mark(d, size * SS / 2, size * SS * 0.52, size * SS * 0.30, color, lw=size * SS * 0.026)
    return img.resize((size, size), Image.LANCZOS)


def build_logo(name: str, sub: str, color: tuple, width_px: int = 2400,
               compact: bool = False) -> Image.Image:
    """Construye el lockup horizontal: [marca] [nombre / subtitulo]."""
    W, H = width_px, int(width_px * 0.255)
    img = Image.new("RGBA", (W * SS // 4, H * SS // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = img.size

    # --- marca ---
    r = h * 0.255
    cx, cy = r + h * 0.10, h * 0.5
    _mark(d, cx, cy, r, color, lw=h * 0.016)

    # --- bloque de texto ---
    if compact:
        sub = ""
    name_font = _font(FONT_SERIF, int(h * 0.195))
    sub_font = _font(FONT_SANS, int(h * 0.105))
    track_name = h * 0.045
    track_sub = h * 0.062

    tx = cx + r + h * 0.155
    # linea vertical separadora (hairline)
    d.line([(tx - h * 0.075, cy - r * 0.92), (tx - h * 0.075, cy + r * 0.92)],
           fill=color[:3] + (110,), width=int(max(1, h * 0.008)))

    name_w = _measure_tracked(d, name.upper(), name_font, track_name)
    sub_w = _measure_tracked(d, sub.upper(), sub_font, track_sub) if sub else 0
    block_w = max(name_w, sub_w)

    # anclaje optico: centrar la caja de mayusculas de cada linea en su eje
    nb = name_font.getbbox(name.upper())
    name_cap = nb[3] - nb[1]
    name_y = cy - h * 0.115 - name_cap / 2 - nb[1]
    _text_tracked(d, (tx + name_w / 2, name_y), name.upper(), name_font, color,
                  tracking=track_name, anchor_mid=True)

    if sub:
        # hairline bajo el nombre
        ry = cy + h * 0.045
        d.line([(tx, ry), (tx + block_w, ry)], fill=color[:3] + (110,), width=int(max(1, h * 0.007)))
        sb = sub_font.getbbox(sub.upper())
        sub_cap = sb[3] - sb[1]
        sub_y = cy + h * 0.185 - sub_cap / 2 - sb[1]
        _text_tracked(d, (tx + sub_w / 2, sub_y), sub.upper(), sub_font, color,
                      tracking=track_sub, anchor_mid=True)

    used_w = tx + block_w + h * 0.12
    img = img.crop((0, 0, int(min(w, used_w)), h))
    img = img.resize((width_px, int(img.size[1] * width_px / img.size[0])), Image.LANCZOS)
    return img


def write_svg(name: str, sub: str, path: str):
    """SVG equivalente (vectorial, editable en Illustrator/Figma)."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 300" width="1000" height="300">
  <!-- Lockup: marca + nombre + subtitulo. Cambia currentColor para recolorear. -->
  <g fill="none" stroke="currentColor" stroke-width="4">
    <circle cx="150" cy="150" r="78"/>
    <polygon points="150,109 191,150 150,191 109,150"/>
    <line x1="150" y1="40" x2="150" y2="260"/>
  </g>
  <polygon points="150,16 135,40 165,40" fill="currentColor"/>
  <line x1="262" y1="78" x2="262" y2="222" stroke="currentColor" stroke-opacity="0.45" stroke-width="2"/>
  <g fill="currentColor" font-family="DejaVu Serif, Georgia, serif" font-size="58" letter-spacing="13">
    <text x="286" y="142">{name.upper()}</text>
  </g>
  <line x1="286" y1="170" x2="906" y2="170" stroke="currentColor" stroke-opacity="0.5" stroke-width="2"/>
  <g fill="currentColor" font-family="DejaVu Sans, Arial, sans-serif" font-size="26" letter-spacing="17">
    <text x="286" y="216">{sub.upper()}</text>
  </g>
</svg>
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="ESTUDIO TINTA")
    ap.add_argument("--sub", default="SANTIAGO · CHILE")
    ap.add_argument("--width", type=int, default=2400)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    for variant, color in PALETTE.items():
        img = build_logo(args.name, args.sub, color, width_px=args.width)
        out = os.path.join(OUT_DIR, f"logo_{variant}.png")
        img.save(out)
        print("escrito:", os.path.relpath(out, ROOT), img.size)

        comp = build_logo(args.name, args.sub, color, width_px=args.width, compact=True)
        out = os.path.join(OUT_DIR, f"logo_compact_{variant}.png")
        comp.save(out)
        print("escrito:", os.path.relpath(out, ROOT), comp.size)

        mark = build_mark(color, width_px=1200)
        out = os.path.join(OUT_DIR, f"logo_mark_{variant}.png")
        mark.save(out)
        print("escrito:", os.path.relpath(out, ROOT), mark.size)

    write_svg(args.name, args.sub, os.path.join(OUT_DIR, "logo.svg"))
    print("escrito: assets/brand/logo.svg")


if __name__ == "__main__":
    main()

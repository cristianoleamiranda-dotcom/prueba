#!/usr/bin/env python3
"""
retouch.py — motor de retoque fotografico profesional (estilo editorial oscuro /
motion-design still). Sin texto: solo luz, volumen, color y marca.

Implementa, en orden de flujo profesional:
  01 lectura + perfil de color + orientacion
  02 balance de blancos y exposicion global (auto, medido en percentiles robustos)
  03 curva de tono filmica (negros densos, rolloff de altas luces)
  04 contraste local / claridad (radio grande, mascara de bordes)
  05 escultura 3D: mapa de sombreado de gran radio sobre luminancia -> modelado de volumen
  06 dodge & burn: luces y sombras pintadas con mascaras suaves (no destructivo: se aplica sobre luminancia)
  07 brillos: bloom con rodilla suave en altas luces + halo calido
  08 separacion de frecuencias ligera para microcontraste sin plasticidad
  09 color grade: split toning frio/calido, vibrancia, densidades
  10 grano filmico + viñeteo final
  11 marca: logo integrado con muestreo de fondo, sombra y escala optica

Uso:
  python3 scripts/retouch.py foto.jpg --out out/foto.jpg --preset editorial
  python3 scripts/retouch.py ./fotos --out ./out --logo assets/brand/abyss_knockout.png
  python3 scripts/retouch.py foto.heif --out out --preset motion --logo-pos auto
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from dataclasses import dataclass, asdict, field

import numpy as np
from PIL import Image, ImageFilter, ImageOps

try:  # HEIF/HEIC (iPhone)
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_OK = True
except Exception:  # pragma: no cover
    HEIF_OK = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPPORTED = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heif", ".heic", ".bmp"}

# ----------------------------------------------------------------------------- presets
@dataclass
class Preset:
    """Perillas del look. Todas 0..1 salvo donde se indica."""
    name: str = "editorial"
    exposure: float = 0.0        # compensacion manual extra en EVs
    target_mid: float = 0.30     # (legado) referencia de medios
    key_tone: float = 0.60       # tono clave objetivo: p88 de luminancia del sustrato
    ev_limit: float = 0.55       # correccion maxima de exposicion permitida (EV)
    contrast: float = 0.22
    black_density: float = 0.34  # cuanto se hunden los negros (fondo negro puro)
    clarity: float = 0.26
    sculpture: float = 0.38      # modelado 3D por mapa de sombreado
    dodge: float = 0.22
    burn: float = 0.34
    bloom: float = 0.16
    bloom_radius: float = 0.010  # fraccion del lado mayor
    bloom_warmth: float = 0.20
    micro_contrast: float = 0.22
    vibrance: float = 0.12
    saturation: float = 0.98     # multiplicador (1.0 = neutro)
    shadow_tint: tuple = (0.06, 0.09, 0.14)   # azul acero en sombras
    highlight_tint: tuple = (0.14, 0.11, 0.06)  # laton calido en luces
    split_amount: float = 0.16
    grain: float = 0.022
    vignette: float = 0.42
    sharpness: float = 0.50
    key_light: tuple = (0.34, 0.24)   # posicion relativa de la luz clave (x, y)
    key_strength: float = 0.18
    upscale: int = 1


PRESETS = {
    # Cercano a la referencia: fondo negro profundo, piel calida, tatuaje con volumen
    "editorial": Preset(),
    # Mas agresivo: microcontraste alto, bloom marcado, sensacion de "still" de motion
    "motion": Preset(
        name="motion", target_mid=0.30, contrast=0.28, black_density=0.42,
        clarity=0.34, sculpture=0.48, dodge=0.28, burn=0.44, bloom=0.26,
        bloom_radius=0.016, bloom_warmth=0.26, micro_contrast=0.28,
        vibrance=0.18, saturation=0.98, split_amount=0.24, grain=0.016,
        vignette=0.54, sharpness=0.58, key_strength=0.24,
    ),
    # Natural / entrega de cliente: sin grano, brillos contenidos
    "clean": Preset(
        name="clean", target_mid=0.34, contrast=0.14, black_density=0.18,
        clarity=0.18, sculpture=0.24, dodge=0.14, burn=0.20, bloom=0.08,
        bloom_radius=0.008, micro_contrast=0.16, vibrance=0.08, split_amount=0.08,
        grain=0.0, vignette=0.26, sharpness=0.44, key_strength=0.10,
    ),
    # Blanco y negro con separacion tonal
    "noir": Preset(
        name="noir", target_mid=0.28, contrast=0.28, black_density=0.40,
        clarity=0.32, sculpture=0.46, dodge=0.24, burn=0.40, bloom=0.18,
        micro_contrast=0.26, vibrance=0.0, saturation=0.0, split_amount=0.06,
        grain=0.034, vignette=0.48, sharpness=0.56, key_strength=0.18,
    ),
}
PRESETS["studio"] = PRESETS["editorial"]


# ----------------------------------------------------------------------------- utils
def _load(path: str) -> Image.Image:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (0, 0, 0))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    return im.convert("RGB")


def _f(im: np.ndarray) -> np.ndarray:
    return im.astype(np.float32) / 255.0


def _u(a: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(a, 0, 1) * 255.0 + 0.5).astype(np.uint8))


def _gauss(a: np.ndarray, sigma: float) -> np.ndarray:
    """Desenfoque gaussiano separable (scipy) con bordes reflejados: sin halos."""
    if sigma <= 0.05:
        return a.copy()
    from scipy.ndimage import gaussian_filter
    sig = (0, 0, sigma) if a.ndim == 3 else (sigma, sigma)
    return gaussian_filter(a, sigma=sig, mode="reflect", truncate=3.0).astype(np.float32)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _screen(base: np.ndarray, top: np.ndarray, amount: float) -> np.ndarray:
    s = 1.0 - (1.0 - base) * (1.0 - top)
    return base + (s - base) * amount


def _soft_light(base: np.ndarray, top: np.ndarray) -> np.ndarray:
    return np.where(top <= 0.5,
                    2 * base * top + base ** 2 * (1 - 2 * top),
                    2 * base * (1 - top) + np.sqrt(np.maximum(base, 0)) * (2 * top - 1))


def _smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / max(e1 - e0, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


def _radial(h: int, w: int, cx: float, cy: float, rx: float, ry: float, feather: float = 1.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / max(rx, 1)) - cx) ** 2 + ((yy / max(ry, 1)) - cy) ** 2)
    return 1.0 - _smoothstep(0.0, feather, d)


def _apply_luma(rgb: np.ndarray, newL: np.ndarray) -> np.ndarray:
    """Re-inyecta una luminancia nueva conservando el croma original.

    Clave del look limpio: todo el modelado (claridad, relieve, brillos, enfoque) se
    hace en luminancia. Si se hace por canal, el ruido de croma del JPEG se amplifica
    y aparecen motas naranja/cian.
    """
    L = _luma(rgb)
    ratio = newL / np.maximum(L, 1e-4)
    return np.clip(rgb * ratio[..., None], 0, 1)


def _percentile(a: np.ndarray, q: float) -> float:
    return float(np.percentile(a, q))


# ----------------------------------------------------------------------------- etapas
def analyze(rgb: np.ndarray) -> dict:
    L = _luma(rgb)
    med = np.median(rgb.reshape(-1, 3), axis=0)
    return {
        "size": [rgb.shape[1], rgb.shape[0]],
        "luma_p01": _percentile(L, 1), "luma_p50": _percentile(L, 50),
        "luma_p99": _percentile(L, 99),
        "shadow_clip": float((L < 0.02).mean()), "highlight_clip": float((L > 0.98).mean()),
        "cast_rgb_median": [round(float(v), 4) for v in med],
        "cast_ratio": [round(float(med[0] / max(med[1], 1e-6)), 3),
                       round(float(med[2] / max(med[1], 1e-6)), 3)],
    }


def apply_exposure(rgb: np.ndarray, ev: float) -> np.ndarray:
    """Exposicion con proteccion de altas luces (low-key safe).

    Un multiplicador puro (2**ev) estampa las luces contra 1.0 y quema los bordes
    iluminados. Aqui la ganancia se reparte como curva asintotica: los medios suben,
    las luces ya altas casi no se mueven. Es el equivalente a subir 'Sombras/Medios'
    en Lightroom en vez de 'Exposicion'.
    """
    if abs(ev) < 1e-3:
        return rgb
    g = 2.0 ** float(ev)
    if ev > 0:
        return np.clip(1.0 - (1.0 - np.clip(rgb, 0, 1)) ** g, 0, 1)
    return np.clip(np.clip(rgb, 0, 1) ** g, 0, 1)


def meter_subject(rgb: np.ndarray) -> dict:
    """Medicion de exposicion por SUJETO, no por promedio del encuadre.

    En low-key (fondo negro dominante) el promedio hunde la medicion y sobreexpone
    al sujeto. Se descarta el fondo (bajo p5 + margen) y se mide sobre el sustrato.
    """
    L = _luma(rgb)
    p05 = float(np.percentile(L, 5))
    p50 = float(np.percentile(L, 50))
    thr = max(p05 + 0.02, (p05 + p50) * 0.45)
    mask = L > thr
    if mask.sum() < L.size * 0.05:
        mask = L > np.percentile(L, 60)
    sub = L[mask]
    return {"key_tone": float(np.percentile(sub, 88)),
            "mid_tone": float(np.median(sub)),
            "subject_ratio": float(mask.mean()),
            "bg_level": p05}


def highlight_recovery(rgb: np.ndarray, thresh: float = 0.88) -> np.ndarray:
    """Recupera luces a punto de quemarse antes de aplicar exposicion.

    Si un canal esta alto pero otros no, se reescala el pixel para que la relacion
    de color sobreviva: evita el tipico 'blob' blanco sin color al subir el brillo.
    """
    peak = rgb.max(axis=2, keepdims=True)
    hot = peak > thresh
    if not hot.any():
        return rgb
    scale = np.where(hot, thresh + (peak - thresh) * 0.35, 1.0) / np.maximum(peak, 1e-4)
    scale = np.where(hot, scale, 1.0)
    return np.clip(rgb * scale, 0, 1)


def white_balance(rgb: np.ndarray, strength: float = 0.65) -> np.ndarray:
    """Gray-world robusto: solo sobre tonos medios, evita que un fondo negro lo rompa."""
    L = _luma(rgb)
    m = (L > 0.18) & (L < 0.85)
    if m.sum() < 500:
        m = L > 0.08
    if m.sum() < 100:
        return rgb
    med = np.median(rgb[m], axis=0)
    target = med.mean()
    gains = target / np.maximum(med, 1e-4)
    gains = 1.0 + (gains - 1.0) * strength
    gains = np.clip(gains, 0.94, 1.08)      # nunca enfriar/calentar mas de ~8%
    return np.clip(rgb * gains[None, None, :], 0, 4)


def _shoulder(x: np.ndarray, knee: float = 0.68, c: float = 2.2) -> np.ndarray:
    """Rodilla filmica de altas luces: C1 en el codo, sin escalones ni plateaus.

    Por debajo de `knee` es identidad; arriba, la pendiente decae de forma continua
    hasta ~0.3 en el blanco. Resultado: las luces llegan a 0.98 con detalle, no se
    estampan contra 1.0 (que es lo que produce los 'parches' planos).
    """
    k = knee
    out = x.copy()
    m = x > k
    t = (x[m] - k) / (1.0 - k)
    f = (1.0 - np.exp(-c * t)) / (1.0 - np.exp(-c))
    out[m] = k + (1.0 - k) * f
    return out


def tone_curve(rgb: np.ndarray, contrast: float, black_density: float) -> np.ndarray:
    """Curva de tono: S simetrica en el medio + pie denso + rodilla de altas luces."""
    x = np.clip(rgb, 0, 1)
    # S-curve simetrica (equivale a una curva de contraste en espacio perceptual)
    sm = x * x * (3 - 2 * x)
    s = x + (sm - x) * (contrast * 1.35)
    # pie: hunde el fondo sin empastar el detalle de las sombras
    s = s - black_density * 0.16 * (1.0 - _smoothstep(0.0, 0.30, s)) * s
    # techo: rodilla filmica
    s = _shoulder(np.clip(s, 0, 1.4), knee=0.66)
    return np.clip(s, 0, 1)


def local_contrast(rgb: np.ndarray, amount: float, radius_frac: float = 0.03) -> np.ndarray:
    """Claridad: unsharp de radio grande con mascara de bordes (no ensucia superficies lisas)."""
    if amount <= 0:
        return rgb
    sigma = max(2.0, min(rgb.shape[:2]) * radius_frac)
    L = _luma(rgb)
    base = _gauss(L, sigma)
    edges = np.abs(_gauss(L, sigma * 0.5) - L)
    guard = _smoothstep(0.002, 0.05, edges)          # solo actuamos donde hay estructura
    detail = (L - base) * (0.55 + 0.45 * guard)
    return _apply_luma(rgb, np.clip(L + detail * amount * 1.25, 0, 1))


def sculpture_3d(rgb: np.ndarray, amount: float, radius_frac: float = 0.05) -> np.ndarray:
    """Modelado 3D: el mapa de sombreado de gran radio se usa como 'matcap' tonal.

    Levanta el relieve percibido (arcos, musculo, cuero) sin tocar el detalle fino:
    se trabaja en luminancia y se re-inyecta el color original.
    """
    if amount <= 0:
        return rgb
    L = _luma(rgb)
    sigma = max(6.0, min(rgb.shape[:2]) * radius_frac)
    shade = _gauss(L, sigma)
    # relieve = shade en forma de S alrededor del gris medio -> micro volumen
    relief = _soft_light(np.clip(shade, 0, 1), np.clip(shade * 1.35 - 0.175, 0, 1))
    relief = relief - shade                      # solo la componente de modelado
    Ln = np.clip(L + relief * amount * 1.6, 0, 1)
    out = _apply_luma(rgb, Ln)
    # gradiente de saturacion: las sombras profundas se desaturan un poco (piel real)
    sat = 1.0 - 0.10 * amount * (1 - _smoothstep(0.0, 0.35, L))
    gray = Ln[..., None]
    return np.clip(gray + (out - gray) * sat[..., None], 0, 1)


def dodge_burn(rgb: np.ndarray, preset: Preset, seed: int = 7) -> np.ndarray:
    """Pinta luz con mascaras suaves: dodge en zonas de luz clave, burn en bordes/fondo."""
    if preset.dodge <= 0 and preset.burn <= 0:
        return rgb
    h, w = rgb.shape[:2]
    L = _luma(rgb)

    # 1) LUZ CLAVE: dodge eliptico donde la fuente de luz ya incide + refuerzo de brillo
    kx, ky = preset.key_light
    key = _radial(h, w, cx=kx * w, cy=ky * h, rx=w * 0.52, ry=h * 0.42, feather=1.25)
    key = key * _smoothstep(0.10, 0.55, L) * (1.0 - _smoothstep(0.66, 0.92, L))
    L = L + key * preset.key_strength * preset.dodge * 0.55

    # 2) BURN perimetral: hunde el fondo para que el sujeto se despegue (profundidad)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / w - 0.5, yy / h - 0.5
    r = np.sqrt((nx * 1.06) ** 2 + (ny * 0.86) ** 2)
    edge = _smoothstep(0.30, 0.86, r)
    edge *= 1.0 - _smoothstep(0.55, 0.95, L)         # no apagues altas luces del sujeto
    L = L - edge * preset.burn * 0.30

    # 3) BURN de contacto: micro sombras en transiciones (donde el gradiente es alto y oscuro)
    grad = np.abs(_gauss(L, 2.0) - L)
    contact = _smoothstep(0.01, 0.10, grad) * (1 - _smoothstep(0.15, 0.55, L))
    L = L - contact * preset.burn * 0.10

    L = np.clip(L, 0, 1)
    ratio = L / np.maximum(_luma(rgb), 1e-4)
    return np.clip(rgb * ratio[..., None], 0, 1)


def bloom(rgb: np.ndarray, preset: Preset) -> np.ndarray:
    """Brillo optico: extrae altas luces con rodilla suave, las difumina y las suma (screen)."""
    if preset.bloom <= 0:
        return rgb
    L = _luma(rgb)
    hi = _smoothstep(0.62, 1.0, L)                   # rodilla: nada antes de 0.62
    bright = rgb * hi[..., None]
    sigma = max(6.0, max(rgb.shape[:2]) * preset.bloom_radius)

    # Halation por canal: en pelicula la capa roja esta mas cerca de la base, asi que
    # el halo se derrama mas en rojo y menos en azul. Se emula con radios distintos.
    radii = (1.22, 1.0, 0.82)                        # R, G, B
    glow = np.empty_like(rgb)
    for c in range(3):
        g1 = _gauss(bright[..., c], sigma * radii[c])
        g2 = _gauss(bright[..., c], sigma * 2.6 * radii[c])
        glow[..., c] = g1 * 0.65 + g2 * 0.35

    warm = np.array([1.0, 0.94, 0.86], dtype=np.float32)
    glow = glow * (1 - preset.bloom_warmth) + glow * warm * preset.bloom_warmth
    out = _screen(rgb, np.clip(glow, 0, 1), preset.bloom)
    # el bloom no debe levantar el fondo negro: limita por la luminancia local
    floor = _smoothstep(0.03, 0.22, L)[..., None]
    return np.clip(rgb + (out - rgb) * floor, 0, 1)


def micro_detail(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Separacion de frecuencias ligera: devuelve textura sin aplanar (piel, tinta, tela)."""
    if amount <= 0:
        return rgb
    L = _luma(rgb)
    low = _gauss(L, max(1.6, min(rgb.shape[:2]) * 0.0035))
    keep = 0.10 + 0.90 * _smoothstep(0.10, 0.55, L)   # no levantar ruido en el fondo negro
    return _apply_luma(rgb, np.clip(L + (L - low) * amount * 1.1 * keep, 0, 1))


def grade(rgb: np.ndarray, preset: Preset) -> np.ndarray:
    L = _luma(rgb)
    out = rgb.copy()

    # split toning: sombras frias / luces calidas
    if preset.split_amount > 0:
        # solo medios tonos: los negros puros quedan neutros (fondo limpio, sin cast)
        w_s = _smoothstep(0.02, 0.16, L) * (1 - _smoothstep(0.10, 0.50, L)) * preset.split_amount
        w_h = _smoothstep(0.50, 1.0, L) * preset.split_amount
        for i in range(3):
            out[..., i] += (preset.shadow_tint[i] - 0.5) * w_s * 0.11
            out[..., i] += (preset.highlight_tint[i] - 0.5) * w_h * 0.16

    # vibrance (mas en colores apagados) + saturacion global
    mx, mn = out.max(axis=2), out.min(axis=2)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    vigor = 1.0 + preset.vibrance * (1.0 - np.clip(sat, 0, 1))
    gray = _luma(out)[..., None]
    out = gray + (out - gray) * vigor[..., None]
    out = gray + (out - gray) * preset.saturation

    # micro-calidez de piel: solo en medios tonos calidos (no toca fondos frios)
    if preset.saturation > 0:
        skin = _smoothstep(0.14, 0.40, L) * (1 - _smoothstep(0.62, 0.92, L))
        warm = np.array([1.014, 1.004, 0.986], dtype=np.float32)
        out = out * (1.0 + (warm - 1.0) * skin[..., None] * 1.0)

    return np.clip(out, 0, 1)


def grain_and_vignette(rgb: np.ndarray, preset: Preset, seed: int = 7) -> np.ndarray:
    h, w = rgb.shape[:2]
    L = _luma(rgb)
    out = rgb

    # viñeteo optico suave (no circular duro)
    if preset.vignette > 0:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx / w - 0.5) * 1.02) ** 2 + ((yy / h - 0.5) * 0.92) ** 2)
        v = 1.0 - _smoothstep(0.28, 0.95, r) * preset.vignette
        out = out * v[..., None]

    # grano: gaussiano, mas visible en medios tonos, casi nulo en negros puros
    if preset.grain > 0:
        rng = np.random.default_rng(seed)
        n = rng.normal(0, 1, (h, w)).astype(np.float32)
        n = _gauss(np.stack([n] * 3, -1), 0.8)[..., 0]
        wg = _smoothstep(0.02, 0.30, L) * (1 - 0.65 * _smoothstep(0.75, 1.0, L))
        out = out + n[..., None] * preset.grain * wg[..., None]
    return np.clip(out, 0, 1)


def highlight_rolloff(rgb: np.ndarray, start: float = 0.80, strength: float = 0.30) -> np.ndarray:
    """Retoque final de luces: un pelin de densidad extra en el ultimo tramo."""
    L = _luma(rgb)
    knee = _smoothstep(start, 1.0, L)
    head = 1.0 - strength * 0.16 * knee ** 1.5
    return _apply_luma(rgb, np.clip(L * head, 0, 1))


def sharpening(rgb: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return rgb
    L = _luma(rgb)
    blur = _gauss(L, 1.0)
    detail = L - blur
    # umbral: por debajo de ~1.5% de diferencia se considera ruido y no se toca
    thr = 0.015
    gate = _smoothstep(thr, thr * 3.0, np.abs(detail))
    edges = np.abs(_gauss(L, 2.5) - L)
    m = (0.30 + 0.70 * _smoothstep(0.004, 0.05, edges)) * gate
    return _apply_luma(rgb, np.clip(L + detail * amount * 1.6 * m, 0, 1))


# ----------------------------------------------------------------------------- marca
def _is_monochrome(logo: Image.Image, tol: float = 0.06) -> bool:
    """True si el logo es basicamente una sola tinta (se puede recolorear sin traicionarlo).

    Una insignia a color (crema + verde + marron) NO se toca: se usa tal cual.
    """
    a = np.asarray(logo.convert("RGBA")).astype(np.float32) / 255.0
    m = a[..., 3] > 0.35
    if m.sum() < 50:
        return True
    px = a[m][:, :3]
    lum = px.mean(axis=1)
    sat = px.max(axis=1) - px.min(axis=1)
    # saturacion media baja y luminancia concentrada -> monotinta
    # monotinta = una sola tinta sobre transparente: saturacion baja y luminancia uniforme
    return (float(np.percentile(sat, 90)) < tol
            and float(np.percentile(lum, 90) - np.percentile(lum, 10)) < 0.12)


def _fit_logo(logo: Image.Image, target_w: int) -> Image.Image:
    r = target_w / logo.size[0]
    return logo.resize((int(target_w), max(1, int(logo.size[1] * r))), Image.LANCZOS)


def composite_logo(rgb: np.ndarray, logo_path: str, pos: str = "auto",
                   width_frac: float = 0.20, margin_frac: float = 0.055,
                   scrim: bool = True, glow: bool = True, blend: str = "auto",
                   tint: str = "auto") -> tuple[np.ndarray, dict]:
    """Integra la marca de forma profesional:

    1. elige color de tinta segun la luminancia local del fondo (contraste garantizado)
    2. escala por fraccion del ancho (consistencia entre piezas del set)
    3. sombra proyectada suave -> asienta la marca en la escena (no 'pegada')
    4. scrim local opcional solo si el fondo es sucio (garantiza legibilidad sin cajas)
    """
    h, w = rgb.shape[:2]
    base_raw = Image.open(logo_path).convert("RGBA")
    # un logo cuadrado (insignia) se escala por el lado corto del encuadre, no por el ancho:
    # asi no se vuelve gigante en formatos horizontales ni diminuto en 9:16
    square = abs(base_raw.width / max(base_raw.height, 1) - 1.0) < 0.08
    ref = min(w, h) if square else w
    base = base_raw
    tw = int(ref * width_frac)
    # legibilidad: por debajo de ~9 px de altura de texto, se prefiere la marca sola
    if tw < 300 and "compact" not in logo_path and "_mark" not in logo_path:
        alt = logo_path.replace(".png", "").replace("logo_", "logo_compact_") + ".png"
        if os.path.exists(alt):
            base, logo_path = Image.open(alt).convert("RGBA"), alt
    elif tw < 150:
        alt = logo_path.replace("logo_", "logo_mark_").split("_compact")[0] + ".png"
        if os.path.exists(alt):
            base, logo_path = Image.open(alt).convert("RGBA"), alt
    lg = _fit_logo(base, tw)
    lw, lh = lg.size
    mx = int(w * margin_frac)
    my = int(h * margin_frac * 0.75)

    # 0) posicion automatica: la esquina mas 'tranquila' (oscura y pareja) para que la
    #    marca nunca caiga sobre el tatuaje ni sobre una zona de alto detalle
    if pos == "auto":
        best, best_score = "br", 1e9
        for cand, (cx, cy) in {"br": (w - mx - lw, h - my - lh), "bl": (mx, h - my - lh),
                               "tr": (w - mx - lw, my), "tl": (mx, my)}.items():
            p_ = rgb[max(0, cy):cy + lh, max(0, cx):cx + lw]
            if p_.size == 0:
                continue
            score = float(_luma(p_).mean()) + 1.6 * float(np.std(_luma(p_)))
            if score < best_score - 1e-4:
                best, best_score = cand, score
        pos = best

    px, py = {
        "tl": (mx, my), "tr": (w - mx - lw, my),
        "bl": (mx, h - my - lh), "br": (w - mx - lw, h - my - lh),
        "bc": ((w - lw) // 2, h - my - lh),
        "tc": ((w - lw) // 2, my),
    }[pos]

    # 1) luminancia del fondo bajo la marca
    patch = rgb[max(0, py):py + lh, max(0, px):px + lw]
    bg_l = float(_luma(patch).mean()) if patch.size else 0.1

    # 2) color: una insignia a color se respeta tal cual; solo se recolorea si es monotinta
    mono = _is_monochrome(lg)
    do_tint = (tint == "always") or (tint == "auto" and mono)
    if do_tint:
        ink = Image.new("RGBA", (lw, lh), (245, 242, 235, 255) if bg_l < 0.55
                        else (16, 16, 16, 255))
        tinted = Image.composite(ink, Image.new("RGBA", (lw, lh), (0, 0, 0, 0)), lg.split()[-1])
    else:
        tinted = lg.copy()

    canvas = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).convert("RGBA")

    # 3) modo de fusion: 'screen' funde el disco oscuro de la insignia con el negro
    #    (las lineas claras sobreviven) sin 'caja' visible; 'normal' deja la insignia solida
    mode = blend
    if mode == "auto":
        # screen solo para marcas monotinta sin disco propio (lineas sobre transparente):
        # en una insignia a color, screen deja pasar la textura del fondo y ensucia el sello
        mode = "screen" if (not do_tint) else "normal"
    if mode == "screen":
        canvas0 = np.asarray(canvas.convert("RGB"), dtype=np.float32) / 255.0
        y0, x0 = max(0, py), max(0, px)
        lgt = np.asarray(tinted.convert("RGB"), dtype=np.float32) / 255.0
        al = np.asarray(tinted.split()[-1], dtype=np.float32)[..., None] / 255.0
        hh, ww = lgt.shape[:2]
        y1, x1 = min(h, y0 + hh), min(w, x0 + ww)
        lgt = lgt[:y1 - y0, :x1 - x0]
        al = al[:y1 - y0, :x1 - x0]
        reg = canvas0[y0:y1, x0:x1]
        scr = 1.0 - (1.0 - reg) * (1.0 - lgt)
        canvas0[y0:y1, x0:x1] = reg + (scr - reg) * al
        canvas = Image.fromarray((np.clip(canvas0, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    else:
        # la capa normal se compone mas abajo (necesita sombra y halo previos)
        pass

    # 4) scrim: solo cuando el fondo bajo la marca es sucio (si es negro limpio, no se usa)
    if scrim:
        bg_noise = float(np.std(_luma(patch))) if patch.size else 0.0
        scrim = bg_noise > 0.045
    if scrim:
        # gradiente radial analitico (sin escalones) + dither para evitar banding en JPEG
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = px + lw / 2.0, py + lh / 2.0
        rx, ry = max(lw * 0.72, 40.0), max(lh * 1.55, 30.0)
        d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        g = 1.0 - _smoothstep(0.35, 1.45, d)
        g = g ** 1.35 * 0.42
        rng = np.random.default_rng(11)
        dith = (rng.random((h, w)).astype(np.float32) - 0.5) / 255.0
        g = np.clip(g + dith, 0, 1)[..., None]
        canvas_arr = np.asarray(canvas.convert('RGB'), dtype=np.float32) / 255.0
        darkened = canvas_arr * (1.0 - g) + np.array([0.012, 0.012, 0.014], np.float32) * g
        canvas = Image.fromarray((np.clip(darkened, 0, 1) * 255).astype(np.uint8)).convert('RGBA')

    # 3) sombra proyectada + halo de asentamiento
    alpha = tinted.split()[-1]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (lw, lh), (0, 0, 0, 255))
    sh.putalpha(alpha.point(lambda v: int(v * 0.55)))
    shadow.paste(sh, (px, py + max(2, lh // 12)), sh)
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(3, lw * 0.022)))
    canvas = Image.alpha_composite(canvas, shadow)

    if glow and bg_l < 0.42:
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        hb = Image.new("RGBA", (lw, lh), (255, 246, 232, 255))
        hb.putalpha(alpha.point(lambda v: int(v * 0.22)))
        halo.paste(hb, (px, py), hb)
        halo = halo.filter(ImageFilter.GaussianBlur(max(4, lw * 0.03)))
        canvas = Image.alpha_composite(canvas, halo)

    if mode != "screen":
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        layer.paste(tinted, (px, py), tinted)
        canvas = Image.alpha_composite(canvas, layer)

    meta = {"logo": os.path.relpath(logo_path, ROOT) if os.path.isabs(logo_path) else logo_path,
            "pos": pos, "size_px": lw, "square": square, "ref": "short-side" if square else "width",
            "monochrome": bool(mono), "tint": "ivory" if (do_tint and bg_l < 0.55)
            else ("ink" if do_tint else "original"),
            "blend": mode, "bg_luma": round(bg_l, 3),
            "bg_noise": round(float(np.std(_luma(patch))), 4),
            "scrim": bool(scrim), "halo": bool(glow and bg_l < 0.42)}
    return _f(np.asarray(canvas.convert("RGB"), dtype=np.uint8)), meta


# ----------------------------------------------------------------------------- pipeline
def retouch(path: str, out_path: str, preset: Preset, logo: str | None = None,
            logo_pos: str = "auto", logo_width: float = 0.20, seed: int = 7,
            crop: str | None = None, save_png: bool = False,
            logo_blend: str = "auto", logo_tint: str = "auto") -> dict:
    im = _load(path)
    src_size = im.size
    if crop:
        tw, th = (int(v) for v in crop.lower().split("x"))
        im = ImageOps.fit(im, (tw, th), method=Image.LANCZOS, centering=(0.5, 0.42))
    if preset.upscale > 1:
        im = im.resize((im.size[0] * preset.upscale, im.size[1] * preset.upscale), Image.LANCZOS)

    rgb = _f(np.asarray(im))
    stats_in = analyze(rgb)

    # 02 balance de blancos + exposicion medida sobre el sujeto
    rgb = white_balance(rgb, 0.22)
    rgb = highlight_recovery(rgb)          # protege el techo antes de exponer
    meter = meter_subject(rgb)  # medicion sobre sujeto
    ev = float(np.log2(preset.key_tone / max(meter["key_tone"], 1e-3))) * 0.55
    ev = float(np.clip(ev, -preset.ev_limit, preset.ev_limit)) + preset.exposure
    rgb = apply_exposure(rgb, ev)

    # 03-10 cadena
    rgb = tone_curve(rgb, preset.contrast, preset.black_density)
    rgb = local_contrast(rgb, preset.clarity)
    rgb = sculpture_3d(rgb, preset.sculpture)
    rgb = dodge_burn(rgb, preset, seed)
    rgb = micro_detail(rgb, preset.micro_contrast)
    rgb = bloom(rgb, preset)
    rgb = grade(rgb, preset)
    rgb = highlight_rolloff(rgb)
    rgb = sharpening(rgb, preset.sharpness)
    rgb = grain_and_vignette(rgb, preset, seed)

    logo_meta = None
    if logo:
        lp = logo if os.path.isabs(logo) else os.path.join(ROOT, logo)
        rgb, logo_meta = composite_logo(rgb, lp, logo_pos, logo_width,
                                        blend=logo_blend, tint=logo_tint)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    out = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    if save_png or out_path.lower().endswith(".png"):
        Image.fromarray(out).save(out_path, optimize=True)
    else:
        Image.fromarray(out).save(out_path, quality=95, subsampling=1, optimize=True,
                                  progressive=True)

    return {"in": os.path.relpath(path, ROOT) if os.path.isabs(path) else path,
            "out": out_path, "source_size": list(src_size),
            "output_size": [out.shape[1], out.shape[0]],
            "exposure_ev": round(ev, 3), "meter_in": meter, "preset": preset.name,
            "analysis_in": stats_in, "analysis_out": analyze(_f(out)),
            "logo": logo_meta}


def build_contact_sheet(items: list[tuple[str, str]], out_path: str, cols: int = 2,
                        pad: int = 24, bg=(12, 12, 13)):
    """Hoja de contacto antes/despues para revisar el set de un vistazo."""
    tiles = []
    for before, after in items:
        b = Image.open(before).convert("RGB")
        a = Image.open(after).convert("RGB")
        hgt = 900
        b = b.resize((int(b.width * hgt / b.height), hgt), Image.LANCZOS)
        a = a.resize((int(a.width * hgt / a.height), hgt), Image.LANCZOS)
        tile = Image.new("RGB", (b.width + a.width + 8, hgt), (30, 30, 32))
        tile.paste(b, (0, 0)); tile.paste(a, (b.width + 8, 0))
        tiles.append(tile)
    if not tiles:
        return
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad), bg)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + pad), pad + r * (th + pad)))
    sheet.save(out_path, quality=92)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Retoque editorial profesional por lotes.")
    ap.add_argument("target", help="archivo o carpeta")
    ap.add_argument("--out", default="out", help="archivo o carpeta de salida")
    ap.add_argument("--preset", default="editorial", choices=sorted(PRESETS))
    ap.add_argument("--logo", default=None,
                    help="PNG del logo. Recomendado: assets/brand/abyss_knockout.png")
    ap.add_argument("--logo-pos", default="auto",
                    choices=["auto", "tl", "tr", "bl", "br", "bc", "tc"],
                    help="auto = esquina mas tranquila (oscura y pareja) del encuadre")
    ap.add_argument("--logo-width", type=float, default=0.20,
                    help="tamano del logo. En insignias cuadradas se mide sobre el lado "
                         "corto del encuadre (0.18-0.22 es el rango profesional)")
    ap.add_argument("--logo-blend", default="auto", choices=["auto", "normal", "screen"],
                    help="screen funde el disco oscuro de la insignia con el fondo negro")
    ap.add_argument("--logo-tint", default="auto", choices=["auto", "always", "never"],
                    help="auto recolorea solo logos monotinta; never respeta el color original")
    ap.add_argument("--crop", default=None, help="recorte final, ej. 1200x1500 o 1080x1920")
    ap.add_argument("--png", action="store_true", help="exportar PNG en vez de JPEG")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--report", default=None, help="ruta del JSON con el registro de ajustes")
    ap.add_argument("--sheet", default=None, help="hoja de contacto antes/despues (JPEG)")
    ap.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR",
                    help="ajusta una perilla del preset, ej. --set sculpture=0.55 "
                         "--set black_density=0.40 (repetible)")
    ap.add_argument("--list-presets", action="store_true")
    args = ap.parse_args(argv)

    if args.list_presets:
        for k, p in PRESETS.items():
            print(f"{k:10s}", json.dumps(asdict(p), indent=None)[:120], "...")
        return 0

    preset = copy.deepcopy(PRESETS[args.preset])
    for item in args.set:
        if "=" not in item:
            ap.error(f"--set espera CLAVE=VALOR, se recibio: {item}")
        k, v = item.split("=", 1)
        k = k.strip()
        if not hasattr(preset, k):
            ap.error(f"perilla desconocida: {k}. Disponibles: {', '.join(asdict(preset))}")
        actual = getattr(preset, k)
        try:
            setattr(preset, k, type(actual)(v) if not isinstance(actual, tuple)
                    else tuple(float(x) for x in v.split(",")))
        except ValueError:
            ap.error(f"valor invalido para {k}: {v}")
    files: list[str] = []
    if os.path.isdir(args.target):
        for name in sorted(os.listdir(args.target)):
            if os.path.splitext(name)[1].lower() in SUPPORTED:
                files.append(os.path.join(args.target, name))
        os.makedirs(args.out, exist_ok=True)
    else:
        files = [args.target]

    records, sheet_items = [], []
    for f in files:
        if os.path.isdir(args.target):
            stem = os.path.splitext(os.path.basename(f))[0]
            ext = ".png" if args.png else ".jpg"
            out = os.path.join(args.out, f"{stem}_retouched{ext}")
        else:
            out = args.out if os.path.splitext(args.out)[1] else os.path.join(args.out,
                                                                            os.path.basename(f))
        rec = retouch(f, out, preset, args.logo, args.logo_pos, args.logo_width,
                      args.seed, args.crop, args.png, args.logo_blend, args.logo_tint)
        records.append(rec)
        sheet_items.append((f, out))
        print(f"[ok] {os.path.basename(f)} -> {out}  ({rec['output_size'][0]}x{rec['output_size'][1]})")

    if args.sheet and sheet_items:
        build_contact_sheet(sheet_items, args.sheet)
        print("hoja:", args.sheet)
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"preset": asdict(preset), "images": records}, fh, indent=2, ensure_ascii=False)
        print("reporte:", args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

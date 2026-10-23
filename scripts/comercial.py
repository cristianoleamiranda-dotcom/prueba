#!/usr/bin/env python3
"""
comercial.py — arma un comercial "fast pacing" con el material real del estudio.

No usa generacion por IA: compone movimiento de camara (push-in, paneo, reveal),
grade consistente, bloom, grano y cortes con flash sobre las fotos ya editadas de
`entregas/`. El cierre es la insignia sobre negro.

Salida: MP4 H.264 + pista de ambiente procedural (reemplazable en post).

Uso:
  python3 scripts/comercial.py --format 9x16 --out entregas/comercial_9x16.mp4
  python3 scripts/comercial.py --format 4x5  --out entregas/comercial_4x5.mp4
  python3 scripts/comercial.py --no-audio          # video mudo, para montar musica propia
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import imageio_ffmpeg

    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # pragma: no cover
    FFMPEG = "ffmpeg"

FORMATS = {"9x16": (1080, 1920), "4x5": (1080, 1350), "16x9": (1920, 1080)}

# (archivo, movimiento, duracion, corrimiento del encuadre x/y)
# El corrimiento aleja el recorte de la esquina donde la foto lleva la insignia: en video
# la marca va una sola vez, al final. Si no, aparece duplicada y recortada en cada plano.
# Tomas SIN insignia horneada (`entregas/_video_src`): en video la marca va fija una sola
# vez sobre todo el clip, no repetida en cada foto.
SHOTS = [
    ("trabajo_hombro_real.jpg", "in", 3.0, (0.0, 0.0)),
    ("plate_p05_color_anime.jpg", "right", 2.4, (0.0, 0.0)),
    ("proceso_hombro.jpg", "in_fast", 2.0, (0.0, 0.0)),
    ("septum.jpg", "up", 2.4, (0.0, 0.0)),
    ("trabajo_lobo_rugido.jpg", "out", 2.6, (0.0, 0.0)),
    ("plate_p08_vitrina_estudio.jpg", "left", 2.2, (0.0, 0.0)),
    ("trabajo_cristo_manga.jpg", "in", 2.4, (0.0, 0.0)),
    ("__LOGO__", "logo", 2.6, (0.0, 0.0)),
]


# ----------------------------------------------------------------------------- utilidades
def easet(t: float) -> float:
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def _cover_crop(im: Image.Image, W: int, H: int, zoom: float, dx: float, dy: float) -> Image.Image:
    """Recorta cubriendo el marco con zoom y desplazamiento normalizado."""
    ar = W / H
    if im.width / im.height > ar:          # fuente mas ancha: limitada por alto
        ch = im.height / zoom
        cw = ch * ar
    else:
        cw = im.width / zoom
        ch = cw / ar
    cw, ch = min(cw, im.width), min(ch, im.height)
    cx = im.width * 0.5 + dx * im.width * 0.5
    cy = im.height * 0.5 + dy * im.height * 0.5
    x0 = float(np.clip(cx - cw / 2, 0, im.width - cw))
    y0 = float(np.clip(cy - ch / 2, 0, im.height - ch))
    return im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BICUBIC)


def _vignette(W: int, H: int, strength: float = 0.42) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx / W - 0.5) * 1.03) ** 2 + ((yy / H - 0.5) * 0.94) ** 2)
    t = np.clip((r - 0.26) / 0.62, 0, 1)
    t = t * t * (3 - 2 * t)
    return (1.0 - strength * t).astype(np.float32)[..., None]


def _grade(rgb: np.ndarray) -> np.ndarray:
    """Look consistente con la entrega fotografica: negros densos, piel calida."""
    x = rgb
    s = x + 0.16 * (x - 1) * x * (2 * x - 1)          # S suave
    # calidez en luces, frio contenido en sombras
    L = s[..., 0] * 0.2126 + s[..., 1] * 0.7152 + s[..., 2] * 0.0722
    hi = np.clip((L - 0.55) / 0.45, 0, 1)[..., None]
    sh = np.clip((0.35 - L) / 0.35, 0, 1)[..., None]
    s = s + hi * np.array([0.020, 0.008, -0.012], np.float32)
    s = s + sh * np.array([-0.004, 0.000, 0.010], np.float32)
    return np.clip(s, 0, 1)


def _bloom(rgb: np.ndarray, amt: float = 0.18) -> np.ndarray:
    L = rgb.max(axis=2, keepdims=True)
    hi = np.clip((L - 0.72) / 0.28, 0, 1) * rgb
    small = Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(max(2, rgb.shape[1] // 140)))
    g = np.asarray(small, dtype=np.float32) / 255.0
    return np.clip(rgb + g * amt, 0, 1)


def _grain(W: int, H: int, rng: np.random.Generator, amt: float = 0.018) -> np.ndarray:
    n = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize(
        (W, H), Image.BILINEAR), dtype=np.float32) / 255.0 - 0.5
    return (n * amt * 2.0)[..., None]


def _ease_shot(kind: str, t: float) -> tuple[float, float, float]:
    """Devuelve (zoom, dx, dy) para el progreso t de un plano."""
    e = easet(t)
    if kind == "in":
        return lerp(1.0, 1.12, e), lerp(0.0, 0.02, e), lerp(0.0, -0.015, e)
    if kind == "in_fast":
        return lerp(1.03, 1.22, e), 0.0, lerp(0.0, -0.025, e)
    if kind == "out":
        return lerp(1.14, 1.0, e), lerp(-0.015, 0.0, e), 0.0
    if kind == "left":
        return 1.10, lerp(0.07, -0.07, e), 0.0
    if kind == "right":
        return 1.10, lerp(-0.07, 0.07, e), 0.0
    if kind == "up":
        return 1.10, 0.0, lerp(0.06, -0.06, e)
    if kind == "down":
        return 1.12, 0.0, lerp(-0.09, 0.09, e)
    return 1.0, 0.0, 0.0


# ----------------------------------------------------------------------------- encuadre
def build_board(fmt: str) -> tuple[list[dict], float]:
    W, H = FORMATS[fmt]
    shots = []
    total = 0.0
    for name, move, dur, off in SHOTS:
        shots.append({"name": name, "move": move, "dur": dur, "start": total, "off": off})
        total += dur
    return shots, total


def render(fmt: str, fps: int, out_path: str, with_audio: bool) -> str:
    W, H = FORMATS[fmt]
    shots, total = build_board(fmt)
    n_frames = int(round(total * fps))
    rng = np.random.default_rng(7)
    vig = _vignette(W, H)
    logo = Image.open(os.path.join(ROOT, "assets", "brand", "abyss_knockout.png")).convert("RGBA")
    # marca fija del clip: 7% del lado corto, abajo-izquierda, a media opacidad
    cs = int(min(W, H) * 0.075)
    cl = logo.resize((cs, int(logo.height * cs / logo.width)), Image.LANCZOS)
    ca = cl.split()[-1].point(lambda v: int(v * 0.62))
    cl.putalpha(ca)
    cpos = (int(W * 0.055), H - cl.height - int(H * 0.035))

    # precarga de fuentes
    for s in shots:
        p = os.path.join(ROOT, "entregas", "_video_src", s["name"])
        s["src"] = Image.open(p).convert("RGB") if os.path.exists(p) else None
        if s["move"] != "logo" and s["src"] is None:
            raise SystemExit(f"falta {p}")

    cmd = [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)

    cut_frames = {int(round(s["start"] * fps)) for s in shots[1:]}
    for f in range(n_frames):
        t_abs = f / fps
        shot = next((s for s in shots if s["start"] <= t_abs < s["start"] + s["dur"]), shots[-1])
        t = min(1.0, (t_abs - shot["start"]) / shot["dur"])

        if shot["move"] == "logo":
            # cierre: insignia sobre negro, escala lenta + halo
            e = easet(min(1.0, t))
            arr = np.zeros((H, W, 3), np.float32)
            ls = int(min(W, H) * (0.42 + 0.03 * e))
            lg = logo.resize((ls, int(logo.height * ls / logo.width)), Image.LANCZOS)
            canvas = Image.new("RGB", (W, H), (8, 8, 9))
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            g2 = lg.copy()
            a = g2.split()[-1].point(lambda v: int(v * 0.20))
            g2.putalpha(a)
            glow.paste(g2, ((W - lg.width) // 2, (H - lg.height) // 2), g2)
            glow = glow.filter(ImageFilter.GaussianBlur(24))
            canvas = Image.alpha_composite(canvas.convert("RGBA"), glow)
            canvas = Image.alpha_composite(canvas, Image.new("RGBA", (W, H), (0, 0, 0, 0)))
            frame_img = canvas.convert("RGB")
            frame_img.paste(lg, ((W - lg.width) // 2, (H - lg.height) // 2), lg)
            arr = np.asarray(frame_img, dtype=np.float32) / 255.0
        else:
            zoom, dx, dy = _ease_shot(shot["move"], t)
            dx += shot["off"][0]
            dy += shot["off"][1]
            img = _cover_crop(shot["src"], W, H, zoom, dx, dy)
            arr = np.asarray(img, dtype=np.float32) / 255.0
            arr = _bloom(_grade(arr))
            arr = arr * vig

        # flash de corte (2 frames): pulso de luz, no un fundido
        if (f in cut_frames or f - 1 in cut_frames) and shot["move"] != "logo":
            arr = np.clip(arr + 0.10, 0, 1)

        arr = np.clip(arr + _grain(W, H, rng), 0, 1)
        if shot["move"] != "logo":
            fi_ = Image.fromarray((arr * 255).astype(np.uint8)).convert("RGBA")
            fi_.alpha_composite(cl, cpos)
            arr = np.asarray(fi_.convert("RGB"), dtype=np.float32) / 255.0
        proc.stdin.write((arr * 255).astype(np.uint8).tobytes())
        if f % 48 == 0:
            print(f"  {fmt} {f}/{n_frames}", end="\r", flush=True)

    proc.stdin.close()
    err = proc.stderr.read().decode(errors="ignore")
    if proc.wait() != 0:
        print(err[-2000:])
        raise SystemExit("ffmpeg fallo en video")

    if with_audio:
        wav = out_path.replace(".mp4", "_audio.wav")
        make_audio(wav, total, cut_frames, fps)
        tmp = out_path.replace(".mp4", "_mux.mp4")
        r = subprocess.run([FFMPEG, "-y", "-i", out_path, "-i", wav, "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k", "-shortest",
                            "-movflags", "+faststart", tmp],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-1500:])
            raise SystemExit("ffmpeg fallo en audio")
        os.replace(tmp, out_path)
        os.remove(wav)
    print(f"  {fmt} listo: {n_frames} frames, {total:.1f}s")
    return out_path


# ----------------------------------------------------------------------------- audio
def make_audio(path: str, dur: float, cut_frames: set[int], fps: int, sr: int = 48000):
    """Ambiente procedural: drone grave + aire + golpes suaves en los cortes.

    Pensado como colchon para que el corte no quede mudo; en post se reemplaza por
    musica y SFX reales (aguja, guantes, ambiente de estudio).
    """
    n = int(dur * sr)
    tt = np.arange(n) / sr
    t_cut = np.array(sorted(f / fps for f in cut_frames))

    # drone: dos senos graves con LFO lento
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * tt)
    drone = (0.16 * np.sin(2 * np.pi * 55 * tt) +
             0.09 * np.sin(2 * np.pi * 82.5 * tt + 1.2) +
             0.05 * np.sin(2 * np.pi * 110 * tt))
    drone *= (0.55 + 0.45 * lfo)

    # aire: ruido filtrado (media movil larga = pasa bajos simple)
    noise = np.random.default_rng(3).normal(0, 1, n)
    k = 900
    kernel = np.ones(k) / k
    air = np.convolve(noise, kernel, mode="same") * 3.0
    air *= (0.25 + 0.20 * np.sin(2 * np.pi * 0.11 * tt + 0.7))

    # golpes en los cortes: seno corto + ruido con envolvente
    hits = np.zeros(n)
    for tc in t_cut:
        i0 = int(tc * sr)
        ln = int(0.20 * sr)
        if i0 + ln >= n:
            continue
        env = np.exp(-np.linspace(0, 7, ln))
        seg = (0.22 * np.sin(2 * np.pi * 62 * np.arange(ln) / sr) +
               0.10 * np.random.default_rng(int(tc * 100)).normal(0, 1, ln))
        hits[i0:i0 + ln] += seg * env

    mix = drone * 0.55 + air * 0.5 + hits * 0.85
    # fade in/out
    fi = int(0.6 * sr)
    mix[:fi] *= np.linspace(0, 1, fi)
    fo = int(1.2 * sr)
    mix[-fo:] *= np.linspace(1, 0, fo)
    peak = np.max(np.abs(mix)) or 1.0
    mix = mix / peak * 0.62
    stereo = np.stack([mix, np.roll(mix, 37)], axis=1) * 0.9
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def poster(fmt: str, out_path: str):
    """Frame de portada para el feed (thumbnail del video)."""
    W, H = FORMATS[fmt]
    src = Image.open(os.path.join(ROOT, "entregas", "feed",
                                  "trabajo_hombro_real_retouched.jpg")).convert("RGB")
    img = _cover_crop(src, W, H, 1.06, 0.0, -0.01)
    arr = _bloom(_grade(np.asarray(img, np.float32) / 255.0))
    arr = arr * _vignette(W, H)
    canvas = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    lg = Image.open(os.path.join(ROOT, "assets", "brand", "abyss_knockout.png")).convert("RGBA")
    ls = int(min(W, H) * 0.20)
    lg = lg.resize((ls, int(lg.height * ls / lg.width)), Image.LANCZOS)
    canvas.alpha_composite(lg, (int(W * 0.06), H - lg.height - int(H * 0.05)))
    canvas.convert("RGB").save(out_path, quality=94, subsampling=1)
    print("poster:", os.path.relpath(out_path, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="9x16", choices=sorted(FORMATS))
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--poster", action="store_true", help="genera tambien la portada")
    args = ap.parse_args()

    out = args.out or os.path.join(ROOT, "entregas", f"comercial_{args.format}.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    render(args.format, args.fps, out, not args.no_audio)
    size = os.path.getsize(out) / 1e6
    print(f"video: {os.path.relpath(out, ROOT)}  ({size:.1f} MB)")
    if args.poster:
        poster(args.format, out.replace(".mp4", "_poster.jpg"))


if __name__ == "__main__":
    sys.exit(main())

# Dark Editorial Retouch — estudio de tatuaje

Sistema de retoque fotografico profesional en **clave baja editorial** (negros densos,
piel calida, relieve 3D, brillos con halation, profundidad) + integracion de marca sin
texto, para fotos de tatuajes y producto sobre fondo oscuro.

Todo corre local, sin servicios de nube: numpy + scipy + Pillow.

---

## Que hay aca

```
skills/dark-editorial-retouch/
├── SKILL.md                      # la skill (formato Anthropic Agent Skills)
└── references/
    ├── pipeline.md               # las 11 etapas del motor, con la matematica
    ├── light-and-depth.md        # 3D, luz clave, bloom/halation, rolloff, clave baja
    ├── motion-language.md        # como se traduce "motion design" a un still
    ├── logo-integration.md       # las 7 reglas de marca sobre fotografia
    └── github-skills-research.md # que se tomo de cada repo de GitHub
scripts/
├── retouch.py                    # motor de retoque por lotes (+ marca integrada)
├── make_logo.py                  # genera el logo (9 PNG + SVG)
└── fetch_links.sh                # baja los links de tmpfiles a incoming/
assets/brand/                     # logo en 3 tintas x 3 formatos (+ SVG)
examples/demo/                    # pruebas editoriales (con marca)
examples/demo_motion/             # pruebas con preset motion (marca en oro)
links.txt                         # los 12 enlaces entregados
```

## Instalacion

```bash
make install          # numpy, scipy, pillow, pillow-heif (HEIC de iPhone)
make brand            # regenera el logo
```

## Flujo con las fotos reales

```bash
make fetch                              # descarga links.txt -> incoming/
make feed                               # 4:5 1080x1350, preset editorial
make story                              # 9:16 1080x1920, preset motion
```

O manual, con control total:

```bash
# una sola foto: 1080x1350 con logo abajo-izquierda
python3 scripts/retouch.py incoming/foto.heif --out out/foto.jpg \
        --crop 1080x1350 --preset editorial \
        --logo assets/brand/logo_ivory.png --logo-pos bl --logo-width 0.30

# lote + hoja de contacto + reporte auditable
python3 scripts/retouch.py incoming --out out \
        --preset motion --crop 1080x1350 \
        --logo assets/brand/logo_ivory.png \
        --sheet out/_contacto.jpg --report out/_reporte.json
```

### Presets

| Preset | Uso | Caracter |
|---|---|---|
| `editorial` | entrega principal | negro profundo, piel calida, relieve marcado |
| `motion` | stories / reels still | mas contraste, bloom y viñeteo, grano fino |
| `clean` | muestra a cliente | natural, sin grano, brillos contenidos |
| `noir` | blanco y negro | separacion tonal, grano 0.034 |

### Perillas que importan

`--preset` define el look base. Para afinar una sesion se edita `PRESETS` en
`scripts/retouch.py`:

- `sculpture` — cuanto volumen 3D (el parametro que mas cambia el resultado)
- `black_density` — que tan negro queda el fondo
- `bloom` / `bloom_radius` — derrame de luz en los bordes iluminados
- `dodge` / `burn` / `key_light` — direccion e intensidad de la luz clave
- `clarity` / `micro_contrast` — textura fina (cuidado: alto = plastico)
- `grain` — textura filmica (evita el aspecto render)
- `logo-width`, `--logo-pos` — tamano y esquina de la marca

## Salida

- JPEG q95, 4:2:2, sRGB. `--png` para PNG.
- El original nunca se sobreescribe.
- `--report json` registra por imagen: EV aplicado, medicion de entrada/salida
  (p01/p50/p99, clipping, cast), decision de marca (tinta, scrim, halo, ancho en px).
  Sirve para auditar la serie y repetir la entrega.

## Checklist antes de publicar

1. Fondo negro de verdad (p5 < 0.04) y sin tinte.
2. Ninguna zona plana quemada (p99 < 1.0 salvo especulares puntuales).
3. Piel con poro al 100% de zoom.
4. El relieve se logro con luz, no con contraste global.
5. Logo legible (alto de texto >= 9 px) y siempre en la misma esquina de la serie.
6. Cero texto en la imagen.

Detalle de cada punto en `skills/dark-editorial-retouch/SKILL.md`.

## Marca

`assets/brand/` trae el lockup completo (marca + nombre + ciudad + hairlines) en tres
tintas (`ivory`, `gold`, `ink`), version `compact` (sin subtitulo) y `mark` (solo
simbolo). La marca es una **aguja dentro de un rombo dentro de un circulo**: lee como
tinta + precision y sobrevive a 40 px.

`composite_logo()` decide solo: si el lockup quedaria por debajo de 300 px de ancho usa
`compact`; bajo 150 px usa `mark`. Elige tinta midiendo la luminancia del fondo y solo
agrega scrim si ese parche tiene ruido. Reglas y fundamentos en
`skills/dark-editorial-retouch/references/logo-integration.md`.

Cambiar el nombre del estudio:

```bash
python3 scripts/make_logo.py --name "TU ESTUDIO" --sub "CIUDAD · PAIS"
```

## Pruebas incluidas

`examples/demo/` y `examples/demo_motion/` son resultados reales del motor sobre dos
bases de prueba (foto de antebrazo con tatuaje), para ver el salto antes/despues sin
depender de los links externos.

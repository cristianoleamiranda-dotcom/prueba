---
name: dark-editorial-retouch
description: Retoque fotografico profesional en clave baja (tattoo / editorial oscuro) con efecto 3D, brillos, profundidad, balance de luz, grano filmico e integracion de marca sin texto. Usa esta skill cuando haya que tratar fotos de tatuajes, piel, cuero o producto sobre fondo negro y entregar piezas de feed/story con logotipo integrado.
license: uso libre en este repositorio
---

# Dark Editorial Retouch

Sistema para convertir fotos planas de estudio en piezas de **clave baja editorial**
(negros densos, piel calida, relieve 3D, brillos controlados) con la marca del estudio
integrada de forma invisible. Todo se ejecuta sin dependencias de nube: `scripts/retouch.py`.

## Cuando usar esta skill

- Fotos de tatuajes, retratos o producto con fondo oscuro / negro.
- Piezas para Instagram (feed 4:5, story 9:16) con logo del estudio.
- Series donde hay que mantener **consistencia** entre 5-50 imagenes.
- Cuando el pedido dice "que se vea 3D", "mas profundidad", "brillos", "cinematografico".

## Regla de oro (lo que separa pro de aficionado)

> El look oscuro **no se logra bajando el brillo**. Se logra subiendo la relacion
> señal/ruido del sujeto y hundiendo el fondo. Un fondo negro con el sujeto bien
> expuesto se lee como premium; un fondo gris con todo quemado se lee como filtro.

## Flujo en 11 etapas (orden no negociable)

| # | Etapa | Funcion en `retouch.py` | Perilla |
|---|-------|--------------------------|---------|
| 01 | Lectura + EXIF + HEIC | `_load` | — |
| 02 | Balance de blancos robusto | `white_balance` | ±8% de ganancia |
| 03 | Recuperacion de luces | `highlight_recovery` | umbral 0.88 |
| 04 | Medicion por sujeto | `meter_subject` | `key_tone` 0.60 |
| 05 | Exposicion protegida | `apply_exposure` | `ev_limit` 0.55 |
| 06 | Curva filmica | `tone_curve` | `contrast`, `black_density` |
| 07 | Claridad local | `local_contrast` | `clarity` |
| 08 | Escultura 3D | `sculpture_3d` | `sculpture` |
| 09 | Dodge & burn | `dodge_burn` | `dodge`, `burn`, `key_light` |
| 10 | Brillo / bloom | `bloom` | `bloom`, `bloom_radius` |
| 11 | Grade + grano + marca | `grade`, `grain_and_vignette`, `composite_logo` | `split_amount`, `grain` |

Detalle tecnico de cada etapa: `references/pipeline.md`.
Psicologia de la luz y del 3D: `references/light-and-depth.md`.
Lectura "motion design": `references/motion-language.md`.
Marca: `references/logo-integration.md`.

## Uso rapido

```bash
# una foto, look editorial con logo
python3 scripts/retouch.py foto.jpg --out out/ --preset editorial \
        --logo assets/brand/logo_ivory.png --logo-width 0.32

# lote completo, recorte 4:5 para feed + hoja de contacto + reporte
python3 scripts/retouch.py ./fotos --out ./out --preset motion \
        --crop 1080x1350 --logo assets/brand/logo_ivory.png \
        --sheet out/_contacto.jpg --report out/_reporte.json

# variantes de entrega
--preset editorial   # look de referencia (equilibrado)
--preset motion      # mas contraste, bloom y viñeteo: "still" de video
--preset clean       # entrega natural, sin grano
--preset noir        # blanco y negro con separacion tonal
```

## Invariantes de calidad (checklist antes de entregar)

1. **El fondo negro es negro**: p5 de luminancia < 0.04 y sin tinte de color.
2. **Ninguna zona plana quemada**: p99 < 1.0 salvo especulares puntuales (<0.2% del area).
3. **La piel conserva poro**: si al 100% se ve plastico, se bajo `micro_contrast` o se subio `bloom`.
4. **El relieve viene de la luz, no del contraste global**: subir `sculpture`, no `contrast`.
5. **El logo se lee**: alto de texto >= 9 px en el archivo final; si no, usar variante compacta.
6. **El logo no flota**: sombra proyectada suave o halo, nunca caja ni rectangulo de color.
7. **Consistencia**: mismo `--width` de logo y mismo preset en toda la serie.
8. **Sin texto**: si el pedido dice "sin textos", no se agrega copy; el logo es la unica marca.

## Errores frecuentes y su sintoma

| Sintoma | Causa | Correccion |
|---|---|---|
| Parches grises planos en el brazo | exponer con multiplicador puro | `apply_exposure` (asintotica) |
| Motas naranja/cian en la piel | filtros aplicados por canal RGB | trabajar en luminancia (`_apply_luma`) |
| Fondo lavado / gris | `black_density` bajo o viñeteo insuficiente | subir `black_density` a 0.35-0.42 |
| Sujeto oscuro y fondo ruidoso | medicion por promedio del encuadre | `meter_subject` (descarta fondo) |
| Look "IA plastico" | bloom alto + micro detalle alto | bajar ambos 30% y subir grano a 0.03 |
| Bandas en el degradado del scrim | gradiente por anillos discretos | gradiente analitico + dither |
| Logo ilegible | escalado por fraccion del ancho en imagen chica | variante compacta o marca sola |

## Salida

- JPEG calidad 95, subsampling 4:2:2 (o PNG con `--png`).
- `sRGB` 8 bits; el original jamas se sobreescribe.
- `_reporte.json` con EV aplicado, medicion de entrada/salida, decision de logo y
  metricas de clipping: permite auditar y replicar la entrega.

# Marca: integrar el logo sin que parezca pegado

Objetivo: que la marca pertenezca a la imagen. Un logo que "flota" o que esta metido en
una caja semitransparente abarata la pieza; uno bien integrado se lee como firma de autor.

## Las 7 reglas (con la investigacion detras)

1. **Esquina primero, centro nunca.** Las esquinas enmarcan sin competir con el sujeto.
   Bottom-right es el estandar de watermark (el ojo termina ahi: se lee como firma);
   bottom-left funciona cuando el sujeto ocupa la derecha. El centro es para portadas.
2. **5-20% del ancho de la imagen.** Referencias de fotografia profesional coinciden en
   5-10% para marcas discretas y 10-20% para marca de estudio. En este sistema:
   `--logo-width 0.28` para el lockup con texto (el ancho del *lockup* incluye margen),
   `0.10-0.15` para la marca sola. Lo que importa no es la fraccion sino la
   **altura tipografica final**: >= 9 px en el archivo entregado.
3. **Zona tranquila.** El logo va donde no hay informacion: negro limpio, pared lisa,
   fondo desenfocado. Nunca sobre el tatuaje ni sobre el punto de mayor interes.
4. **Espacio de resguardo = 1x la altura del elemento principal** de la marca, en los
   cuatro lados. Implementado como `margin_frac` relativo al encuadre, no en pixeles fijos.
5. **Contraste garantizado.** Si el fondo bajo la marca es oscuro → tinta hueso; si es
   claro → tinta negra. `composite_logo()` lo decide midiendo la luminancia de ese parche
   (`bg_luma < 0.55`). Nunca se usa el logo de color sobre fotografia.
6. **Sin cajas.** Si hace falta separar del fondo, se usa un **scrim radial** suave
   (gradiente + dither, no un rectangulo) y solo cuando el fondo tiene ruido
   (`bg_noise > 0.045`). Sobre negro limpio el scrim se omite: la caja se nota.
7. **Asentamiento fisico.** Sombra proyectada suave (desplazada ~8% de la altura del logo,
   desenfoque ~2% del ancho) + un halo calido muy tenue cuando el fondo es negro. Eso
   integra la marca a la escena en lugar de superponerla.

## Consistencia de serie

En una serie de 10-30 fotos, la marca debe estar **en el mismo lugar y del mismo
tamano**. Por eso el sistema usa fracciones del encuadre (no pixeles) y una sola
decision por lote:

```bash
python3 scripts/retouch.py ./fotos --out ./out --preset editorial \
        --logo assets/brand/logo_ivory.png --logo-pos bl --logo-width 0.28
```

El `_reporte.json` registra `pos`, `width_px`, `ink`, `bg_luma`, `scrim` y `halo` por
imagen: si una foto se desvia (por ejemplo, la marca cambia a tinta oscura porque el
fondo se aclaro), se detecta en el reporte antes de publicar.

## Variantes del archivo de marca

| Archivo | Uso | Ancho minimo |
|---|---|---|
| `logo_ivory.png` | lockup completo sobre fotos oscuras | 480 px (relativo: `0.28`) |
| `logo_gold.png` | acento premium, sobre negro absoluto | 480 px |
| `logo_ink.png` | sobre fondos claros / papel | 480 px |
| `logo_compact_ivory.png` | solo marca + nombre, encuadres apretados | 240 px |
| `logo_mark_ivory.png` | sello, favicon, avatar, story | 120 px |
| `logo.svg` | vectorial, para imprenta o web | — |

`composite_logo()` hace el cambio de variante solo: si el lockup quedaria por debajo de
300 px de ancho usa `compact`, y por debajo de 150 px usa la marca sola. Asi nunca se
entrega un logo ilegible por accidente.

## Regenerar la marca

```bash
python3 scripts/make_logo.py --name "ESTUDIO TINTA" --sub "SANTIAGO · CHILE" --width 2400
```

Produce las 9 variantes PNG (ivory / gold / ink × lockup / compact / mark) y el SVG.
La marca es una aguja dentro de un rombo dentro de un circulo: lectura = tinta +
precision, geometria dura, legible a 40 px. El lockup usa serif con tracking amplio
(autoridad) + sans con tracking mayor en el subtitulo (direccion de arte editorial).

## Errores que se notan de inmediato

- Logo con transparencia sobre zona de alto detalle (se ensucia).
- Logo blanco al 100% sobre zona con textura clara: pierde bordes.
- Logo mas grande del 25% del ancho: compite y grita "watermark".
- Marca distinta de posicion entre fotos del mismo carrusel.
- Sombra dura/negra tipo "drop shadow" de PowerPoint: usar siempre desenfoque amplio y
  opacidad baja.

# Flujo de comerciales con IA — adaptado a ABYSS

> Basado en **"Cómo Crear COMERCIALES DE AGENCIA Con IA (Flujo De TRABAJO ACTUALIZADO)"**
> de Scalboost (Aslet Daniel), YouTube, 4 sep 2026 · 9:26 · 165k vistas.
> https://youtu.be/ldhp1WwVM2s
> Prompts originales publicados por el autor: https://www.scalboost.ai/guia/prompts-comerciales-ia

El video **no tiene subtítulos** (verificado: el reproductor no expone pista de texto), así que
esto sale de los capítulos, la descripción y la guía de prompts del propio autor — que
contiene los 8 prompts completos. Se cita la fuente de cada dato al final.

---

## 1. Resumen del video

Tesis: **un comercial de agencia con IA no se genera, se dirige.** El modelo de video (Seedance
2.5) ya sostiene 30 s en una sola pasada con audio nativo y hasta 50 referencias; lo que falla
es la falta de dirección. El flujo son 5 niveles, cada uno apoyado en el anterior:

| Nivel | Qué se hace | Herramienta del video |
|---|---|---|
| 1 | **Moodboard**: decidir qué historia se cuenta (eligió "detrás de escena" de una fábrica) | Pinterest, 10-15 refs, *fast pacing* |
| 2 | **Ficha de producto**: un documento visual que congela el producto | Claude redacta → GPT Image 2 dibuja |
| 3 | **Construcción de tomas**: una imagen por ángulo, siempre con la ficha + la ref anterior | GPT Image 2 |
| 4 | **Dirección**: un solo prompt que cuenta el comercial con tus palabras | Claude |
| 5 | **Animación**: prueba en baja resolución, corrige, recién ahí 1080p | Seedance 2.5 |

Los tres trucos que sostienen todo:

1. **La ficha.** Evita que el producto cambie entre tomas. Es el paso que casi todos se saltean.
2. **La frase fija.** Las 4 referencias terminan con las mismas palabras ("fábrica oscura
   desenfocada, luz suave de lado, poca profundidad de campo, foto de producto cinematográfica").
   Eso es lo que hace que parezcan del mismo comercial.
3. **Prueba barata primero.** Baja resolución para validar cámara, acciones y consistencia;
   después se paga el render final.

---

## 2. Lo que cambia en nuestro caso

El video resuelve **producto** (una gorra). Nosotros tenemos **piel, tinta y metal**: otra
categoría de problema. Tres diferencias que obligan a adaptar el flujo:

| Producto (video) | ABYSS (nuestro material) |
|---|---|
| El producto es idéntico en cada toma → se congela con ficha | El "producto" es **un tatuaje terminado**, que ya existe: se congela con la foto real, no con una ficha generada |
| Fondo de fábrica inventado | El entorno **existe y es nuestro**: el estudio, la fachada, la vitrina (ya fotografiados) |
| Cualquier persona en el cierre sirve | El cierre debe ser **el maestro real**, y su rostro no se inventa: se usa una foto con permiso |
| Producto sin movimiento propio | Piel y aguja **tienen micro-movimiento**: eso es lo que hay que dirigir |

Traducción: no necesitamos generar la ficha desde cero — **ya la tenemos**. `scripts/ficha.py`
la arma con nuestro material editado (`entregas/`) y la deja lista como referencia única.

---

## 3. Flujo ABYSS (5 niveles, adaptado)

### Nivel 0 — Inventario (nuevo, no está en el video)

Antes de cualquier prompt: saber qué tenemos. En este repo ya está resuelto:

```bash
make paquete SRC=incoming OUT=entregas     # edita + marca
python3 scripts/ficha.py                   # arma la ficha con las entregas
```

Salida: `entregas/ficha_abyss.jpg` — hero, 4 vistas, 3 macros, paleta con hex y reglas de
consistencia. Esa imagen es **la referencia única** de todo lo que sigue.

### Nivel 1 — Moodboard (igual que el video, pero con nuestro entorno)

- Buscar en Pinterest: `tattoo studio behind the scenes`, `tattoo process macro`, `black and
  grey realism close up`, `piercing macro titanium`.
- Guardar 10-15 referencias. Mirar el **ritmo**: los que funcionan son *fast pacing*, cortes
  rápidos, mucho macro.
- Fijar el entorno de toda la pieza: **estudio oscuro, pared texturada, luz lateral cálida**.
  Esa frase se repite en todos los prompts.

### Nivel 2 — Ficha (ya construida)

`entregas/ficha_abyss.jpg`. Si cambia el material (nuevo trabajo), se regenera con
`python3 scripts/ficha.py`. Regla: **toda generación posterior adjunta la ficha**.

### Nivel 3 — Construcción de tomas (4 imágenes base)

Cada toma se genera con **la ficha + la toma anterior** como referencias. Orden recomendado
para tatuaje (de lo general a lo íntimo):

| # | Toma | Qué debe mostrar | Prompt base |
|---|---|---|---|
| 01 | **Hero 3/4** | el trabajo completo, brazo/hombro, fondo negro | ver `prompts.md` §T1 |
| 02 | **Macro de tinta** | línea, relleno, saturación del negro | §T2 |
| 03 | **Proceso** | aguja, piel, guantes, gota de tinta | §T3 |
| 04 | **Entorno / cierre** | estudio, vitrina, fachada o el maestro trabajando | §T4 |

Cada prompt cierra con la **frase fija ABYSS**:

```
estudio oscuro con pared texturada desenfocada, luz lateral suave y cálida,
poca profundidad de campo, foto editorial de estudio de tatuaje, sin texto
```

### Nivel 4 — Dirección (un prompt, tus palabras)

Se le pasa a Claude una captura con las 4 referencias y se cuenta el comercial en lenguaje
normal. La estructura de 6 líneas que funciona: **ritmo, estilo, secuencia, cierre, formato,
reglas**. Plantilla lista en `prompts.md` §D1. Para ABYSS los formatos que importan son 9:16
(reels/stories) y 4:5 (feed), no 16:9.

### Nivel 5 — Animación (con control de créditos)

Regla del video, y es la más importante: **no se renderiza en alta hasta validar en baja**.

```
1. Seedance 2.5 en 480p, 9:16, 30 s máx.
2. Revisar: ¿la cámara sigue lo que pedí? ¿la tinta se mantiene? ¿el cierre se entiende?
3. Corregir el prompt con Claude (plantilla §D2), mantener todo lo demás igual.
4. Recién ahí: 1080p.
5. Edición: SFX (aguja, zumbido de máquina), música, y variantes del mismo clip.
```

**Advertencia técnica verificada:** varias fuentes secundarias reportan la salida de la API de
Seedance 2.5 en **480p/720p a 24 fps**, no 4K, aunque el anuncio prometía 4K y la ficha de
consumidor (Dreamina) lo publicite. Planificar la entrega sabiendo que puede requerir un
paso de escalado o un modelo distinto para 1080p real. Verificar en la plataforma que uses
antes de cotizar.

---

## 4. Recursos y conocimiento (qué usar y por qué)

### Modelos

| Modelo | Qué aporta | Por qué importa acá |
|---|---|---|
| **GPT Image 2** (`gpt-image-2`, OpenAI, 21 abr 2026) | hasta 16 imágenes de referencia; texto en imagen ~95-99% de precisión; 1K/2K/4K; hasta 8 imágenes coherentes por prompt | es lo que hace posible la ficha y las tomas consistentes; el texto exacto importa porque la insignia dice "ABYSS / TATTOO Y PIERCING" |
| **Seedance 2.5** (ByteDance Seed, lanzamiento 31 jul 2026) | 30 s en una pasada, audio-video nativo, hasta 50 referencias (30 img + 10 video + 10 audio), edición por timestamp, extensión multironda | permite un comercial completo sin coser clips; el audio nativo ahorra la mitad del trabajo de edición |
| **Claude** | redacta y corrige los prompts | el video insiste: el modelo no dirige solo, alguien tiene que escribir la dirección |

### Skills de GitHub útiles (verificadas en el repo)

- **`anthropics/skills` → `canvas-design`**: el criterio de "tesis visual antes de ejecutar"
  es exactamente lo que pide el Nivel 1. Ya aplicado en este repo.
- **`anthropics/skills` → `brand-guidelines`**: la ficha es, en el fondo, un brand guideline
  visual. Nuestro `scripts/ficha.py` sigue esa lógica (paleta + tipografía + reglas).
- **`remotion-dev/skills`**: si el comercial se programa en vez de generarse (o para los
  overlays, el logo animado y las variantes en lote), Remotion cubre el render determinista.
  Es la alternativa cuando la IA no mantiene un elemento fijo.
- **`vercel-labs/skills`**: convención de `references/` para no inflar el prompt principal.

### Lo que NO se debe generar con IA en este flujo

- **El tatuaje.** Un tatuaje generado no es el trabajo de nadie: si aparece en el comercial,
  es publicidad engañosa. Se usa la foto real del trabajo (Nivel 0) y la IA solo anima cámara
  y luz alrededor.
- **El rostro del maestro** sin foto de referencia y permiso.
- **La insignia.** Ya existe en vectorial/PNG; se compone, no se genera.

---

## 5. Pipeline de archivos en este repo

```
incoming/                  fotos crudas (del repo abysstattoo o propias)
   → scripts/retouch.py    edición con presets feed / piel + insignia
entregas/feed, entregas/piel
   → scripts/ficha.py      ficha de marca (referencia única)
entregas/ficha_abyss.jpg   ← se adjunta a TODAS las generaciones
   → Nivel 1-4             moodboard, tomas, dirección  (prompts.md)
   → Nivel 5               Seedance 2.5: 480p → corrección → 1080p
```

Comandos:

```bash
make paquete SRC=incoming OUT=entregas   # 1. editar + marca
python3 scripts/ficha.py                 # 2. armar la ficha
```

---

## 6. Checklist antes de quemar créditos

- [ ] La ficha existe y se ve la insignia legible en miniatura.
- [ ] Las 4 tomas base están aprobadas **como imagen** antes de animar nada.
- [ ] El prompt de dirección tiene las 6 líneas (ritmo, estilo, secuencia, cierre, formato, reglas).
- [ ] La secuencia nombra cada toma y el orden en que aparece.
- [ ] Hay un cierre definido (inmersión, corte al maestro, plano del estudio).
- [ ] Formato fijado en el prompt (9:16 para reels, 4:5 para feed).
- [ ] Primera generación en 480p. **Siempre.**
- [ ] Cada corrección se hace sobre el prompt, no sobre el clip.
- [ ] El tatuaje que aparece es real, con su foto de origen trazable.

---

## 7. Fuentes

- Video y capítulos: https://youtu.be/ldhp1WwVM2s (Scalboost, 4 sep 2026)
- Prompts completos del autor (8 prompts, 5 niveles): https://www.scalboost.ai/guia/prompts-comerciales-ia
- Seedance 2.5, anuncio oficial: https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5
- Seedance 2.5, especificaciones y discrepancias de resolución: https://seedance2-video.com/seedance-2-5 · https://apiframe.ai/guides/seedance-2-5-guide
- GPT Image 2: https://www.mindstudio.ai/blog/what-is-gpt-image-2 · https://together.ai/models/gpt-image-2
- Halation/rolloff y criterio de retoque ya documentados en `skills/dark-editorial-retouch/references/`

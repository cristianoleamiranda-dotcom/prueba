# Prompts ABYSS — listos para copiar

Adaptados de los 8 prompts de Scalboost (https://www.scalboost.ai/guia/prompts-comerciales-ia)
al caso tatuaje/piercing. La estructura se mantiene; cambia el sujeto y el entorno.

**Regla de oro:** toda generación de imagen adjunta `entregas/ficha_abyss.jpg`. Toda
generación de video adjunta las 4 tomas base. Nada se genera "de memoria".

---

## FASE 1 · Ficha desde foto real (si hace falta una nueva)

> Usar cuando hay un trabajo nuevo que todavía no está en la ficha.

```
Look at the tattoo in the image I'm uploading and write me a prompt for a reference sheet.
I'll paste your output into an image model together with the same reference image, so the
prompt must describe the tattoo literally and completely — the image model will only get
right what you spell out.

STEP 1 — Study the tattoo before writing anything:
- Placement and body part, orientation, size relative to the limb.
- Style: black and grey realism / fine line / colour / ornamental. Say it plainly.
- Value structure: where the blacks are solid, where the greys sit, where the skin shows.
- Line work: thickness, whether shading is whip-shaded, dotwork or smooth gradient.
- Do not invent elements that are not visible.

STEP 2 — Identity anchors (the most important part):
- List the 5 features that make this piece recognisable and must stay identical in every panel.
- Transcribe any lettering EXACTLY as it appears, in double quotes, with its position,
  orientation, size and whether it is script or block.

STEP 3 — Write the prompt with this exact structure:
1. One-sentence identity of the piece.
2. Full description: placement, style, value structure, line work, greys.
3. Lettering and motifs, each transcribed in quotes.
4. Layout: one large hero at 3/4; front, side and detail views of the same arm; three to
   six macro insets; a strip of black/grey/skin swatches.
5. Consistency rules: identical tattoo in every panel, same lighting, dark textured
   background, no text added.
```

---

## FASE 2 · Las 4 tomas base (una imagen cada una)

Todas terminan con la **frase fija ABYSS**. Sin excepción: es lo que las vuelve del mismo
comercial.

### T1 · Hero 3/4

```
Crea una imagen del brazo/hombro con el tatuaje completo, desde un ángulo cercano a 3/4,
centrado y ocupando el 70% del encuadre. El fondo es el estudio oscuro con pared texturada
totalmente desenfocado, con luz lateral suave y cálida que marca el relieve del músculo.
Poca profundidad de campo, foto editorial de estudio de tatuaje, sin texto. 9:16.
```
Inputs: `ficha_abyss.jpg`

### T2 · Macro de tinta

```
Crea una imagen en macro extremo de una zona de relleno negro sólido y degradado gris.
Se ve el límite entre el negro y la piel: el borde del tatuaje, el poro, el vello fino y
el brillo especular tenue sobre la tinta. Un dedo enguantado en negro entra desenfocado
desde la esquina inferior. Fondo oscuro desenfocado con una luz cálida puntual.
Estudio oscuro con pared texturada desenfocada, luz lateral suave y cálida, poca
profundidad de campo, foto editorial de estudio de tatuaje, sin texto.
```
Inputs: ficha + T1

### T3 · Proceso (aguja sobre piel)

```
Crea una imagen en primer plano de una máquina de tatuar en pleno trabajo: la aguja toca
la piel, hay una gota de tinta negra y un rastro de vaselina. Se ven el guante negro, la
empuñadura metálica y el cable. La piel alrededor está enrojecida, con textura real.
Luz lateral marca el metal y el relieve de la aguja. Fondo desenfocado con bokeh cálido
y un rollo de papel de limpieza.
Estudio oscuro con pared texturada desenfocada, luz lateral suave y cálida, poca
profundidad de campo, foto editorial de estudio de tatuaje, sin texto.
```
Inputs: ficha + T1

### T4 · Entorno / cierre

```
Crea una imagen amplia del interior del estudio de tatuaje: sillón, lámpara articulada,
vitrina de joyería con piercing de titanio, paredes oscuras texturadas y una planta.
La luz es cálida y lateral, con polvo en suspensión. Un tatuador de espaldas trabaja,
desenfocado, en el tercio derecho del encuadre. Nada de texto en las paredes.
Estudio oscuro con pared texturada desenfocada, luz lateral suave y cálida, poca
profundidad de campo, foto editorial de estudio de tatuaje, sin texto.
```
Inputs: ficha + T1

**Las 4 tomas se aprueban como imagen antes de animar.** Es el filtro más barato del flujo.

---

## FASE 3 · Dirección del comercial

### D1 · Prompt de dirección (pasar a Claude con una captura de las 4 refs)

```
Te adjunto una captura con las 4 imágenes de referencia de mi estudio de tatuaje (ABYSS):
hero del trabajo, macro de tinta, proceso con la aguja y el entorno del estudio.
Escríbeme el prompt para generar el comercial en video con Seedance 2.5.

Cómo quiero el video:
- Ritmo: fast pacing, muy dinámico, cortes rápidos, ningún plano de más de 2 segundos.
- Estilo: tomas cinematográficas, macro extremo, luz lateral cálida, negro profundo.
- Secuencia: [1) el hero del brazo gira lentamente → 2) macro de la aguja entrando en la
  piel → 3) la tinta negra rellenando y el degradado gris apareciendo → 4) el tatuador
  limpiando la zona, plano medio → 5) el estudio en travelling lateral].
- Cierre: [una inmersión final al tatuaje terminado, que corta a negro].
- Formato: [vertical 9:16 para reels], [20] segundos.
- Audio: sin locución; solo sonido de máquina, guantes y ambiente de estudio.

Reglas: mantén el tatuaje idéntico a las referencias en todas las tomas (negro, grises y
lettering); describe movimientos de cámara concretos, la luz y el entorno (estudio oscuro,
pared texturada, luz lateral cálida); entrega el prompt final en un solo bloque listo
para pegar.
```

### D2 · Corrección después de la prueba en 480p

```
Esta es la prueba en baja resolución del comercial. Lo que no funciona:
[la cámara no sigue la aguja / el tatuaje cambia de forma / el corte final no se entiende].
Ajusta el prompt para que [la cámara haga un push-in lento hacia la aguja y termine en el
tatuaje completo]. Mantén todo lo demás igual y devuélveme el prompt completo corregido.
```

### D3 · Variantes del mismo clip (después de aprobar)

```
Con el mismo prompt y las mismas referencias, dame tres variantes que solo cambien:
1) el ritmo (más lento, planos de 3 s), 2) el cierre (corte al tatuador a cámara, sin
texto), 3) el formato (4:5 para feed). Devuelve tres prompts completos, uno por variante.
```

---

## FASE 4 · Reglas de marca dentro del video

| Elemento | Regla |
|---|---|
| Insignia | Se compone en post (`assets/brand/abyss_knockout.png`), **nunca** se genera |
| Posición | Esquina inferior o superior, 17-19% del lado corto (igual que en las fotos) |
| Texto | Cero texto en el video. La insignia ya dice el nombre |
| Paleta | La de la ficha: #181818, #A89090, #786060, #303030, #907878 |
| Tatuaje | Siempre real, con foto de origen trazable |

---

## Errores que salen caros

| Síntoma | Causa | Arreglo |
|---|---|---|
| El tatuaje "respira" y cambia entre tomas | no se adjuntó la ficha o se adjuntó una sola vez | ficha + toma anterior en **cada** generación |
| Las tomas parecen de comerciales distintos | falta la frase fija al final del prompt | repetirla literal |
| Se quema crédito en renders malos | se generó en 1080p sin prueba | 480p primero, siempre |
| El cierre no se entiende | no se pidió cierre | definir 1 cierre explícito en D1 |
| La aguja atraviesa la piel | el modelo no entiende física | pedir "la aguja toca la piel, sin atravesarla" |
| Manos con seis dedos | fuera de foco en el prompt | pedir "manos fuera de foco / solo guante" |

PY ?= python3
BRAND := assets/brand/abyss_knockout.png
SRC   ?= incoming
OUT   ?= out

.PHONY: help install brand demo fetch feed story paquete ficha all resumen clean

help:
	@echo "make install  - dependencias de python"
	@echo "make brand    - rearma el kit de marca desde assets/brand/abyss_source.png"
	@echo "make fetch    - descarga links.txt a incoming/"
	@echo "make feed     - lote 4:5 (1080x1350) con insignia  [preset editorial]"
	@echo "make story    - lote 9:16 (1080x1920) con insignia [preset motion]"
	@echo "make demo     - reprocesa las bases de ejemplo"
	@echo "make paquete  - feed+story+resumen desde SRC=<carpeta> (sin descargar nada)"
	@echo "make ficha    - ficha de marca (referencia unica para generar tomas con IA)"
	@echo "make all      - fetch + feed + story + resumen (entrega completa)"
	@echo "make resumen  - tabla de la ultima entrega (EV, esquina, tamano de insignia)"
	@echo "make clean    - borra out/"

install:
	$(PY) -m pip install --break-system-packages -q numpy scipy pillow pillow-heif

brand:
	$(PY) scripts/prepare_brand.py --src assets/brand/abyss_source.png --name abyss

fetch:
	bash scripts/fetch_links.sh links.txt

# 4:5 para feed: insignia en la esquina mas tranquila, 20% del lado corto
feed:
	$(PY) scripts/retouch.py $(SRC) --out $(OUT)/feed --preset editorial \
		--crop 1080x1350 --logo $(BRAND) --logo-pos auto --logo-width 0.20 \
		--sheet $(OUT)/_contacto_feed.jpg --report $(OUT)/_reporte_feed.json

# 9:16 para stories: mas contraste/bloom, marca arriba (zona segura de UI)
story:
	$(PY) scripts/retouch.py $(SRC) --out $(OUT)/story --preset motion \
		--crop 1080x1920 --logo $(BRAND) --logo-pos tl --logo-width 0.17 \
		--sheet $(OUT)/_contacto_story.jpg --report $(OUT)/_reporte_story.json

demo:
	$(PY) scripts/retouch.py examples/_demo_src --out examples/demo --preset editorial \
		--crop 1080x1350 --logo $(BRAND) --logo-pos auto --logo-width 0.20
	$(PY) scripts/retouch.py examples/_demo_src --out examples/demo_motion --preset motion \
		--crop 1080x1920 --logo $(BRAND) --logo-pos auto --logo-width 0.17

# ficha de marca: la referencia que se adjunta a toda generacion con IA
ficha:
	$(PY) scripts/ficha.py

# entrega de una carpeta ya disponible (fotos subidas al chat, o cualquier ruta)
paquete: feed story resumen

# entrega completa en un comando (descarga + procesa)
all: fetch feed story resumen

resumen:
	@$(PY) -c "import json,glob;\
print(f'{\"archivo\":34s} {\"salida\":12s} {\"EV\":>6s} {\"insignia\":>9s} {\"esquina\":>8s}');\
print(\"-\"*76);\
[print(f'{i[\"out\"].split(\"/\")[-1]:34s} {\"%dx%d\" % tuple(i[\"output_size\"]):12s} {i[\"exposure_ev\"]:>6.2f} {i[\"logo\"][\"size_px\"]:>9d} {i[\"logo\"][\"pos\"]:>8s}') for f in sorted(glob.glob(\"$(OUT)/_reporte_*.json\")) for i in json.load(open(f))[\"images\"]]" 2>/dev/null || echo "sin reportes en $(OUT)/ todavia"

clean:
	rm -rf $(OUT)

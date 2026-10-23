PY ?= python3
BRAND := assets/brand/abyss_knockout.png
SRC   ?= incoming
OUT   ?= out

.PHONY: help install brand demo fetch feed story clean

help:
	@echo "make install  - dependencias de python"
	@echo "make brand    - rearma el kit de marca desde assets/brand/abyss_source.png"
	@echo "make fetch    - descarga links.txt a incoming/"
	@echo "make feed     - lote 4:5 (1080x1350) con insignia  [preset editorial]"
	@echo "make story    - lote 9:16 (1080x1920) con insignia [preset motion]"
	@echo "make demo     - reprocesa las bases de ejemplo"
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

clean:
	rm -rf $(OUT)

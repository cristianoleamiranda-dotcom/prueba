PY ?= python3
BRAND := assets/brand/logo_ivory.png
SRC   ?= incoming
OUT   ?= out

.PHONY: help install brand demo fetch feed story clean

help:
	@echo "make install  - dependencias de python"
	@echo "make brand    - regenera el logo (9 PNG + SVG)"
	@echo "make fetch    - descarga links.txt a incoming/"
	@echo "make feed     - lote 4:5 (1080x1350) con logo  [preset editorial]"
	@echo "make story    - lote 9:16 (1080x1920) con logo [preset motion]"
	@echo "make demo     - reprocesa las bases de ejemplo en examples/"
	@echo "make clean    - borra out/"

install:
	$(PY) -m pip install --break-system-packages -q numpy scipy pillow pillow-heif

brand:
	$(PY) scripts/make_logo.py --name "ESTUDIO TINTA" --sub "SANTIAGO · CHILE"

fetch:
	bash scripts/fetch_links.sh links.txt

feed:
	$(PY) scripts/retouch.py $(SRC) --out $(OUT)/feed --preset editorial \
		--crop 1080x1350 --logo $(BRAND) --logo-pos bl --logo-width 0.30 \
		--sheet $(OUT)/_contacto_feed.jpg --report $(OUT)/_reporte_feed.json

story:
	$(PY) scripts/retouch.py $(SRC) --out $(OUT)/story --preset motion \
		--crop 1080x1920 --logo $(BRAND) --logo-pos tl --logo-width 0.26 \
		--sheet $(OUT)/_contacto_story.jpg --report $(OUT)/_reporte_story.json

demo:
	$(PY) scripts/retouch.py examples/_demo_src --out examples/demo --preset editorial \
		--logo $(BRAND) --logo-pos bl --logo-width 0.30
	$(PY) scripts/retouch.py examples/_demo_src --out examples/demo_motion --preset motion \
		--logo assets/brand/logo_gold.png --logo-pos tr --logo-width 0.30

clean:
	rm -rf $(OUT)

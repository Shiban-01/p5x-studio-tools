"""Comprueba que la ventana de dependencias existe, ensena el peso y que su consola es de solo
lectura (no hay dentro ningun campo donde escribir)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)

import webview  # noqa: E402
from p5x_studio import ajustes, dependencias, ui_web  # noqa: E402

peso_esperado = dependencias.peso_aproximado_mb()

ajustes.CACHE.mkdir(parents=True, exist_ok=True)
pagina = str(Path(RAIZ) / "p5x_studio" / "ui_web" / "index.html")
api = ui_web.Api()
w = webview.create_window("prueba deps", pagina, js_api=api, width=1180, height=700)
RES = {}


def trabajo():
    def js(expr, defecto=None):
        try:
            return w.evaluate_js(expr)
        except Exception:
            return defecto

    time.sleep(4)
    RES["boton_existe"] = js("!!document.querySelector('#deps-open')", False)
    if RES["boton_existe"]:
        js("document.querySelector('#deps-open').click()")
    time.sleep(1.5)
    RES["visible"] = js("(() => { const m=document.querySelector('#deps-modal'); return !!m && !m.hidden; })()", False)
    RES["peso"] = js("(document.querySelector('#deps-peso')||{}).textContent")
    RES["consola_tag"] = js("(document.querySelector('#deps-consola')||{}).tagName")
    RES["editables"] = js(
        "document.querySelectorAll('#deps-modal input, #deps-modal textarea, "
        "#deps-modal [contenteditable=true]').length", -1)
    RES["boton"] = js("(document.querySelector('#deps-bajar')||{}).textContent")
    RES["lista"] = js("document.querySelectorAll('#deps-lista li').length", 0)
    w.destroy()


webview.start(trabajo, gui="edgechromium")
comun.comprobar(RES.get("boton_existe") is True, "hay boton de dependencias en el riel")
comun.comprobar(RES.get("visible") is True, "el boton abre la ventana de dependencias")
comun.comprobar(str(peso_esperado) in (RES.get("peso") or ""),
                "la ventana dice el peso aproximado %s MB (%r)" % (peso_esperado, RES.get("peso")))
comun.comprobar(RES.get("consola_tag") == "PRE", "la consola es un <pre> (%r)" % RES.get("consola_tag"))
comun.comprobar(RES.get("editables") == 0,
                "no hay ningun campo editable en la ventana (%s)" % RES.get("editables"))
comun.comprobar("Download" in (RES.get("boton") or ""),
                "hay boton de descarga (%r)" % RES.get("boton"))
comun.comprobar(RES.get("lista") == 5, "la ventana lista las cinco piezas (%s)"
                % RES.get("lista"))
comun.resumen()

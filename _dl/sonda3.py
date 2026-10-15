import sys, time
from pathlib import Path
RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)
import webview
from p5x_studio import ajustes, ui_web
ajustes.CACHE.mkdir(parents=True, exist_ok=True)
pagina = str(Path(RAIZ) / "p5x_studio" / "ui_web" / "index.html")
api = ui_web.Api()
w = webview.create_window("sonda3", pagina, js_api=api, width=1180, height=700)
RES = {}
def trabajo():
    def js(e, d=None):
        try: return w.evaluate_js(e)
        except Exception as ex: return "EXC: %s" % ex
    time.sleep(5)
    js("document.querySelector('#deps-open').click()")
    time.sleep(2)
    RES["li"] = js("document.querySelectorAll('#deps-lista li').length")
    RES["peso"] = js("document.querySelector('#deps-peso').textContent")
    RES["estado"] = js("JSON.stringify(window.pywebview.api.estado_dependencias())")
    w.destroy()
webview.start(trabajo, gui="edgechromium")
for k, v in RES.items(): print("%-8s %s" % (k, str(v)[:400]))

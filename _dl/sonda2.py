import sys, time
from pathlib import Path
RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)
import webview
from p5x_studio import ajustes, ui_web
ajustes.CACHE.mkdir(parents=True, exist_ok=True)
pagina = str(Path(RAIZ) / "p5x_studio" / "ui_web" / "index.html")
api = ui_web.Api()
w = webview.create_window("sonda2", pagina, js_api=api, width=1180, height=700)
RES = {}
def trabajo():
    def js(e, d=None):
        try: return w.evaluate_js(e)
        except Exception as ex: return "EXC: %s" % ex
    time.sleep(4)
    RES["ids"] = js("JSON.stringify([...document.querySelectorAll('[id^=deps-]')].map(e=>e.id))")
    RES["es_null"] = js("document.querySelector('#deps-lista') === null")
    RES["por_id"] = js("JSON.stringify(document.getElementById('deps-lista') ? 'existe' : 'null')")
    RES["cuantos_lista"] = js("document.querySelectorAll('#deps-lista').length")
    RES["menu"] = js("document.querySelectorAll('ul').length")
    RES["tipo_dollar"] = js("typeof $")
    RES["dollar_lista"] = js("(() => { try { return String($('#deps-lista')); } catch(e){ return 'LANZA ' + e.message; } })()")
    w.destroy()
webview.start(trabajo, gui="edgechromium")
for k, v in RES.items(): print("%-14s %s" % (k, str(v)[:250]))

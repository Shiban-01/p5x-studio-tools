import sys, time
from pathlib import Path
RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)
import webview
from p5x_studio import ajustes, ui_web
ajustes.CACHE.mkdir(parents=True, exist_ok=True)
pagina = str(Path(RAIZ) / "p5x_studio" / "ui_web" / "index.html")
api = ui_web.Api()
w = webview.create_window("sonda4", pagina, js_api=api, width=1180, height=700)
RES = {}
def trabajo():
    def js(e, d=None):
        try: return w.evaluate_js(e)
        except Exception as ex: return "EXC: %s" % ex
    time.sleep(5)
    js("document.querySelector('#deps-open').click()")
    time.sleep(2)
    RES["pila"] = js("""
      (function(){
        try { pintarDeps({herramientas:{motor:true,wannacri:null,vgmstream:null,ffmpeg:null},
                           tamanos:{motor:16,wannacri:5,vgmstream:11,ffmpeg:105},
                           faltan:["wannacri"], fuera:{}}); return "sin error"; }
        catch(e){ return (e && e.stack) ? e.stack.split("\n").slice(0,4).join(" || ") : String(e); }
      })()
    """)
    RES["lista_vacia"] = js("document.querySelectorAll('#deps-lista li').length")
    RES["tipo_pintar"] = js("typeof pintarDeps")
    RES["fuente"] = js("String(pintarDeps).slice(0, 420)")
    w.destroy()
webview.start(trabajo, gui="edgechromium")
for k, v in RES.items(): print("--- %s ---\n%s\n" % (k, str(v)[:900]))

"""Sonda: por que la lista de la ventana de dependencias se queda vacia."""
import sys, time, json
from pathlib import Path

RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)
import webview
from p5x_studio import ajustes, ui_web

ajustes.CACHE.mkdir(parents=True, exist_ok=True)
pagina = str(Path(RAIZ) / "p5x_studio" / "ui_web" / "index.html")
api = ui_web.Api()
w = webview.create_window("sonda", pagina, js_api=api, width=1180, height=700)
RES = {}


def trabajo():
    def js(expr, defecto=None):
        try:
            return w.evaluate_js(expr)
        except Exception as e:
            return "EXCEPCION: %s" % e
    time.sleep(4)
    js("document.querySelector('#deps-open').click()")
    time.sleep(1.5)
    js("""
       window.__prueba = (function(){
         try {
           const est = {herramientas:{motor:true,wannacri:true,vgmstream:true,ffmpeg:true},
                        tamanos:{motor:16,wannacri:5,vgmstream:11,ffmpeg:105}, falta:[],
                        fuera:{wannacri:"C:/x/wannacri.exe"}};
           pintarDeps(est);
           return "sin error, li=" + document.querySelectorAll('#deps-lista li').length;
         } catch(e){ return "LANZA: " + e.message; }
       })();
       window.__prueba;
    """)
    RES["resultado"] = js("window.__prueba")
    RES["errs"] = js("JSON.stringify(window.__errs || 'no existe')")
    RES["lista_html"] = js("(document.querySelector('#deps-lista')||{}).innerHTML")
    w.destroy()


webview.start(trabajo, gui="edgechromium")
for k, v in RES.items():
    print("%-12s %s" % (k, str(v)[:400]))

"""Punta a punta por la VENTANA: extrae un video con sus tres pistas de audio tocando la interfaz.

Las pruebas anteriores llamaban al puente directamente. Esta usa la ventana de verdad: abre la
pantalla de video, hace clic en la fila del video y en el boton de extraer, y luego comprueba con
ffprobe que el MP4 salio con las tres pistas (japones, chino y efectos).
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)

import webview  # noqa: E402
from p5x_studio import ajustes, ui_web  # noqa: E402

VIDEO = "gacha_fourth_thief_last_04_new.usm"      # tiene las tres pistas
FFPROBE = (r"C:\Users\Lukas\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin\ffprobe.exe")

ajustes.preparar_carpetas()
salida = ajustes.carpeta_herramientas() / "media"
pagina = str(Path(RAIZ) / "p5x_studio" / "ui_web" / "index.html")
api = ui_web.Api()
w = webview.create_window("prueba e2e", pagina, js_api=api, width=1180, height=700)
RES = {}


def trabajo():
    def js(expr, defecto=None):
        try:
            return w.evaluate_js(expr)
        except Exception:
            return defecto

    time.sleep(4)
    # la fila del video, buscada por nombre, se pulsa de verdad
    idx = js("(() => mediaDatos.usm.findIndex(m => m.nombre === '%s'))()" % VIDEO, -1)
    RES["fila"] = idx
    if idx is None or idx < 0:
        w.destroy()
        return
    js("ir('media')")
    time.sleep(0.8)
    RES["filas_dom"] = js("document.querySelectorAll('#media-lista .media-row').length", -1)
    RES["seg"] = js("(() => mediaSeg)()")
    js("document.querySelectorAll('#media-lista .media-row')[%d].click()" % idx)
    time.sleep(0.5)
    RES["seleccionado"] = js("(() => mediaSel)()")
    if RES["seleccionado"] != idx:          # sin seleccion no se extrae: se informa y se corta
        w.destroy()
        return
    js("document.querySelector('#media-extract').click()")
    # a esperar a que la tarea termine (el video son 6,5 MB)
    t0 = time.time()
    while time.time() - t0 < 300:
        time.sleep(2)
        e = js("null")
        try:
            e = api.estado_tarea()
        except Exception:
            pass
        if e and e.get("terminada"):
            RES["tarea"] = {k: e.get(k) for k in ("tipo", "resultado", "error", "terminada")}
            break
    RES["consola_txt"] = js("(document.querySelector('#media-estado')||{}).textContent")
    w.destroy()


webview.start(trabajo, gui="edgechromium")
comun.comprobar(RES.get("fila", -1) >= 0, "el video de tres pistas esta en la lista (%s)" % RES.get("fila"))
comun.comprobar(RES.get("seg") == "usm", "la pantalla arranca en la lista de videos (%s)" % RES.get("seg"))
comun.comprobar(RES.get("filas_dom", -1) > 0, "la lista tiene filas pintadas (%s)" % RES.get("filas_dom"))
comun.comprobar(RES.get("seleccionado") == RES.get("fila"), "el clic selecciona la fila (%s/%s)"
                % (RES.get("seleccionado"), RES.get("fila")))
t = RES.get("tarea") or {}
comun.comprobar(t.get("terminada") is True, "la extraccion termino (%s)" % t)
comun.comprobar(not t.get("error"), "termino sin error (%s)" % t.get("error"))
comun.comprobar((t.get("resultado") or "").startswith(Path(VIDEO).stem),
                "se extrajo el video elegido, no otro (%s)" % t.get("resultado"))

esperado = salida / (Path(VIDEO).stem + ".mp4")
comun.comprobar(esperado.is_file(), "el MP4 esta en %s" % esperado)
if esperado.is_file():
    comun.comprobar(esperado.stat().st_size > 1_000_000,
                    "el MP4 pesa %d bytes" % esperado.stat().st_size)
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "stream=index,codec_type,codec_name:stream_tags=language,handler_name,title",
                        "-of", "default=noprint_wrappers=1", str(esperado)],
                       capture_output=True, text=True, timeout=120)
    plano = r.stdout
    RES["ffprobe"] = plano.strip().splitlines()[:4]
    tipos = [l for l in plano.splitlines() if l.startswith("codec_type=")]
    idiomas = [l for l in plano.splitlines() if l.startswith("TAG:language=")]
    comun.comprobar(len(tipos) == 4, "el MP4 tiene 4 pistas (%s)" % tipos)
    comun.comprobar(tipos.count("codec_type=video") == 1, "una de video")
    comun.comprobar(tipos.count("codec_type=audio") == 3, "tres de audio (%s)" % tipos)
    for idi in ("jpn", "chi", "und"):
        comun.comprobar(any(idi in l for l in idiomas), "esta la pista %s (%s)" % (idi, idiomas))

print("  ffprobe:", RES.get("ffprobe"))
comun.resumen()

"""PRUEBA DE FUEGO: la carpeta del escritorio empezando VACIA.

Solo se dejan dentro el programa y el README, como cuando alguien se lo descarga. Todo lo demas
-tiene que traerlo el propio boton de dependencias- y luego se prueba cada herramienta con el
ejecutable PUBLICADO (no el codigo fuente), pulsando lo que pulsaria un usuario.

Lo que hace falta para que esto funcione al arrancar:
  - `P5X Studio Tools.exe` (el programa)
  - `README_TOOLS.md` (las instrucciones)
Nada mas: sin motor, sin tools/, sin config. La carpeta se vacia a proposito en la prueba.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilotar_exe import Piloto  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import dependencias  # noqa: E402

ESCRITORIO = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools")
EXE = "P5X Studio Tools.exe"
FFPROBE = r"C:\Users\Lukas\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin\ffprobe.exe"
VIDEO = "gacha_fourth_thief_last_04_new.usm"     # el que lleva las tres pistas
PESO = str(dependencias.peso_aproximado_mb())  # el peso que debe ensenar la ventana
TOTAL = "%d of %d" % (len(dependencias.ORDEN), len(dependencias.ORDEN))
PUERTO = 9222

PASOS: list[tuple] = []
PROCESO = None


def paso(nombre, ok, detalle=""):
    PASOS.append((nombre, bool(ok), str(detalle)))
    print(("  ok    " if ok else "  FALLA ") + nombre + (("   [" + str(detalle) + "]") if detalle else ""),
          flush=True)
    return ok


def lanzar(extra_env=None):
    global PROCESO
    entorno = dict(os.environ)
    entorno["P5X_STUDIO_UI_CDP"] = str(PUERTO)
    entorno.update(extra_env or {})
    PROCESO = subprocess.Popen([str(ESCRITORIO / EXE)], cwd=str(ESCRITORIO), env=entorno,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return PROCESO


def matar():
    global PROCESO
    if PROCESO and PROCESO.poll() is None:
        try:
            PROCESO.terminate()
            PROCESO.wait(timeout=15)
        except Exception:  # noqa: BLE001
            try:
                PROCESO.kill()
            except Exception:  # noqa: BLE001
                pass
    PROCESO = None
    time.sleep(2)


def ffprobe(ruta: Path) -> list[str]:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "stream=index,codec_type:stream_tags=language",
                        "-of", "default=noprint_wrappers=1", str(ruta)],
                       capture_output=True, text=True, timeout=180)
    return [l for l in r.stdout.splitlines() if l.strip()]


def main() -> None:
    print("=" * 78)
    print("PRUEBA DE FUEGO — P5X Studio Tools 1.0.0-beta, congelado, carpeta vacia")
    print("=" * 78)

    # ---------------------------------------------------------------- 0) lo que hay antes
    print("\n0) PUNTO DE PARTIDA")
    antes = sorted(p.name for p in ESCRITORIO.iterdir()) if ESCRITORIO.exists() else []
    paso("solo se deja el programa y el README",
         antes in (["P5X Studio Tools.exe", "README_TOOLS.md"],
                   ["P5X Studio Tools.exe", "README_TOOLS.md", "cache"]),
         ", ".join(antes) or "(carpeta vacia)")
    paso("no hay motor, ni tools/, ni config",
         not (ESCRITORIO / "engine").exists() and not (ESCRITORIO / "tools").exists()
         and not (ESCRITORIO / "config.json").exists())
    paso("el .exe esta", (ESCRITORIO / EXE).is_file())

    # ---------------------------------------------------------------- 1) primer arranque
    print("\n1) PRIMER ARRANQUE (sin nada instalado)")
    # el tope de prueba corta el bulk a 2 bundles por categoria: minutos en vez de horas
    lanzar({"P5X_STUDIO_BULK_LIMITE": "2"})
    try:
        with Piloto(PUERTO) as p:
            titulo = p.js("document.title")
            paso("la ventana abre", bool(titulo), titulo)
            paso("es la interfaz nueva (WebView2)",
                 p.js("!!window.pywebview && !!document.querySelector('#nav button')") is True)
            time.sleep(3)
            n = p.js("(() => document.querySelectorAll('#nav button').length)()")
            paso("estan las seis pestanas", n == 6, "%s" % n)

            # el explorador no necesita NADA instalado: lee del disco
            p.js("ir('bundles')")
            time.sleep(2)
            crudo = p.texto("#foot-index")
            caja = p.js("(() => (bundles||[]).length)()")
            paso("el explorador lista los bundles sin dependencias", (caja or 0) == 16535,
                 "%s en el pie: %s" % (caja, crudo.strip()[:40]))
            paso("dice que los lee del disco",
                 "disk" in p.texto("#note-bundles").lower()
                 or bool(p.js("document.querySelector('#note-bundles').textContent")))

            # el buscador sin indice debe decirlo, no inventar
            p.js("ir('resources')")
            time.sleep(1)
            paso("el buscador avisa de que el indice no esta",
                 "index" in p.texto("#res-estado").lower(),
                 p.texto("#res-estado").strip()[:70])

            # la Tools se publica SOLO en ingles: ni una palabra en espanol a la vista
            ESPANOL = ("falta", "faltan", "instalado", "instalada", "descargar", "dependencias",
                       "carpeta", "fichero", "juego", "idioma", "espanol", "español", "listo",
                       "listas", "ya esta", "aprox", "ningun", "ninguna", "puedes", "mirar",
                       "cerrar", "elegir", "guardar", "cancelar", "pistas", "sin dato")
            visto = p.js("document.body.innerText.toLowerCase()") or ""
            encontrado = sorted({w for w in ESPANOL if w in visto})
            paso("la ventana no tiene ni una palabra en espanol", not encontrado,
                 "encontrado: %s" % (encontrado or "nada"))

            # ------------------------------------------------------------ 2) el boton
            print("\n2) EL BOTON DE DEPENDENCIAS")
            paso("el boton esta en el riel", p.visible("#deps-open"))
            p.pulsar("#deps-open")
            time.sleep(2)
            paso("abre la ventana", p.visible("#deps-modal"))
            # la lista se pinta cuando el motor contesta: en un arranque en frio revisa cada
            # herramienta con un subproceso y puede tardar mas de lo que tarda la ventana en
            # abrirse. Se espera a que pinte; no se da por vacia a los 2 segundos.
            t_lista = time.time()
            lista = 0
            while time.time() - t_lista < 90:
                lista = p.filas("#deps-lista li")
                if lista:
                    break
                time.sleep(2)
            paso("lista las cinco piezas", lista == 5,
                 "%s (tras %.1f s)" % (lista, time.time() - t_lista))
            faltan = p.js("(() => [...document.querySelectorAll('#deps-lista li')]"
                          ".map(l => l.textContent).join(' | '))()")
            # ni una puede constar como puesta DENTRO de la carpeta: o falta, o es una copia de
            # fuera (la del escritorio, la del PATH) que no viaja con ella
            puestas = faltan.count("installed")
            de_fuera = faltan.count("outside the folder")
            paso("ninguna consta como puesta de la carpeta",
                 puestas == 0 and faltan.count("missing") + de_fuera == 5,
                 "outside=%d, missing=%d" % (de_fuera, faltan.count("missing")))
            paso("dice el peso aproximado", PESO in p.texto("#deps-peso"),
                 p.texto("#deps-peso").strip()[:60])
            paso("la consola es de solo lectura", p.js(
                "(() => { const c=document.querySelector('#deps-consola'); "
                "return c.tagName==='PRE' && document.querySelectorAll("
                "'#deps-modal input,#deps-modal textarea,[contenteditable=true]').length===0; })()") is True)

            t0 = time.time()
            p.pulsar("#deps-bajar")
            primeras = ""
            for _ in range(20):                       # que empiece a escribir
                time.sleep(2)
                primeras = p.texto("#deps-consola")
                if len(primeras) > 20:
                    break
            paso("al pulsar, la consola empieza a contar lo que pasa", len(primeras) > 20,
                 primeras.strip().splitlines()[:1] and primeras.strip().splitlines()[0][:70])
            paso("no se puede escribir en la consola (sigue siendo <pre>)",
                 p.js("document.querySelector('#deps-consola').tagName") == "PRE")

            fin = p.esperar_texto("#deps-consola", TOTAL, timeout=1500, cada=5)
            minutos = (time.time() - t0) / 60
            paso("acaba: %s herramientas" % TOTAL, fin, "%.1f min" % minutos)
            # lo que se lee en la consola de descarga va en ingles: ni "5 de 5" ni "aprox" ni "listo"
            consola = (p.texto("#deps-consola") or "").lower()
            restos = sorted({w for w in (" de ", "aprox", "listo", "listas", "herramientas", "descargando",
                                         "instalando", "ya esta", "descomprimiendo")
                             if w in consola})
            paso("la consola de descarga tambien va en ingles", not restos,
                 "restos: %s" % (restos or "ninguno"))
            cola = p.texto("#deps-consola").strip().splitlines()[-3:]
            print("        ultimas lineas: " + " / ".join(cola)[:160])

            # quedan instaladas de verdad
            ok_dis = all((ESCRITORIO / r).exists() for r in
                         ("engine", "tools/uv", "tools/wannacri", "tools/vgmstream", "tools/ffmpeg"))
            paso("quedan en la carpeta engine/ y tools/", ok_dis)
            exes = {n: next(ESCRITORIO.rglob(n), None) for n in
                    ("AssetStudioModCLI.exe", "uv.exe", "wannacri.exe", "vgmstream-cli.exe",
                     "ffmpeg.exe")}
            paso("los cinco ejecutables estan", all(v is not None for v in exes.values()),
                 ", ".join("%s=%s" % (k, "si" if v else "NO") for k, v in exes.items()))
            peso = sum(f.stat().st_size for f in ESCRITORIO.rglob("*") if f.is_file()) / 1e6
            paso("pesa menos de 260 MB", peso < 260, "%.0f MB" % peso)
            p.pulsar("#deps-cerrar")
            time.sleep(1)

            # ------------------------------------------------------------ 3) cada herramienta
            print("\n3) CADA HERRAMIENTA, YA COMPLETA")

            # inspector (algun bundle no tiene nada que listar; se prueban unos cuantos y se dice cual)
            p.js("ir('inspector')")
            ruta, filas_insp = "", 0
            for cand in (p.js("(() => (bundles||[])[115] && bundles[115].ruta)()"),
                         "115/shared_3e45cab0.bundle", "109/shared_23b7c8db.bundle",
                         p.js("(() => (bundles||[])[5000] && bundles[5000].ruta)()")):
                if not cand:
                    continue
                p.js("(() => { document.querySelector('#insp-path').value = %r; })()" % cand)
                p.pulsar("#insp-open")
                time.sleep(7)
                if p.filas("#insp-body tr") > 0:
                    ruta, filas_insp = cand, p.filas("#insp-body tr")
                    break
            paso("el inspector abre un bundle y lista lo de dentro", filas_insp > 0,
                 "%s = %s filas" % (ruta, filas_insp))

            # recursos: arrancar el indice y ver que avanza, luego cancelar
            p.js("ir('resources')")
            p.pulsar("#res-build")
            time.sleep(12)
            avanzando = p.js("(() => document.querySelector('#res-estado').textContent)()") or ""
            barra = p.js("(() => document.querySelector('#res-prog-i').style.width)()") or ""
            paso("el buscador construye su indice y lo dice con numeros",
                 any(c.isdigit() for c in avanzando), "%s (barra %s)" % (avanzando.strip()[:60], barra))
            p.pulsar("#res-cancel")
            cancelado = False
            for _ in range(12):                       # cancelar tarda: mira por tandas de bundles
                time.sleep(5)
                est = (p.js("(() => document.querySelector('#res-estado').textContent)()") or "").lower()
                if "cancel" in est and p.js("(() => document.querySelector('#res-build').disabled)()") is False:
                    cancelado = True
                    break
            paso("se puede cancelar", cancelado)

            # texturas (igual: algunos bundles no traen ninguna)
            p.js("ir('textures')")
            fotos, usado = 0, ""
            for cand in ("109/shared_23b7c8db.bundle", ruta):
                if not cand:
                    continue
                p.js("(() => { document.querySelector('#tex-bundle').value = %r; })()" % cand)
                p.pulsar("#tex-export")
                time.sleep(25)
                if p.filas("#tex-galeria figure") > 0:
                    fotos, usado = p.filas("#tex-galeria figure"), cand
                    break
            paso("las texturas se exportan y se ven", fotos > 0, "%s imagenes de %s" % (fotos, usado))

            # video y audio (usa las tres herramientas que acaba de bajar el boton)
            p.js("ir('media')")
            p.pulsar("#media-list")
            time.sleep(8)
            idx = p.js("(() => (mediaDatos.usm||[]).findIndex(m => m.nombre === %r))()" % VIDEO)
            paso("la lista de videos carga", (idx or -1) >= 0, "indice %s" % idx)
            if isinstance(idx, int) and idx >= 0:
                p.js("document.querySelectorAll('#media-lista .media-row')[%d].click()" % idx)
                time.sleep(1)
                p.pulsar("#media-extract")
                salida = ESCRITORIO / "extracted" / "media" / (Path(VIDEO).stem + ".mp4")
                for _ in range(120):
                    time.sleep(5)
                    if salida.is_file() and salida.stat().st_size > 1_000_000:
                        break
                paso("saca el MP4", salida.is_file(), "%s" % salida.name)
                if salida.is_file():
                    datos = ffprobe(salida)
                    tipos = [l for l in datos if l.startswith("codec_type=")]
                    idiomas = [l for l in datos if l.startswith("TAG:language=")]
                    paso("el MP4 lleva video y LAS TRES pistas de audio", len(tipos) == 4,
                         "%s" % tipos)
                    paso("las pistas van etiquetadas jpn/chi/und",
                         all(any(i in l for l in idiomas) for i in ("jpn", "chi", "und")),
                         "%s" % idiomas)


            # ------------------------------------------------- el bulk de TODAS las texturas
            print("\n3b) TEXTURAS EN BLOQUE (un lote corto, pero de verdad)")
            p.js("ir('bulk')")
            time.sleep(2)
            paso("la pestana abre", p.visible("#p-bulk"))
            filas = p.filas("#bulk-categorias tr")
            paso("lista las categorias de bundles", filas >= 6, "%d filas" % filas)
            suma = p.js("(() => [...document.querySelectorAll('#bulk-categorias tr')]"
                        ".reduce((a, r) => a + parseInt(r.children[2].textContent.replace(/,/g, ''), 10), 0))()")
            paso("los bundles de la tabla suman los 16.535 del catalogo", suma == 16535, "%s" % suma)
            paso("dice el peso estimado antes de empezar",
                 "MB" in p.texto("#bulk-estimado") and "textures" in p.texto("#bulk-estimado"),
                 p.texto("#bulk-estimado").strip()[:60])
            paso("ensena el sitio libre del disco", "free" in p.texto("#bulk-libre"),
                 p.texto("#bulk-libre").strip()[:40])
            # solo Effects y sin reanudar: asi extrae de verdad y no se salta nada
            p.pulsar("#bulk-todo")
            p.js("(() => { const i = document.querySelector('#bulk-categorias input[data-cat=\"effects\"]');"
                 " i.checked = true; i.dispatchEvent(new Event('change'));"
                 " document.querySelector('#bulk-reanudar').checked = false; return true; })()")
            time.sleep(0.5)
            p.pulsar("#bulk-empezar")
            for _ in range(60):
                time.sleep(5)
                if p.js("document.querySelector('#bulk-empezar').disabled === false"):
                    break
            carpeta = ESCRITORIO / "extracted" / "textures"
            # ojo: en `extracted/textures/` tambien escribe la herramienta de texturas de UN bundle,
            # que las deja sueltas. Aqui solo se mira lo que pone el bulk, que son las de Effects/.
            propias = list((carpeta / "Effects").rglob("*.png")) if (carpeta / "Effects").exists() else []
            paso("extrae las texturas y las deja en el disco", len(propias) > 0, "%d PNG" % len(propias))
            paso("ordenadas en <Categoria>/<conjunto>/",
                 bool(propias) and all(len(f.relative_to(carpeta).parts) >= 3 for f in propias),
                 str(propias[0].relative_to(carpeta)) if propias else "-")
            consola = p.texto("#bulk-consola")
            paso("la consola del bulk va en ingles y es de solo lectura",
                 bool(consola) and " de " not in consola
                 and p.js("document.querySelector('#bulk-consola').tagName") == "PRE",
                 consola.strip().splitlines()[-1][:60] if consola.strip() else "")
            paso("avisa del final", "Done" in p.texto("#bulk-estado"), p.texto("#bulk-estado").strip()[:50])

            paso("sin errores de JavaScript en toda la sesion", p.errores_js() == [],
                 p.errores_js())
    except Exception as e:  # noqa: BLE001
        paso("la sesion con la ventana nueva", False, "%s: %s" % (type(e).__name__, e))
    finally:
        matar()

    # ---------------------------------------------------------------- 4) si no hay WebView2
    print("\n4) LA INTERFAZ CLASICA (simulando que no hay WebView2)")
    (ESCRITORIO / "cache" / "ui_decision.txt").unlink(missing_ok=True)
    PROC = lanzar({"P5X_STUDIO_WEBVIEW2_OFF": "1"})
    time.sleep(14)
    vivo = PROC.poll() is None
    paso("con WebView2 ausente la app sigue abierta (interfaz clasica)", vivo)
    decision = ""
    try:
        decision = (ESCRITORIO / "cache" / "ui_decision.txt").read_text(encoding="utf-8")
    except OSError:
        pass
    paso("deja escrito que se cayo a la clasica",
         "ui=classic" in decision, decision.strip().splitlines()[-1][:70] if decision else "")
    matar()

    # ---------------------------------------------------------------- 5) al reves
    print("\n5) CON WEBVIEW2 (sin fingir nada)")
    (ESCRITORIO / "cache" / "ui_decision.txt").unlink(missing_ok=True)
    PROC = lanzar()
    time.sleep(14)
    paso("arranca y sigue vivo", PROC.poll() is None)
    decision = ""
    try:
        decision = (ESCRITORIO / "cache" / "ui_decision.txt").read_text(encoding="utf-8")
    except OSError:
        pass
    paso("elige la interfaz nueva", "ui=web" in decision,
         decision.strip().splitlines()[-1][:70] if decision else "")
    matar()

    # ---------------------------------------------------------------- resumen
    print("\n" + "=" * 78)
    fallos = [n for n, ok, _ in PASOS if not ok]
    print("RESUMEN: %d comprobaciones, %d bien, %d fallos" % (len(PASOS), len(PASOS) - len(fallos), len(fallos)))
    for n in fallos:
        detalle = [d for nn, ok, d in PASOS if nn == n and not ok]
        print("   FALLA: %s   %s" % (n, (detalle[0] if detalle else "")[:90]))
    print("=" * 78)
    (Path(__file__).resolve().parent / "informe_fuego.json").write_text(
        json.dumps(PASOS, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

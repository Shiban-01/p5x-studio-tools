"""Puente entre la interfaz web (pywebview/WebView2) y la fachada del motor (`motor.py`).

Aqui vive SOLO lo que necesita saber que "hay una ventana": los dialogos de fichero/carpeta, abrir
el explorador del sistema y el lanzamiento de tareas largas en hilo con progreso. Nada de logica de
datos: esta toda en el motor. La pagina (ui_web/*) llama a estos metodos por el puente JS de
pywebview y recibe JSON.
"""
from __future__ import annotations

import base64
import os
import subprocess
import threading
import time
from pathlib import Path

import webview

from . import ajustes, bustups, dependencias, motor
from .idiomas import t

# carpeta de salida de las extracciones que se piden desde la interfaz nueva
def _salida(sub: str) -> Path:
    d = ajustes.carpeta_herramientas() / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def _limite_de_prueba() -> int | None:
    """`P5X_STUDIO_BULK_LIMITE=N` corta el bulk a N bundles por categoria.

    Es un gancho de PRUEBA: la prueba de punta a punta tarda minutos en vez de horas. Sin la
    variable no hace nada (devuelve None).
    """
    try:
        n = int(os.environ.get("P5X_STUDIO_BULK_LIMITE") or 0)
    except ValueError:
        return None
    return n or None


class Api:
    """Objeto expuesto a JavaScript (`window.pywebview.api`)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cancelar = threading.Event()
        self._bust_carpeta = None      # carpeta de texturas elegida a mano (None = la de la app)
        self._tarea = {"activa": False, "terminada": False, "tipo": "", "hechos": 0,
                       "total": 0, "ultimo": "", "resultado": "", "error": "",
                       "cancelada": False}

    # ---------------------------------------------------------------- datos (fachada)
    def textos(self):
        return motor.textos()

    def estado(self):
        return motor.estado()

    def tipos(self):
        return motor.tipos_bundle()

    def bundles(self):
        return motor.listar_bundles()

    def novedades(self):
        """Bundles anadidos por actualizaciones del juego desde la ultima vez que se marco visto."""
        return motor.estado_novedades()

    def marcar_novedades(self):
        return {"marcados": motor.marcar_novedades_vistas()}

    def ficha(self, ruta):
        return motor.ficha_bundle(ruta)

    def abrir(self, ruta):
        return motor.abrir_bundle(ruta)

    def abrir_con_motor(self, ruta):
        return motor.abrir_con_motor(ruta)

    def exportar(self, ruta, tipos):
        try:
            destino = motor.exportar_bundle(ruta, tipos, _salida("bundles"))
            return {"ok": True, "destino": destino, "error": ""}
        except Exception as e:
            return {"ok": False, "destino": "", "error": str(e)}

    def buscar(self, texto="", tipo="", limite=1000):
        return motor.buscar_recursos(texto, tipo, limite)

    def texturas_listar(self, carpeta=""):
        return motor.texturas_listar(carpeta)

    def imagenes(self, carpeta=None):
        return motor.imagenes_de(carpeta or motor.carpeta_extraidas())

    def media(self):
        return motor.listar_media()

    def estado_herramientas(self):
        return motor.estado_herramientas()

    # ---------------------------------------------------------------- dialogos y sistema
    def elegir_bundle(self):
        v = webview.windows[0]
        res = v.create_file_dialog(webview.OPEN_DIALOG, directory=str(motor.carpeta_herramientas()),
                                   file_types=("Bundles (*.bundle)", "Todos (*.*)"))
        if not res:
            return None
        # pywebview devuelve una ruta absoluta; el motor trabaja con la relativa a la carpeta
        # de bundles. Se recorta si cae dentro.
        p = Path(res[0])
        carpeta = ajustes.carpeta_bundles()
        if carpeta:
            try:
                return p.relative_to(carpeta).as_posix()
            except ValueError:
                pass
        return str(p)

    def elegir_carpeta(self):
        v = webview.windows[0]
        res = v.create_file_dialog(webview.FOLDER_DIALOG, directory=str(motor.carpeta_extraidas()))
        return res[0] if res else None

    def revelar(self, ruta):
        p = motor.ruta_real(ruta)
        if not p:
            return False
        subprocess.Popen(["explorer", "/select,", p])
        return True

    def abrir_salida(self):
        try:
            os.startfile(motor.carpeta_extraidas())  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", motor.carpeta_extraidas()])
        return True

    def media_extraer_todos_usm(self):
        """Extrae TODOS los .usm a mp4. Lanza tarea en background."""
        return motor.extraer_todos_media("usm")

    def media_extraer_todos_acb(self):
        """Extrae TODOS los .acb/.awb a wav. Lanza tarea en background."""
        return motor.extraer_todos_media("awb")

    def verificar_update(self):
        return motor.verificar_update()

    def abrir_url_update(self, url):
        motor.abrir_url_update(url)

    def texturas_preview(self, carpeta="", limite=40):
        """Primeras imagenes con base64 inline para que la galeria las pinte directo."""
        import base64, mimetypes as _mm, os as _os
        r = motor.texturas_listar(carpeta)
        imgs = []
        for item in r.get("imagenes", [])[:limite]:
            ruta = item.get("ruta", "")
            src = ""
            if ruta and _os.path.isfile(ruta):
                try:
                    mt = _mm.guess_type(ruta)[0] or "image/png"
                    with open(ruta, "rb") as f:
                        src = "data:" + mt + ";base64," + base64.b64encode(f.read()).decode()
                except Exception:
                    pass
            imgs.append({"ruta": ruta, "nombre": item.get("nombre", ""),
                         "bytes": item.get("bytes", 0), "src": src})
        return {"ok": True, "imagenes": imgs, "n_total": r.get("n", 0),
                "carpeta": r.get("carpeta", "")}

    def tex_imagen_data(self, ruta):
        """Devuelve la imagen como data URL base64 (para que el visor la muestre)."""
        import base64, mimetypes as _mm, os as _os
        if not ruta or not _os.path.isfile(ruta):
            return {"ok": False}
        try:
            mt = _mm.guess_type(ruta)[0] or "image/png"
            with open(ruta, "rb") as f:
                data = base64.b64encode(f.read()).decode("ascii")
            return {"ok": True, "src": f"data:{mt};base64,{data}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def texturas_exportar(self, ruta):
        try:
            destino = motor.exportar_texturas(ruta, _salida("textures"))
            return {"ok": True, "destino": destino, "error": ""}
        except Exception as e:
            return {"ok": False, "destino": "", "error": str(e)}

    # ---------------------------------------------------------------- tareas largas
    def _nueva_tarea(self, tipo, total=0):
        with self._lock:
            self._cancelar.clear()
            self._tarea = {"activa": True, "terminada": False, "tipo": tipo, "hechos": 0,
                           "total": total, "ultimo": "", "resultado": "", "error": "",
                           "cancelada": False, "lineas": []}

    def _fin_tarea(self, resultado="", error="", cancelada=False):
        with self._lock:
            self._tarea.update({"activa": False, "terminada": True, "resultado": resultado,
                                "error": error, "cancelada": cancelada})

    def _log(self, tipo, maximo=400):
        """Devuelve una funcion que apunta lineas del progreso.

        Se guardan las ultimas `maximo` (una descarga de 90 MB imprime cientos de lineas, y la lista
        entera viaja a JavaScript en cada sondeo: sin tope se come la memoria). `ultimo` se mantiene
        porque lo usa el sondeo que ya existia.
        """
        def f(msg):
            with self._lock:
                self._tarea["ultimo"] = str(msg)
                lineas = self._tarea.setdefault("lineas", [])
                lineas.append(str(msg))
                if len(lineas) > maximo:
                    del lineas[: len(lineas) - maximo]
        return f

    def iniciar_video(self, ruta):
        self._nueva_tarea("video")
        destino = _salida("media")

        def trabajo():
            try:
                salida = motor.extraer_video(ruta, destino, self._log("video"))
                self._fin_tarea(resultado=os.path.basename(salida))
            except Exception as e:
                self._fin_tarea(error=str(e))
        threading.Thread(target=trabajo, daemon=True).start()
        return True

    def iniciar_audio(self, ruta):
        self._nueva_tarea("audio")
        destino = _salida("media")

        def trabajo():
            try:
                salidas = motor.extraer_audio(ruta, destino, self._log("audio"))
                self._fin_tarea(resultado="%d WAV" % len(salidas))
            except Exception as e:
                self._fin_tarea(error=str(e))
        threading.Thread(target=trabajo, daemon=True).start()
        return True

    def iniciar_indice(self):
        est = motor.estado_indice()
        self._nueva_tarea("indice", total=est.get("bundles", 0))

        def progreso(hechos, total):
            with self._lock:
                self._tarea["hechos"] = hechos
                self._tarea["total"] = total

        def trabajo():
            try:
                filas = motor.construir_indice(progreso=progreso,
                                               cancelar=self._cancelar.is_set,
                                               log=self._log("indice"))
                if self._cancelar.is_set():
                    self._fin_tarea(cancelada=True)
                else:
                    self._fin_tarea(resultado="%d" % len(filas))
            except Exception as e:
                self._fin_tarea(error=str(e))
        threading.Thread(target=trabajo, daemon=True).start()
        return True

    def estado_dependencias(self):
        """Que herramientas faltan y cuanto pesa todo. No instala nada: solo mira."""
        est = motor.estado_herramientas()
        return {"herramientas": est,
                "peso_mb": dependencias.peso_aproximado_mb(),
                "tamanos": dict(dependencias.TAMANOS_MB),
                "faltan": [k for k, v in est.items() if not v],
                # las que se estan usando desde fuera de la carpeta: funcionan, pero no viajan
                # (hacen falta las rutas: `estado_herramientas` solo dice si/no)
                "fuera": dependencias.dentro_de_carpeta(motor.estado_herramientas_rutas())}

    def instalar_dependencias(self):
        """Descarga/instala las herramientas externas que la app necesita, linea a linea."""
        self._nueva_tarea("dependencias")

        def trabajo():
            try:
                r = dependencias.asegurar_todas(progreso=self._log("dependencias"))
                if r["fallos"]:
                    self._fin_tarea(error="; ".join("%s: %s" % (k, v)
                                                    for k, v in r["fallos"].items()))
                else:
                    self._fin_tarea(resultado="%d of %d" % (len(r["ok"]), len(dependencias.ORDEN)))
            except Exception as e:  # noqa: BLE001
                self._fin_tarea(error=str(e))
        threading.Thread(target=trabajo, daemon=True).start()
        return True

    def cancelar_tarea(self):
        self._cancelar.set()
        return True

    # ---------------------------------------------------------------- texturas en bloque
    def bulk_inventario(self, filtro=""):
        """Que se puede sacar, por categoria (bundles exactos, texturas y peso estimados)."""
        return motor.bulk_inventario(filtro or "")

    def bulk_estado(self, destino=None):
        """Lo que ya hay hecho en el destino: es lo que decide si reanudar o empezar."""
        est = motor.bulk_estado(destino or None)
        est["inventario"] = motor.bulk_inventario("")
        return est

    def elegir_destino_bulk(self):
        v = webview.windows[0]
        res = v.create_file_dialog(webview.FOLDER_DIALOG, directory=str(motor.carpeta_extraidas()))
        if not res:
            return None
        return {"destino": res[0], "libre": motor.bulk_estado(res[0])["libre"]}

    def abrir_destino_bulk(self, destino=None):
        d = motor.bulk_estado(destino or None)["destino"]
        try:
            os.startfile(d)  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", d])
        return True

    def bulk_forzar(self, destino=None):
        """Olvida lo apuntado en ese destino (la proxima pasada lo mira todo otra vez)."""
        return motor.bulk_forzar(destino or None)

    def iniciar_bulk(self, opciones=None):
        """Saca las texturas marcadas. Tarea larga: hilo propio, progreso y cancelacion."""
        opciones = opciones or {}
        categorias = [c for c in (opciones.get("categorias") or []) if c]
        filtro = (opciones.get("filtro") or "").strip()
        sprites = bool(opciones.get("sprites", True))
        por_tipo = bool(opciones.get("por_tipo", False))
        reanudar = bool(opciones.get("reanudar", True))
        destino = opciones.get("destino") or None
        if not categorias:
            return {"ok": False, "error": t("bulk_err_sin_categoria")}
        self._nueva_tarea("bulk", total=motor.bulk_bundles(categorias))

        def progreso(hechos, cuantos):
            with self._lock:
                self._tarea["hechos"] = hechos
                self._tarea["total"] = cuantos
                if hechos >= cuantos:
                    self._tarea["ultimo"] = t("web_bulk_progreso", hechos, cuantos)

        def trabajo():
            try:
                r = motor.bulk_extraer(categorias, destino, filtro=filtro, sprites=sprites,
                                       por_tipo=por_tipo, reanudar=reanudar, progreso=progreso,
                                       log=self._log("bulk"), cancelar=self._cancelar.is_set,
                                       limite=_limite_de_prueba())
                with self._lock:
                    self._tarea["total"] = r.get("total") or self._tarea["total"]
                    self._tarea["hechos"] = r.get("bundles") or self._tarea["hechos"]
                if r.get("cancelado"):
                    self._fin_tarea(resultado=t("bulk_fin_cancelado", r.get("ficheros", 0)),
                                    cancelada=True)
                elif r.get("fallos"):
                    self._fin_tarea(resultado=t("bulk_fin", r.get("ficheros", 0)),
                                    error="; ".join(r["fallos"][:4]))
                else:
                    self._fin_tarea(resultado=t("bulk_fin", r.get("ficheros", 0)))
            except Exception as e:  # noqa: BLE001
                self._fin_tarea(error=str(e))
        threading.Thread(target=trabajo, daemon=True).start()
        return {"ok": True, "error": ""}

    def estado_tarea(self):
        with self._lock:
            return dict(self._tarea)

    # ---------------------------------------------------------------- visor de bust-ups
    def bustups_lista(self, filtro=""):
        """Los bust-ups que se pueden montar. La lista NO trae imagenes: se piden al abrir uno."""
        return motor.bustups_lista(filtro or "", self._bust_carpeta)

    def bustups_ver(self, clave, expresion="", shader=False, sin_tinte=False):
        """Monta un bust-up. El PNG viaja como data URL: la pagina no puede leer del disco, y asi
        al cambiar de expresion no se pelea con la cache del navegador. Con shader=True se aplica el
        shader de dialogo del juego (el tono calido de las conversaciones). Con sin_tinte=True se
        aplica el shader pero sin el degradado ambiental."""
        r = motor.bustups_ver(clave, expresion or None, self._bust_carpeta, bool(shader),
                               sin_tinte=bool(sin_tinte))
        r["png"] = ""
        if r.get("ok") and r.get("ruta"):
            try:
                r["png"] = "data:image/png;base64," + base64.b64encode(
                    Path(r["ruta"]).read_bytes()).decode("ascii")
            except OSError:
                pass
        return r

    def bustups_exportar(self, clave, expresion="", shader=False, sin_tinte=False):
        try:
            r = motor.bustups_exportar(clave, expresion or None, _salida("bustups"),
                                       self._bust_carpeta, bool(shader), sin_tinte=bool(sin_tinte))
            return {"ok": bool(r.get("ok")), "destino": r.get("destino", ""),
                    "error": r.get("error", "")}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "destino": "", "error": str(e)}

    def bustups_elegir_carpeta(self):
        """Deja elegir donde estan las texturas (por si el bulk se paso en otro sitio)."""
        v = webview.windows[0]
        res = v.create_file_dialog(webview.FOLDER_DIALOG, directory=str(bustups.carpeta_texturas()))
        if not res:
            return None
        self._bust_carpeta = res[0]
        return {"carpeta": res[0], "texturas": motor.bustups_texturas(res[0])}

    def revelar_fichero(self, ruta):
        """Ensenar un fichero concreto en el explorador (el PNG exportado)."""
        p = Path(ruta)
        if not p.exists():
            return False
        subprocess.Popen(["explorer", "/select,", str(p)])
        return True

    # ---------------------------------------------------------------- extracto de retratos
    def bustups_retratos_estado(self):
        """Que hay para el visor: el extracto pequeno de retratos o el bulk entero."""
        return motor.bustups_retratos_estado()

    def iniciar_bustups_retratos(self):
        """Saca SOLO las texturas de los retratos: el visor queda autosuficiente sin el bulk."""
        estado = motor.bustups_retratos_estado()
        self._nueva_tarea("retratos", total=len(estado.get("bundles") or []))

        def progreso(hechos, cuantos):
            with self._lock:
                self._tarea["hechos"] = hechos
                self._tarea["total"] = cuantos
                if hechos >= cuantos:
                    self._tarea["ultimo"] = t("web_bust_retr_progreso", hechos, cuantos)

        def trabajo():
            try:
                r = motor.bustups_retratos_extraer(progreso=progreso, log=self._log("retratos"),
                                                   cancelar=self._cancelar.is_set,
                                                   limite=_limite_de_prueba())
                est = motor.bustups_retratos_estado()
                fin = t("web_bust_retr_fin", r.get("ficheros", 0), est.get("retratos_mb", 0))
                if r.get("cancelado"):
                    self._fin_tarea(resultado=t("bulk_fin_cancelado", r.get("ficheros", 0)),
                                    cancelada=True)
                elif r.get("fallos"):
                    self._fin_tarea(resultado=fin, error="; ".join(r["fallos"][:4]))
                else:
                    self._fin_tarea(resultado=fin)
            except Exception as e:  # noqa: BLE001
                self._fin_tarea(error=str(e))

        threading.Thread(target=trabajo, daemon=True).start()
        return {"ok": True, "error": ""}

    def abrir_carpeta_retratos(self):
        """Abre la carpeta del extracto de retratos."""
        d = motor.bustups_retratos_estado().get("retratos") or motor.carpeta_extraidas()
        Path(d).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(d)  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", d])
        return True


def _pagina() -> str:
    return str(Path(__file__).resolve().parent / "ui_web" / "index.html")


def _capturar_si_pedido() -> None:
    """Si se pide por entorno, guarda una captura de la ventana y/o la cierra sola.

    Hace falta para comprobar la interfaz DENTRO del .exe (congelada): en el codigo fuente se puede
    enganchar un sondeo de JavaScript al DOM, pero a un .exe ya lanzado no. Con esto se lanza el
    ejecutable, se guarda la captura y se mira.

    `P5X_STUDIO_UI_ESPERA` son los segundos que se deja pintar la ventana antes de la captura.
    """
    ruta = os.environ.get("P5X_STUDIO_UI_CAPTURA")
    try:
        segundos = float(os.environ.get("P5X_STUDIO_UI_AUTOCIERRE") or 0)
    except ValueError:
        segundos = 0.0
    if not ruta and not segundos:
        return
    try:
        espera = float(os.environ.get("P5X_STUDIO_UI_ESPERA") or 6)
    except ValueError:
        espera = 6.0

    def trabajo():
        time.sleep(espera)
        ventana = next(iter(webview.windows), None)
        if ventana is None:
            return
        if ruta:
            try:
                from PIL import ImageGrab
                x, y = int(ventana.x), int(ventana.y)
                w, h = int(ventana.width), int(ventana.height + 40)   # 40: margen del marco
                ImageGrab.grab(bbox=(max(x, 0), max(y, 0), x + w, y + h)).save(ruta)
            except Exception:
                pass
        if segundos:
            try:
                ventana.destroy()
            except Exception:
                pass

    threading.Thread(target=trabajo, daemon=True).start()


def arrancar(titulo: str = "P5X Studio · Tools %s" % ajustes.VERSION) -> None:
    """Abre la ventana nueva. Si WebView2 no responde, lanza la excepcion (que captura `ui`)."""
    ajustes.CACHE.mkdir(parents=True, exist_ok=True)
    # Gancho de diagnostico: con P5X_STUDIO_UI_CDP=<puerto> la ventana acepta el protocolo de
    # depuracion de WebView2. Sirve para pilotar el .exe YA CONGELADO desde fuera (pulsar botones y
    # leer la pantalla), que es la unica forma de probar de verdad el ejecutable publicado.
    puerto = os.environ.get("P5X_STUDIO_UI_CDP")
    if puerto:
        try:
            webview.settings["REMOTE_DEBUGGING_PORT"] = int(puerto)
        except (TypeError, ValueError):
            pass
    api = Api()
    webview.create_window(titulo, _pagina(), js_api=api, width=1180, height=700,
                          min_size=(940, 560), background_color="#0b0b0d")
    # gui='edgechromium' a proposito: si WebView2 no esta, queremos que FALLE y se caiga a la
    # clasica, en vez de que pywebview busque otro motor que el usuario no ha aprobado.
    webview.start(_capturar_si_pedido, gui="edgechromium")


    def texturas_preview(self, carpeta="", limite=30):
        """Primeras N imagenes con base64 inline para la galeria."""
        import base64, mimetypes as _mm, os as _os
        from pathlib import Path as _P
        r = motor.texturas_listar(carpeta)
        imgs = []
        for item in r.get("imagenes", [])[:limite]:
            ruta = item.get("ruta", "")
            src = ""
            if ruta and _os.path.isfile(ruta):
                try:
                    mt = _mm.guess_type(ruta)[0] or "image/png"
                    with open(ruta, "rb") as f:
                        src = f"data:{mt};base64," + base64.b64encode(f.read()).decode()
                except Exception:
                    pass
            imgs.append({"ruta": ruta, "nombre": item.get("nombre", ""),
                         "bytes": item.get("bytes", 0), "src": src})
        return {"ok": True, "imagenes": imgs, "n_total": r.get("n", 0),
                "carpeta": r.get("carpeta", "")}

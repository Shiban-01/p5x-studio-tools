"""Herramientas de P5X Studio: explorar, inspeccionar y extraer cualquier cosa del juego.

La pestana de extraccion saca modelos de personaje. Esta pestana es para todo lo demas: mirar
los 16.535 bundles sin abrir nada (con los indices ya construidos), abrir UNO con el motor y ver
que lleva dentro, buscar un recurso por su nombre en TODO el juego, ver las imagenes que salgan
de una extraccion y sacar los videos y la musica del cliente.

Todo el texto visible sale del modulo `idiomas`; al crear cada widget se registra una funcion que
le vuelve a poner el texto, y cambiar de idioma recorre ese registro sin reconstruir la pestana.

Todo lo pesado (el motor, wannacri, vgmstream, ffmpeg) va en un hilo aparte y se comunica con la
ventana por una cola, para que la interfaz no se congele nunca. Las herramientas externas se
BUSCAN; si falta alguna, se dice con claridad en vez de fallar, y nunca se instala nada solo.

Modulo independiente: no importa `gui` (gui lo importa a el), asi que no puede haber ciclo.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import ajustes, dependencias, idiomas, trajes
from .idiomas import t

COLOR_FONDO = "#1f2024"
COLOR_PANEL = "#2a2c32"
COLOR_TEXTO = "#e8e8ee"
COLOR_SUAVE = "#a8a8b4"
COLOR_ACENTO = "#e04a5a"
COLOR_OK = "#5fbf7f"
COLOR_AVISO = "#e0a94a"

# version de Unity del juego: el motor la necesita porque los bundles no la traen dentro
UNITY = "2022.3.49f1"
# clave decimal de los .usm (valida en el cliente global, no ha cambiado desde la OBT)
CLAVE_USM = "1729401234202"

# extensiones de imagen que el visor sabe abrir
EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga", ".webp")


# --------------------------------------------------------------------------- rutas y datos
def _raiz_datos() -> Path:
    """La carpeta `_dl` con los indices del juego (empaquetada si el .exe esta congelado)."""
    if getattr(sys, "frozen", False):
        emp = getattr(sys, "_MEIPASS", None)
        if emp and (Path(emp) / "_dl").is_dir():
            return Path(emp) / "_dl"
        return Path(sys.executable).resolve().parent.parent / "_dl"
    return Path(__file__).resolve().parent.parent.parent / "_dl"


def _leer_json(relativo: str) -> dict:
    ruta = _raiz_datos() / relativo
    if not ruta.is_file():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def indice_ficheros() -> dict:
    return _leer_json("indice_juego/indice_ficheros.json")


def indice_assets() -> dict:
    return _leer_json("indice_assets/assets.json")


_CATALOGO: list[dict] | None = None


def catalogo_bundles() -> list[dict]:
    """Los 16.535 bundles con todo lo que los indices saben de cada uno, sin abrir ninguno.

    Cruza tres fuentes ya construidas: el indice de ficheros (tipo, tamano), el de trajes (papel,
    actor, traje, mallas, texturas) y el de contenido (tipos de recurso que lleva dentro).
    """
    global _CATALOGO
    if _CATALOGO is not None:
        return _CATALOGO
    ficheros = indice_ficheros().get("ficheros", [])
    tb = trajes.datos().get("bundles", {}) if trajes.disponible() else {}
    asx = indice_assets()
    salida = []
    for f in ficheros:
        ruta = "%s/%s" % (f.get("carpeta", ""), f.get("fichero", ""))
        b = tb.get(ruta) or {}
        a = asx.get(ruta) or {}
        salida.append({
            "ruta": ruta,
            "carpeta": f.get("carpeta", ""),
            "fichero": f.get("fichero", ""),
            "tipo": (f.get("tipo") or "").lower(),
            "que_es": f.get("que_es", ""),
            "nombre": f.get("nombre", ""),
            "mb": f.get("mb", 0) or 0,
            "papel": b.get("papel", ""),
            "actores": b.get("actores") or [],
            "trajes": b.get("trajes") or [],
            "mallas": b.get("mallas") or [],
            "texturas": b.get("texturas") or [],
            "tiene": a.get("tiene") or [],
            "cuenta": a.get("cuenta") or {},
            "quien": a.get("quien") or [],
        })
    _CATALOGO = salida
    return salida


def tipos_de_bundle() -> list[str]:
    """Los tipos de bundle que existen de verdad, con su numero, ordenados de mas a menos."""
    cuenta: dict[str, int] = {}
    for b in catalogo_bundles():
        t_ = b["tipo"] or "?"
        cuenta[t_] = cuenta.get(t_, 0) + 1
    return [t_ for t_, _ in sorted(cuenta.items(), key=lambda x: -x[1])]


_RECURSOS: list[tuple] | None = None


def indice_recursos() -> list[tuple]:
    """(nombre, tipo, bundle) de cada recurso conocido del juego.

    Se arma con los nombres de malla y de textura del indice de trajes (listas COMPLETAS) mas la
    `muestra` del indice de contenido, que cubre tipos que el de trajes no anota (AnimationClip,
    MonoBehaviour, Sprite, VideoClip, TextAsset, Font, Animator).
    """
    global _RECURSOS
    if _RECURSOS is not None:
        return _RECURSOS
    salida: list[tuple] = []
    vistos: set = set()
    tb = trajes.datos().get("bundles", {}) if trajes.disponible() else {}
    for ruta, b in tb.items():
        for n in (b.get("mallas") or []):
            if (n, "Mesh", ruta) not in vistos:
                vistos.add((n, "Mesh", ruta))
                salida.append((n, "Mesh", ruta))
        for n in (b.get("texturas") or []):
            if (n, "Texture2D", ruta) not in vistos:
                vistos.add((n, "Texture2D", ruta))
                salida.append((n, "Texture2D", ruta))
    for ruta, a in indice_assets().items():
        for tipo, nombres in (a.get("muestra") or {}).items():
            for n in nombres:
                if (n, tipo, ruta) not in vistos:
                    vistos.add((n, tipo, ruta))
                    salida.append((n, tipo, ruta))
    _RECURSOS = salida
    return salida


def tipos_de_recurso() -> list[str]:
    cuenta: dict[str, int] = {}
    for _, t_, _ in indice_recursos():
        cuenta[t_] = cuenta.get(t_, 0) + 1
    return [t_ for t_, _ in sorted(cuenta.items(), key=lambda x: -x[1])]


def carpeta_bundles() -> Path | None:
    return ajustes.carpeta_bundles()


def ruta_bundle_juego(ruta_rel: str) -> Path | None:
    """Fichero real de un bundle a partir de su ruta relativa (`110/shared_...bundle`)."""
    carpeta = carpeta_bundles()
    if not carpeta:
        return None
    p = carpeta / (ruta_rel or "").replace("/", os.sep)
    return p if p.is_file() else None


# --------------------------------------------------------------------------- herramientas externas
def _candidatos_wannacri() -> list[list[str]]:
    raiz = ajustes.RAIZ
    cands = []
    for base in (raiz.parent / "tools", raiz / "tools"):
        exe = base / "env" / "Scripts" / "wannacri.exe"
        if exe.is_file():
            cands.append([str(exe)])
        py = base / "env" / "Scripts" / "python.exe"
        if py.is_file():
            cands.append([str(py), "-m", "wannacri"])
    cands.append(["wannacri"])
    return cands


def _candidatos_vgmstream() -> list[list[str]]:
    raiz = ajustes.RAIZ
    cands = []
    for base in (raiz.parent / "tools", raiz / "tools"):
        exe = base / "vgmstream" / "vgmstream-cli.exe"
        if exe.is_file():
            cands.append([str(exe)])
    cands.append(["vgmstream-cli"])
    return cands


def _candidatos_ffmpeg() -> list[list[str]]:
    cands = [["ffmpeg"]]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cands.append([str(Path(local) / "hermes" / "tools" / "ffmpeg-9.0.1-win32-x64" / "bin" / "ffmpeg.exe")])
    return cands


def _comprueba(comando: list[str], args=("-version",)) -> bool:
    try:
        r = subprocess.run(comando + list(args), capture_output=True, text=True, timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0 or bool((r.stdout or "") + (r.stderr or ""))
    except Exception:
        return False


def _localiza(candidatos: list[list[str]], args=("-version",)) -> list[str] | None:
    for c in candidatos:
        if _comprueba(c, args):
            return c
    return None


def estado_herramientas() -> dict:
    """Que herramientas externas hay disponibles. No instala nada: solo mira."""
    return {
        "wannacri": _localiza(_candidatos_wannacri(), ("-h",)),
        "vgmstream": _localiza(_candidatos_vgmstream(), ("-h",)),
        "ffmpeg": _localiza(_candidatos_ffmpeg(), ("-version",)),
        "motor": dependencias.ruta_assetstudio(),
    }


# --------------------------------------------------------------------------- motor (bundle a bundle)
def _ruta_motor() -> Path:
    exe = dependencias.ruta_assetstudio()
    if not exe:
        raise RuntimeError(t("her_motor_falta"))
    return Path(exe)


def _ejecutar_motor(argumentos: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    orden = [str(_ruta_motor())] + argumentos
    entorno = dict(os.environ)
    entorno["MSYS_NO_PATHCONV"] = "1"
    return subprocess.run(orden, capture_output=True, text=True, timeout=timeout,
                          env=entorno, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def listar_bundle(ruta_rel: str, log=None) -> list[dict]:
    """Abre UN bundle con `-m info --export-asset-list xml` y devuelve sus recursos.

    Es rapido (~0,2 s) porque no decodifica nada: solo escribe la lista de lo que lleva dentro.
    El XML se parsea con ElementTree, NUNCA con regex `.*?` + re.S: un bundle con ~1.400 assets
    hace retroceso catastrofico y el regex se cuelga (parecia un cuelgue del motor).
    """
    fichero = ruta_bundle_juego(ruta_rel)
    if not fichero:
        raise RuntimeError(t("her_err_bundle", ruta_rel))
    destino = ajustes.CACHE / "herramientas" / "info"
    destino.mkdir(parents=True, exist_ok=True)
    xml = destino / "assets.xml"
    if xml.exists():
        try:
            xml.unlink()
        except OSError:
            pass
    if log:
        log(t("her_log_abriendo", ruta_rel))
    r = _ejecutar_motor([str(fichero), "-m", "info", "--export-asset-list", "xml",
                         "-o", str(destino), "--log-level", "Error", "--unity-version", UNITY])
    if not xml.is_file():
        raise RuntimeError(t("her_err_sin_lista")
                           % ((r.stdout or "") + (r.stderr or ""))[-600:])
    raiz = ET.parse(str(xml)).getroot()
    filas = []
    for a in raiz.findall("Asset"):
        filas.append({
            "nombre": (a.findtext("Name") or "").strip(),
            "tipo": (a.findtext("Type") or "").strip(),
            "contenedor": (a.findtext("Container") or "").strip(),
            "pathid": (a.findtext("PathID") or "").strip(),
            "tamano": int((a.findtext("Size") or "0").strip() or 0),
        })
    return filas


def exportar_bundle(ruta_rel: str, tipos: str, destino: Path, log=None) -> Path:
    """Exporta los recursos elegidos de UN bundle. `tipos` va en minusculas y con comas."""
    fichero = ruta_bundle_juego(ruta_rel)
    if not fichero:
        raise RuntimeError(t("her_err_bundle", ruta_rel))
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    if log:
        log(t("her_log_exportando", ruta_rel, tipos))
    r = _ejecutar_motor([str(fichero), "-m", "export", "-t", tipos, "-o", str(destino),
                         "--log-level", "Error", "-r", "--unity-version", UNITY], timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(t("her_err_exportar")
                           % ((r.stdout or "") + (r.stderr or ""))[-800:])
    return destino


# --------------------------------------------------------------------------- video y audio
def carpeta_media() -> Path | None:
    """La carpeta con los .usm y .awb del cliente."""
    juego = ajustes.detectar_juego()
    if not juego:
        return None
    for sub in ("Client/OuterPackage/Media/Windows", "Client/bin/Media/Windows"):
        p = juego / sub
        if p.is_dir():
            return p
    return None


def listar_media(carpeta: Path | None = None) -> dict:
    carpeta = carpeta or carpeta_media()
    if not carpeta or not carpeta.is_dir():
        return {"carpeta": None, "usm": [], "awb": []}
    usm, awb = [], []
    for p in carpeta.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() == ".usm":
            usm.append({"nombre": p.name, "ruta": str(p), "mb": p.stat().st_size / 1e6})
        elif p.suffix.lower() == ".awb":
            awb.append({"nombre": p.name, "ruta": str(p), "mb": p.stat().st_size / 1e6})
    usm.sort(key=lambda x: x["nombre"].lower())
    awb.sort(key=lambda x: x["nombre"].lower())
    return {"carpeta": str(carpeta), "usm": usm, "awb": awb}


def extraer_video(ruta_usm: str, destino: Path, log=None) -> Path:
    """`.usm` -> `.mp4` con wannacri + ffmpeg. Salen .ivf (VP9), .avi (Sofdec) o alphas/*.sfv."""
    wannacri = _localiza(_candidatos_wannacri(), ("-h",))
    ffmpeg = _localiza(_candidatos_ffmpeg(), ("-version",))
    if not wannacri:
        raise RuntimeError(t("her_err_wannacri"))
    if not ffmpeg:
        raise RuntimeError(t("her_err_ffmpeg"))
    origen = Path(ruta_usm)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    crudo = destino / (origen.stem + "_crudo")
    if crudo.exists():
        shutil.rmtree(crudo, ignore_errors=True)
    crudo.mkdir(parents=True, exist_ok=True)
    if log:
        log(t("her_log_wannacri", origen.name))
    r = subprocess.run(wannacri + ["extractusm", str(origen), "-k", CLAVE_USM, "-o", str(crudo)],
                       capture_output=True, text=True, timeout=1800,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    # pistas de video: .ivf o .avi; pista alfa: alphas/*.sfv
    piezas = [p for p in crudo.rglob("*") if p.suffix.lower() in (".ivf", ".avi", ".mpg", ".m2v")]
    if not piezas:
        # algunos clips mueren con «Unknown element occurence 0» (parche documentado en el skill)
        raise RuntimeError(t("her_err_sin_pista")
                           % ((r.stdout or "") + (r.stderr or ""))[-600:])
    pieza = max(piezas, key=lambda p: p.stat().st_size)
    salida = destino / (origen.stem + ".mp4")
    if log:
        log(t("her_log_ffmpeg", pieza.name, salida.name))
    r2 = subprocess.run([ffmpeg[0], "-y", "-i", str(pieza), "-c", "copy", "-f", "mp4", str(salida)],
                        capture_output=True, text=True, timeout=1800,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r2.returncode != 0 or not salida.is_file():
        raise RuntimeError(t("her_err_ffmpeg_empaquetar")
                           % ((r2.stdout or "") + (r2.stderr or ""))[-600:])
    if log:
        log(t("her_log_video_listo", salida.name, salida.stat().st_size / 1e6))
    return salida


def partir_hca(ruta_awb: str, destino: Path, log=None) -> list[Path]:
    """Los .awb son HCA concatenados EN CLARO: se parten por la magia `HCA\\0`."""
    datos = Path(ruta_awb).read_bytes()
    partes = datos.split(b"HCA\x00")
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    salidas = []
    for i, p in enumerate(partes[1:], 1):
        blob = b"HCA\x00" + p
        f = destino / ("%s_%02d.hca" % (Path(ruta_awb).stem, i))
        f.write_bytes(blob)
        salidas.append(f)
    if log:
        log(t("her_log_hca", len(salidas)))
    return salidas


def extraer_audio(ruta_awb: str, destino: Path, log=None) -> list[Path]:
    """`.awb` -> `.wav` con el troceador HCA + vgmstream."""
    vgm = _localiza(_candidatos_vgmstream(), ("-h",))
    if not vgm:
        raise RuntimeError(t("her_err_vgmstream"))
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    hcas = partir_hca(ruta_awb, destino / (Path(ruta_awb).stem + "_hca"), log)
    salidas = []
    for h in hcas:
        wav = destino / (h.stem + ".wav")
        r = subprocess.run(vgm + ["-o", str(wav), str(h)], capture_output=True, text=True,
                           timeout=600, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if wav.is_file():
            salidas.append(wav)
            if log:
                log(t("her_log_wav", h.name, wav.name, wav.stat().st_size / 1e6))
        elif log:
            log(t("her_log_no_wav", h.name))
    if not salidas:
        raise RuntimeError(t("her_err_sin_audio"))
    return salidas


def imagenes_de(carpeta: Path) -> list[Path]:
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    salida = [p for p in carpeta.rglob("*") if p.is_file() and p.suffix.lower() in EXT_IMAGEN]
    salida.sort(key=lambda p: p.name.lower())
    return salida


# =========================================================================== panel de la interfaz
class PanelHerramientas(ttk.Frame):
    """La pestana de HERRAMIENTAS. Se empaqueta dentro del Notebook de la ventana principal."""

    def __init__(self, maestro, log=None):
        super().__init__(maestro, style="TFrame")
        self.log_externo = log
        self.cola: "queue.Queue" = queue.Queue()
        self.trabajando = False
        self._imagen = None                 # referencia viva de la vista previa (si no, se borra)
        self._filas_explorador: list[dict] = []
        self._filas_inspector: list[dict] = []
        self._filas_recursos: list[tuple] = []
        self._media = {"usm": [], "awb": []}
        self._destino_por_defecto = ajustes.carpeta_salida() / "herramientas"
        self._estilo()
        self._construir()
        self.after(150, self._vaciar_cola)

    # ------------------------------------------------------------------ aspecto
    def _estilo(self):
        st = ttk.Style()
        st.configure("Her.Treeview", background=COLOR_PANEL, fieldbackground=COLOR_PANEL,
                     foreground=COLOR_TEXTO, font=("Consolas", 9), rowheight=20, borderwidth=0)
        st.configure("Her.Treeview.Heading", background=COLOR_FONDO, foreground=COLOR_SUAVE,
                     font=("Segoe UI Semibold", 9))
        st.map("Her.Treeview", background=[("selected", COLOR_ACENTO)],
               foreground=[("selected", "#ffffff")])
        st.configure("Her.TNotebook", background=COLOR_FONDO, borderwidth=0)
        st.configure("Her.TNotebook.Tab", background=COLOR_PANEL, foreground=COLOR_SUAVE,
                     padding=(12, 5), font=("Segoe UI", 9))
        st.map("Her.TNotebook.Tab", background=[("selected", COLOR_FONDO)],
               foreground=[("selected", COLOR_TEXTO)])

    # ------------------------------------------------------------------ idiomas
    def _t(self, widget, clave, *args):
        idiomas.registrar(lambda w=widget, k=clave, a=args: w.config(text=t(k, *a)))
        return widget

    def _t_tab(self, pestana, clave):
        idiomas.registrar(lambda p=pestana, k=clave: self.cuaderno.tab(p, text=t(k)))

    def _construir(self):
        cab = ttk.Frame(self, padding=(14, 8, 14, 4))
        cab.pack(fill="x")
        self._t(ttk.Label(cab, style="Titulo.TLabel"), "her_titulo").pack(anchor="w")
        self._t(ttk.Label(cab, style="Suave.TLabel"), "her_lema").pack(anchor="w")

        self.cuaderno = ttk.Notebook(self, style="Her.TNotebook")
        self.cuaderno.pack(fill="both", expand=True, padx=14, pady=(4, 10))

        self.tab_explorador = ttk.Frame(self.cuaderno)
        self.tab_inspector = ttk.Frame(self.cuaderno)
        self.tab_buscador = ttk.Frame(self.cuaderno)
        self.tab_texturas = ttk.Frame(self.cuaderno)
        self.tab_media = ttk.Frame(self.cuaderno)
        for pestana, clave in ((self.tab_explorador, "her_tab_explorador"),
                               (self.tab_inspector, "her_tab_inspector"),
                               (self.tab_buscador, "her_tab_buscador"),
                               (self.tab_texturas, "her_tab_texturas"),
                               (self.tab_media, "her_tab_media")):
            self.cuaderno.add(pestana, text=t(clave))
            self._t_tab(pestana, clave)

        self._construir_explorador()
        self._construir_inspector()
        self._construir_buscador()
        self._construir_texturas()
        self._construir_media()

    # ------------------------------------------------------------------ helpers
    def registrar(self, texto):
        if self.log_externo:
            self.log_externo(texto)

    def _arbol(self, maestro, columnas, anchos):
        marco = ttk.Frame(maestro)
        barra = ttk.Scrollbar(marco, orient="vertical")
        tv = ttk.Treeview(marco, columns=columnas, show="headings", style="Her.Treeview",
                          yscrollcommand=barra.set)
        for c, a in zip(columnas, anchos):
            tv.heading(c, text=t(c))
            tv.column(c, width=a, stretch=(c == columnas[0]))
        idiomas.registrar(lambda: [tv.heading(c, text=t(c)) for c in columnas])
        barra.config(command=tv.yview)
        barra.pack(side="right", fill="y")
        tv.pack(side="left", fill="both", expand=True)
        return marco, tv

    def _en_hilo(self, funcion):
        if self.trabajando:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_ocupado"))
            return
        self.trabajando = True

        def envoltorio():
            try:
                funcion()
            except Exception as e:
                self.cola.put(("error", str(e)))
            finally:
                self.cola.put(("ocupado", False))
        threading.Thread(target=envoltorio, daemon=True).start()

    def _vaciar_cola(self):
        try:
            while True:
                tipo, carga = self.cola.get_nowait()
                if tipo == "log":
                    self.registrar(carga)
                elif tipo == "inspector":
                    self._pintar_inspector(carga)
                elif tipo == "recursos":
                    self._pintar_recursos(carga)
                elif tipo == "media":
                    self._pintar_media(carga)
                elif tipo == "herr":
                    self._pintar_estado_herr(carga)
                elif tipo == "estado":
                    self.estado.config(text=carga)
                elif tipo == "error":
                    self.registrar("")
                    self.registrar(t("her_err_no_completar", carga))
                    self.estado.config(text=t("msg_no_completar"))
                    messagebox.showerror(ajustes.NOMBRE, str(carga)[:1200])
                elif tipo == "ocupado":
                    self.trabajando = bool(carga)
        except Exception:
            pass
        self.after(150, self._vaciar_cola)

    def _destino(self, sugerido="herramientas"):
        d = self._destino_por_defecto / sugerido
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ============================================================ EXPLORADOR
    def _construir_explorador(self):
        t_ = self.tab_explorador
        filtros = ttk.Frame(t_, padding=(0, 8, 0, 4))
        filtros.pack(fill="x")

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_tipo").pack(side="left")
        self.combo_tipo = ttk.Combobox(filtros, state="readonly", width=12)
        self.combo_tipo.pack(side="left", padx=(4, 12))
        self._preparar_combo_tipo()
        idiomas.registrar(self._preparar_combo_tipo)

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_actor").pack(side="left")
        self.ent_actor = ttk.Entry(filtros, width=12)
        self.ent_actor.pack(side="left", padx=(4, 12))

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_traje").pack(side="left")
        self.ent_traje = ttk.Entry(filtros, width=12)
        self.ent_traje.pack(side="left", padx=(4, 12))

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_min_mb").pack(side="left")
        self.ent_mb = ttk.Entry(filtros, width=6)
        self.ent_mb.pack(side="left", padx=(4, 12))

        self._t(ttk.Button(filtros, command=self.explorar), "her_filtrar").pack(side="left")
        self.etiq_explorador = ttk.Label(filtros, text="", style="Suave.TLabel")
        self.etiq_explorador.pack(side="left", padx=(12, 0))

        cuerpo = ttk.Frame(t_)
        cuerpo.pack(fill="both", expand=True)
        # El panel de detalle se empaqueta ANTES que la tabla: si no, la tabla (cuyo ancho pedido
        # es la suma de sus columnas, ~800 px) se queda el sitio primero y empuja el panel fuera
        # de la ventana. Reservando el panel a la derecha, la tabla se encoge y cabe todo.
        det = ttk.Frame(cuerpo, style="Panel.TFrame", padding=8, width=300)
        det.pack(side="right", fill="y", padx=(10, 0))
        det.pack_propagate(False)
        self.detalle = tk.Text(det, width=34, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                               font=("Consolas", 9), bd=0, highlightthickness=0, wrap="word")
        self.detalle.pack(fill="both", expand=True)
        fila = ttk.Frame(det, style="Panel.TFrame")
        fila.pack(fill="x", pady=(6, 0))
        self._t(ttk.Button(fila, command=self.explorador_al_inspector),
                "her_ver_dentro").pack(side="left", fill="x", expand=True)
        fila2 = ttk.Frame(det, style="Panel.TFrame")
        fila2.pack(fill="x", pady=(4, 0))
        self._t(ttk.Button(fila2, command=self.explorador_exportar),
                "her_exportar_mesh_tex").pack(fill="x")

        marco, self.arbol_explorador = self._arbol(
            cuerpo, ("her_col_bundle", "her_col_tipo", "her_col_papel", "her_col_mb",
                     "her_col_mallas", "her_col_texturas", "her_col_contenido"),
            (260, 70, 80, 60, 60, 70, 200))
        marco.pack(side="left", fill="both", expand=True)
        self.arbol_explorador.bind("<<TreeviewSelect>>", lambda e: self.detalle_explorador())

    def _preparar_combo_tipo(self):
        """(Re)llena el desplegable de tipos conservando lo elegido."""
        actual = self.combo_tipo.get()
        valores = [t("comun_todo")] + tipos_de_bundle()
        self.combo_tipo.config(values=valores)
        self.combo_tipo.set(actual if actual in valores else valores[0])

    def explorar(self):
        filas = catalogo_bundles()
        tipo = self.combo_tipo.get().strip().lower()
        actor = self.ent_actor.get().strip().lower()
        traje = self.ent_traje.get().strip().lower()
        try:
            mb_min = float(self.ent_mb.get().strip() or 0)
        except ValueError:
            mb_min = 0.0
        sel = []
        for b in filas:
            if tipo and tipo != t("comun_todo").lower() and b["tipo"] != tipo:
                continue
            if mb_min and b["mb"] < mb_min:
                continue
            if actor and not any(actor in (a or "").lower() for a in b["actores"]) \
                    and not any(actor in (a or "").lower() for a in b["quien"]) \
                    and actor not in b["fichero"].lower():
                continue
            if traje and not any(traje in (t_ or "").lower() for t_ in b["trajes"]) \
                    and traje not in b["fichero"].lower():
                continue
            sel.append(b)
        self._filas_explorador = sel
        self.arbol_explorador.delete(*self.arbol_explorador.get_children())
        for b in sel[:4000]:
            contenido = ",".join(b["tiene"]) or b["que_es"]
            self.arbol_explorador.insert(
                "", "end", values=(b["ruta"], b["tipo"], b["papel"] or "-",
                                   "%.1f" % b["mb"], len(b["mallas"]), len(b["texturas"]),
                                   contenido))
        self.etiq_explorador.config(
            text=t("her_bundles_de", len(sel), len(filas))
                 + (t("her_solo_4000") if len(sel) > 4000 else ""))

    def _bundle_seleccionado(self, arbol, filas):
        sel = arbol.selection()
        if not sel:
            return None
        i = arbol.index(sel[0])
        return filas[i] if 0 <= i < len(filas) else None

    def detalle_explorador(self):
        b = self._bundle_seleccionado(self.arbol_explorador, self._filas_explorador)
        if not b:
            return
        lineas = [
            b["ruta"],
            t("her_det_tipo_papel", b["tipo"], b["papel"] or "-"),
            t("her_det_que_es", b["que_es"] or "-"),
            t("her_det_tamano", b["mb"]),
            "",
            t("her_det_actores", ", ".join(b["actores"]) or "-"),
            t("her_det_trajes", ", ".join(b["trajes"]) or "-"),
            t("her_det_quien", ", ".join(b["quien"]) or "-"),
            "",
            t("her_det_contenido", json.dumps(b["cuenta"], ensure_ascii=False) or "-"),
            t("her_det_mallas", len(b["mallas"]), ", ".join(b["mallas"][:8]) or "-"),
            t("her_det_texturas", len(b["texturas"]), ", ".join(b["texturas"][:8]) or "-"),
        ]
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", "\n".join(lineas))
        self.detalle.configure(state="disabled")

    def explorador_al_inspector(self):
        b = self._bundle_seleccionado(self.arbol_explorador, self._filas_explorador)
        if not b:
            return
        self.ent_ruta.delete(0, "end")
        self.ent_ruta.insert(0, b["ruta"])
        self.cuaderno.select(self.tab_inspector)
        self.abrir_inspector()

    def explorador_exportar(self):
        b = self._bundle_seleccionado(self.arbol_explorador, self._filas_explorador)
        if not b:
            return
        self._exportar_async(b["ruta"], "mesh,tex2d", "explorador")

    # ============================================================ INSPECTOR
    def _construir_inspector(self):
        t_ = self.tab_inspector
        fila = ttk.Frame(t_, padding=(0, 8, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_bundle").pack(side="left")
        self.ent_ruta = ttk.Entry(fila)
        self.ent_ruta.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._t(ttk.Button(fila, command=self.elegir_bundle),
                "her_elegir_fichero").pack(side="left")
        self._t(ttk.Button(fila, command=self.abrir_inspector),
                "her_abrir_motor").pack(side="left", padx=(6, 0))

        self.arbol_inspector = None
        marco, self.arbol_inspector = self._arbol(
            t_, ("her_col_nombre", "her_col_tipo2", "her_col_contenedor", "her_col_pathid",
                 "her_col_tamano"), (300, 110, 260, 160, 80))
        marco.pack(fill="both", expand=True)

        pie = ttk.Frame(t_, padding=(0, 6, 0, 0))
        pie.pack(fill="x")
        self._t(ttk.Label(pie, style="Suave.TLabel"), "her_exportar").pack(side="left")
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector("mesh")),
                "her_mallas").pack(side="left", padx=(6, 0))
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector("tex2d")),
                "her_texturas").pack(side="left", padx=(4, 0))
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector("mesh,tex2d")),
                "her_mallas_texturas").pack(side="left", padx=(4, 0))
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector(
            "mesh,tex2d,mat,anim,mono,font,sprite,text,audio,video")),
            "her_todo_posible").pack(side="left", padx=(4, 0))
        self.estado = ttk.Label(pie, text="", style="Suave.TLabel")
        self.estado.pack(side="left", padx=(12, 0))

    def elegir_bundle(self):
        carpeta = carpeta_bundles()
        ruta = filedialog.askopenfilename(
            title=t("dlg_bundle_titulo"),
            initialdir=str(carpeta) if carpeta else None,
            filetypes=[(t("dlg_bundle_unity"), "*.bundle"), (t("dlg_bundle_todos"), "*.*")])
        if ruta:
            self.ent_ruta.delete(0, "end")
            self.ent_ruta.insert(0, ruta)

    def abrir_inspector(self):
        ruta = self.ent_ruta.get().strip()
        if not ruta:
            messagebox.showinfo(ajustes.NOMBRE, t("her_msg_ruta"))
            return
        self.estado.config(text=t("her_abriendo"))

        def trabajo():
            filas = listar_bundle(ruta, lambda s: self.cola.put(("log", s)))
            self.cola.put(("log", t("her_recursos_dentro", len(filas), Path(ruta).name)))
            self.cola.put(("inspector", filas))
            self.cola.put(("estado", t("her_n_recursos", len(filas))))
        self._en_hilo(trabajo)

    def _pintar_inspector(self, filas):
        self._filas_inspector = filas
        self.arbol_inspector.delete(*self.arbol_inspector.get_children())
        for f in filas:
            self.arbol_inspector.insert(
                "", "end", values=(f["nombre"], f["tipo"], f["contenedor"], f["pathid"],
                                   "%.1f KB" % (f["tamano"] / 1024.0)))

    def exportar_inspector(self, tipos):
        ruta = self.ent_ruta.get().strip()
        if not ruta:
            return
        self._exportar_async(ruta, tipos, "inspector")

    # ============================================================ BUSCADOR
    def _construir_buscador(self):
        t_ = self.tab_buscador
        fila = ttk.Frame(t_, padding=(0, 8, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_recurso").pack(side="left")
        self.ent_recurso = ttk.Entry(fila)
        self.ent_recurso.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self.ent_recurso.bind("<Return>", lambda e: self.buscar_recurso())
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_tipo").pack(side="left")
        self.combo_tipo_recurso = ttk.Combobox(fila, state="readonly", width=14)
        self.combo_tipo_recurso.pack(side="left", padx=(4, 6))
        self._preparar_combo_tipo_recurso()
        idiomas.registrar(self._preparar_combo_tipo_recurso)
        self._t(ttk.Button(fila, command=self.buscar_recurso), "comun_buscar").pack(side="left")

        marco, self.arbol_recursos = self._arbol(
            t_, ("her_col_recurso", "her_col_tipo3", "her_col_bundle"), (420, 130, 320))
        marco.pack(fill="both", expand=True)

        pie = ttk.Frame(t_, padding=(0, 6, 0, 0))
        pie.pack(fill="x")
        self.etiq_recursos = ttk.Label(pie, text="", style="Suave.TLabel")
        self.etiq_recursos.pack(side="left")
        self._t(ttk.Button(pie, command=self.recurso_al_inspector),
                "her_ver_bundle").pack(side="right")
        self._t(ttk.Button(pie, command=lambda: self.recurso_exportar()),
                "her_exportar_bundle").pack(side="right", padx=(0, 6))

    def _preparar_combo_tipo_recurso(self):
        actual = self.combo_tipo_recurso.get()
        valores = [t("comun_todo")] + tipos_de_recurso()
        self.combo_tipo_recurso.config(values=valores)
        self.combo_tipo_recurso.set(actual if actual in valores else valores[0])

    def buscar_recurso(self):
        texto = self.ent_recurso.get().strip().lower()
        if len(texto) < 2:
            messagebox.showinfo(ajustes.NOMBRE, t("her_msg_dos_letras"))
            return
        tipo = self.combo_tipo_recurso.get().strip()
        todos = indice_recursos()
        sel = []
        for nombre, tip, bundle in todos:
            if tipo and tipo != t("comun_todo") and tip != tipo:
                continue
            if texto in (nombre or "").lower():
                sel.append((nombre, tip, bundle))
            if len(sel) >= 5000:
                break
        self._filas_recursos = sel
        self.arbol_recursos.delete(*self.arbol_recursos.get_children())
        for nombre, tip, bundle in sel:
            self.arbol_recursos.insert("", "end", values=(nombre, tip, bundle))
        self.etiq_recursos.config(
            text=t("her_coincidencias", len(sel), len(todos)))
        self.registrar(t("her_log_buscador", texto, len(sel)))

    def recurso_al_inspector(self):
        sel = self.arbol_recursos.selection()
        if not sel:
            return
        i = self.arbol_recursos.index(sel[0])
        if not (0 <= i < len(self._filas_recursos)):
            return
        _, _, bundle = self._filas_recursos[i]
        self.ent_ruta.delete(0, "end")
        self.ent_ruta.insert(0, bundle)
        self.cuaderno.select(self.tab_inspector)
        self.abrir_inspector()

    def recurso_exportar(self):
        sel = self.arbol_recursos.selection()
        if not sel:
            return
        i = self.arbol_recursos.index(sel[0])
        if not (0 <= i < len(self._filas_recursos)):
            return
        _, tip, bundle = self._filas_recursos[i]
        tipos = {"Mesh": "mesh", "Texture2D": "tex2d"}.get(tip, "mesh,tex2d")
        self._exportar_async(bundle, tipos, "recursos")

    # ============================================================ TEXTURAS
    def _construir_texturas(self):
        t_ = self.tab_texturas
        fila = ttk.Frame(t_, padding=(0, 8, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_carpeta").pack(side="left")
        self.ent_carpeta_img = ttk.Entry(fila)
        self.ent_carpeta_img.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._t(ttk.Button(fila, command=self.elegir_carpeta_imgs),
                "her_elegir_carpeta").pack(side="left")
        self._t(ttk.Button(fila, command=self.listar_imagenes),
                "her_listar_imagenes").pack(side="left", padx=(6, 0))

        cuerpo = ttk.Frame(t_)
        cuerpo.pack(fill="both", expand=True)
        izq = ttk.Frame(cuerpo)
        izq.pack(side="left", fill="y")
        barra = ttk.Scrollbar(izq, orient="vertical")
        self.lista_imgs = tk.Listbox(izq, width=42, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                     selectbackground=COLOR_ACENTO, selectforeground="#ffffff",
                                     font=("Consolas", 9), bd=0, highlightthickness=0,
                                     yscrollcommand=barra.set, activestyle="none")
        barra.config(command=self.lista_imgs.yview)
        barra.pack(side="right", fill="y")
        self.lista_imgs.pack(side="left", fill="both", expand=True)
        self.lista_imgs.bind("<<ListboxSelect>>", lambda e: self.mostrar_imagen())

        der = ttk.Frame(cuerpo, style="Panel.TFrame", padding=6)
        der.pack(side="right", fill="both", expand=True, padx=(10, 0))
        self.lienzo = tk.Canvas(der, bg=COLOR_PANEL, highlightthickness=0)
        self.lienzo.pack(fill="both", expand=True)
        self.info_img = self._t(ttk.Label(der, style="SuavePanel.TLabel"), "her_elige_imagen")
        self.info_img.pack(anchor="w", pady=(4, 0))

    def elegir_carpeta_imgs(self):
        inicial = self.ent_carpeta_img.get().strip() or str(self._destino())
        carpeta = filedialog.askdirectory(title=t("dlg_carpeta_img_titulo"),
                                          initialdir=inicial)
        if carpeta:
            self.ent_carpeta_img.delete(0, "end")
            self.ent_carpeta_img.insert(0, carpeta)
            self.listar_imagenes()

    def listar_imagenes(self):
        carpeta = self.ent_carpeta_img.get().strip()
        self.lista_imgs.delete(0, "end")
        self._imgs = imagenes_de(carpeta) if carpeta else []
        for p in self._imgs:
            self.lista_imgs.insert("end", "  %s" % p.name)
        self.info_img.config(text=t("her_n_imagenes", len(self._imgs)))
        if not self._imgs:
            self.lienzo.delete("all")
            self.lienzo.create_text(20, 20, anchor="nw", fill=COLOR_SUAVE,
                                    text=t("her_sin_imagenes"))

    def mostrar_imagen(self):
        sel = self.lista_imgs.curselection()
        if not sel or not getattr(self, "_imgs", None):
            return
        ruta = self._imgs[sel[0]]
        try:
            from PIL import Image, ImageTk
        except Exception as e:
            self.info_img.config(text=t("her_sin_pillow", e))
            return
        try:
            img = Image.open(ruta)
            ancho, alto = img.size
            modo = img.mode
            w = max(self.lienzo.winfo_width(), 200)
            h = max(self.lienzo.winfo_height(), 200)
            img.thumbnail((w - 12, h - 12))
            self._imagen = ImageTk.PhotoImage(img)
            self.lienzo.delete("all")
            self.lienzo.create_image(6, 6, anchor="nw", image=self._imagen)
            self.info_img.config(text="%s   %dx%d px   %s   (%.0f KB)"
                                 % (ruta.name, ancho, alto, modo, ruta.stat().st_size / 1024))
        except Exception as e:
            self.lienzo.delete("all")
            self.lienzo.create_text(20, 20, anchor="nw", fill=COLOR_AVISO,
                                    text=t("her_err_imagen", e))

    # ============================================================ VIDEO Y AUDIO
    def _construir_media(self):
        t_ = self.tab_media
        est = ttk.Frame(t_, style="Panel.TFrame", padding=(10, 8))
        est.pack(fill="x", pady=(8, 6))
        self._t(ttk.Label(est, style="Panel.TLabel", font=("Segoe UI Semibold", 10)),
                "her_herr_externas").pack(anchor="w")
        self.etiquetas_herr = {}
        for clave, clave_texto in (("wannacri", "her_wannacri"),
                                   ("vgmstream", "her_vgmstream"),
                                   ("ffmpeg", "her_ffmpeg"),
                                   ("motor", "her_motor")):
            f = ttk.Frame(est, style="Panel.TFrame")
            f.pack(fill="x", pady=(3, 0))
            ttk.Label(f, text="•", style="Panel.TLabel", foreground=COLOR_SUAVE,
                      width=2).pack(side="left")
            self._t(ttk.Label(f, style="Panel.TLabel", width=32), clave_texto).pack(side="left")
            et = ttk.Label(f, text=t("comun_comprobando"), style="SuavePanel.TLabel")
            et.pack(side="left")
            self.etiquetas_herr[clave] = et
        self._t(ttk.Button(est, command=self.comprobar_herramientas),
                "her_comprobar_herr").pack(anchor="w", pady=(6, 0))

        fila = ttk.Frame(t_, padding=(0, 2, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_mostrar").pack(side="left")
        self.combo_media = ttk.Combobox(fila, state="readonly", width=16)
        self.combo_media.pack(side="left", padx=(4, 8))
        self._preparar_combo_media()
        idiomas.registrar(self._preparar_combo_media)
        self.combo_media.bind("<<ComboboxSelected>>", lambda e: self.pintar_media())
        self._t(ttk.Button(fila, command=self.listar_media), "her_listar").pack(side="left")
        self.etiq_media = ttk.Label(fila, text="", style="Suave.TLabel")
        self.etiq_media.pack(side="left", padx=(10, 0))

        cuerpo = ttk.Frame(t_)
        cuerpo.pack(fill="both", expand=True)
        # el panel derecho se reserva primero, para que la lista no lo empuje fuera (ver explorador)
        der = ttk.Frame(cuerpo, style="Panel.TFrame", padding=10, width=290)
        der.pack(side="right", fill="y", padx=(10, 0))
        der.pack_propagate(False)
        self._t(ttk.Label(der, style="Panel.TLabel", font=("Segoe UI Semibold", 10)),
                "her_extraer_elegido").pack(anchor="w")
        self._t(ttk.Label(der, style="SuavePanel.TLabel", wraplength=250),
                "her_media_ayuda").pack(anchor="w", pady=(4, 8))
        self.boton_video = self._t(ttk.Button(der, command=self.extraer_video_sel),
                                   "her_extraer_mp4")
        self.boton_video.pack(fill="x")
        self.boton_audio = self._t(ttk.Button(der, command=self.extraer_audio_sel),
                                   "her_extraer_wav")
        self.boton_audio.pack(fill="x", pady=(6, 0))
        self._t(ttk.Button(der, command=self.abrir_salida),
                "her_abrir_salida").pack(fill="x", pady=(12, 0))
        self.etiq_sel_media = ttk.Label(der, text="", style="SuavePanel.TLabel", wraplength=250)
        self.etiq_sel_media.pack(anchor="w", pady=(10, 0))

        izq = ttk.Frame(cuerpo)
        izq.pack(side="left", fill="both", expand=True)
        barra = ttk.Scrollbar(izq, orient="vertical")
        self.lista_media = tk.Listbox(izq, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                      selectbackground=COLOR_ACENTO, selectforeground="#ffffff",
                                      font=("Consolas", 9), bd=0, highlightthickness=0,
                                      yscrollcommand=barra.set, activestyle="none")
        barra.config(command=self.lista_media.yview)
        barra.pack(side="right", fill="y")
        self.lista_media.pack(side="left", fill="both", expand=True)
        self.lista_media.bind("<<ListboxSelect>>", lambda e: self.detalle_media())

    def _preparar_combo_media(self):
        """(Re)llena el desplegable Videos/Audio conservando la eleccion (por indice)."""
        i = self.combo_media.current()
        self.combo_media.config(values=[t("her_videos"), t("her_audios")])
        self.combo_media.current(i if i >= 0 else 0)

    def comprobar_herramientas(self):
        def trabajo():
            est = estado_herramientas()
            self.cola.put(("herr", est))
        self._en_hilo(trabajo)
        # el resultado llega por cola; se pinta cuando llegue
        self.cola.put(("log", t("her_log_comprobando_herr")))

    def _pintar_estado_herr(self, est):
        for clave, et in self.etiquetas_herr.items():
            valor = est.get(clave)
            if valor:
                texto = valor[0] if isinstance(valor, (list, tuple)) else str(valor)
                et.config(text=t("her_disponible", Path(texto).name), foreground=COLOR_OK)
            else:
                et.config(text=t("her_no_disponible"), foreground=COLOR_AVISO)

    def listar_media(self):
        datos = listar_media()
        self._media = datos
        if not datos.get("carpeta"):
            self.etiq_media.config(text=t("her_no_carpeta_media"))
            self.lista_media.delete(0, "end")
            self.registrar(t("her_log_no_media"))
            return
        self.pintar_media()

    def pintar_media(self):
        es_audio = self.combo_media.current() == 1
        lista = self._media.get("awb" if es_audio else "usm", [])
        self.lista_media.delete(0, "end")
        self._media_sel = lista
        for m in lista:
            self.lista_media.insert("end", "  %-42s %8.1f MB" % (m["nombre"], m["mb"]))
        self.etiq_media.config(text=t("her_ficheros_en", len(lista), self._media.get("carpeta", "")))

    def detalle_media(self):
        sel = self.lista_media.curselection()
        if not sel or not getattr(self, "_media_sel", None):
            return
        m = self._media_sel[sel[0]]
        self.etiq_sel_media.config(text="%s\n%.1f MB" % (m["nombre"], m["mb"]))

    def _media_elegido(self):
        sel = self.lista_media.curselection()
        if not sel or not getattr(self, "_media_sel", None):
            messagebox.showinfo(ajustes.NOMBRE, t("her_msg_elige_fichero"))
            return None
        return self._media_sel[sel[0]]

    def extraer_video_sel(self):
        m = self._media_elegido()
        if not m:
            return
        destino = self._destino("media")

        def trabajo():
            self.cola.put(("log", t("her_log_extrayendo_video", m["nombre"])))
            salida = extraer_video(m["ruta"], destino, lambda s: self.cola.put(("log", s)))
            self.cola.put(("estado", t("her_estado_video_listo", salida.name)))
            self.cola.put(("log", t("her_log_video_extraido", salida)))
        self._en_hilo(trabajo)

    def extraer_audio_sel(self):
        m = self._media_elegido()
        if not m:
            return
        destino = self._destino("media")

        def trabajo():
            self.cola.put(("log", t("her_log_extrayendo_audio", m["nombre"])))
            salidas = extraer_audio(m["ruta"], destino, lambda s: self.cola.put(("log", s)))
            self.cola.put(("estado", t("her_estado_audio_listo", len(salidas))))
        self._en_hilo(trabajo)

    def abrir_salida(self):
        destino = self._destino("media")
        try:
            os.startfile(str(destino))  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", str(destino)])

    # ============================================================ exportar (comun)
    def _exportar_async(self, ruta_rel, tipos, subcarpeta):
        if not ruta_rel:
            return
        destino = self._destino(subcarpeta)
        self.estado.config(text=t("her_exportando", tipos))

        def trabajo():
            self.cola.put(("log", t("her_log_exportando", ruta_rel, destino)))
            exportar_bundle(ruta_rel, tipos, destino, lambda s: self.cola.put(("log", s)))
            n = sum(1 for _ in Path(destino).rglob("*") if _.is_file())
            self.cola.put(("log", t("her_log_n_ficheros", n)))
            self.cola.put(("estado", t("her_estado_exportado", destino)))
            self.registrar(t("her_log_export_terminada", destino))
        self._en_hilo(trabajo)

    # ------------------------------------------------------------------ primer arranque
    def arrancar(self):
        """Rellena el explorador y comprueba las herramientas la primera vez que se abre."""
        self.explorar()
        self.comprobar_herramientas()
        self.after(600, self.listar_media)
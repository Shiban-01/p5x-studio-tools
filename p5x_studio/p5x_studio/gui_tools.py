"""Ventana de P5X Studio Tools: la misma app, SOLO con la pestana de HERRAMIENTAS.

Esta version publica no extrae modelos de personaje: no importa `extractor`, `unity`,
`rig_unitypy`, `glb_rig`, `fbx_blender` ni `sesion_unity` (por eso el ejecutable pesa mucho
menos). Lo que queda es lo que funciona con certeza:

    explorador de bundles, inspector de un bundle, buscador de recursos, visor de texturas y
    video/audio (con sonido y eleccion de idioma de doblaje).

A diferencia de `gui.py`, aqui no hay pestana de extraccion ni pie de "Extraer": la ventana es mas
corta de logica y arranca directamente en las herramientas. Reutiliza `herramientas.PanelHerramientas`
tal cual, para no duplicar ni una linea de lo que ya funciona.

Todo el texto sale de `idiomas`, asi que la interfaz es bilingue (espanol/ingles) como la grande.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import ajustes, herramientas, idiomas
from .idiomas import t

COLOR_FONDO = "#1f2024"
COLOR_PANEL = "#2a2c32"
COLOR_TEXTO = "#e8e8ee"
COLOR_SUAVE = "#a8a8b4"
COLOR_ACENTO = "#e04a5a"
COLOR_OK = "#5fbf7f"
COLOR_AVISO = "#e0a94a"

# ancho/ancho-alto de diseno. Sin el pie de extraccion no hay boton que anclar abajo, asi que la
# ventana puede ser distinta de la de 701 px de la version completa.
#
# El alto NO se fija a ciegas: esta app no es DPI-aware, asi que Windows la escala (aqui x1,5) y un
# alto fijo se sale por abajo. En una pantalla de 1080 px a 150 % el area util son ~720 px logicos,
# de los que hay que descontar la barra de tareas y la barra de titulo. Por eso el alto se recorta
# en tiempo de ejecucion a lo que quepa (ver `_alto_que_cabe`): asi el registro de actividad nunca
# queda por debajo de la barra de tareas, ni en 1080 al 150 % ni en 1080 al 100 %.
VENTANA_ANCHO = 1180
VENTANA_ALTO = 640          # deseado; se recorta si la pantalla no da
VENTANA_ALTO_MIN = 540
VENTANA_MIN = (1000, 540)


class VentanaHerramientas:
    """La ventana de la version publica: solo herramientas."""

    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        idiomas.olvidar_registro()
        idiomas._ACTIVO["v"] = "en"          # la Tools va solo en ingles
        self.raiz.title("%s %s" % (t("tools_herramientas_solo"), ajustes.VERSION))
        # posicion fija arriba a la izquierda: con el escalado de Windows (~x1,5) una ventana
        # centrada baja lo suficiente como para que la barra de tareas tape el registro de
        # actividad. Anclada arriba, el alto que se calcula aqui SIEMPRE deja ver la ventana entera.
        self.raiz.geometry("%dx%d+0+0" % (VENTANA_ANCHO, self._alto_que_cabe()))
        self.raiz.minsize(*VENTANA_MIN)
        self.raiz.configure(bg=COLOR_FONDO)
        self._estilo()
        self._construir()
        # el panel se rellena solo un poco despues, para no retrasar el arranque
        self.raiz.after(500, self.panel.arrancar)

    def _alto_que_cabe(self) -> int:
        """Alto (en px logicos) que deja la ventana ENTERA dentro de la pantalla.

        La app no es DPI-aware: si la pantalla va al 150 %, Windows escala la ventana por 1,5, asi
        que el area util en px logicos es ~1/1,5 de la fisica (1080 -> ~720). Se descuentan ~88 px
        para la barra de titulo y la de tareas, de modo que el registro de actividad nunca queda
        escondido detras de la barra de tareas. Devuelve el alto deseado si la pantalla da de sobra.
        """
        try:
            disponible = self.raiz.winfo_screenheight()
        except Exception:
            return VENTANA_ALTO
        return max(VENTANA_ALTO_MIN, min(VENTANA_ALTO, disponible - 88))

    # ------------------------------------------------------------------ aspecto
    def _estilo(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=COLOR_FONDO, foreground=COLOR_TEXTO,
                     fieldbackground=COLOR_PANEL, bordercolor=COLOR_PANEL)
        st.configure("TFrame", background=COLOR_FONDO)
        st.configure("Panel.TFrame", background=COLOR_PANEL)
        st.configure("TLabel", background=COLOR_FONDO, foreground=COLOR_TEXTO,
                     font=("Segoe UI", 10))
        st.configure("Panel.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXTO,
                     font=("Segoe UI", 10))
        st.configure("Titulo.TLabel", font=("Segoe UI Semibold", 17), foreground=COLOR_TEXTO)
        st.configure("Suave.TLabel", foreground=COLOR_SUAVE, font=("Segoe UI", 9))
        st.configure("SuavePanel.TLabel", background=COLOR_PANEL, foreground=COLOR_SUAVE,
                     font=("Segoe UI", 9))
        st.configure("TButton", font=("Segoe UI", 10), padding=6)
        st.configure("TCheckbutton", background=COLOR_PANEL, foreground=COLOR_TEXTO,
                     font=("Segoe UI", 10))

    def _texto(self, widget, clave, *args):
        idiomas.registrar(lambda w=widget, k=clave, a=args: w.config(text=t(k, *a)))
        return widget

    def _construir(self):
        # --- cabecera: TODO en una sola fila (titulo + lema a la izquierda; carpeta del juego y
        # selector de idioma a la derecha, apilados en dos lineas). En vertical gastaba ~90 px de
        # mas, y la ventana no lleva DPI-awareness: cada pixel de alto cuenta.
        cab = ttk.Frame(self.raiz, padding=(16, 8, 16, 6))
        cab.pack(fill="x")
        izq = ttk.Frame(cab)
        izq.pack(side="left", anchor="nw")
        ttk.Label(izq, text=t("tools_herramientas_solo"), style="Titulo.TLabel").pack(anchor="w")
        self._texto(ttk.Label(izq, style="Suave.TLabel"), "tools_lema").pack(anchor="w")

        der = ttk.Frame(cab)
        der.pack(side="right", anchor="ne")

        fila_juego = ttk.Frame(der, style="Panel.TFrame", padding=(8, 4))
        fila_juego.pack(side="top", fill="x")
        self._texto(ttk.Label(fila_juego, style="Panel.TLabel"), "tools_juego").pack(side="left")
        self.etiq_juego = ttk.Label(fila_juego, text="", style="SuavePanel.TLabel")
        self.etiq_juego.pack(side="left", padx=(6, 8))
        self._texto(ttk.Button(fila_juego, command=self.elegir_juego),
                    "tools_elegir_juego").pack(side="right")
        idiomas.registrar(self._refrescar_juego)
        self._refrescar_juego()

        # --- registro de actividad (el panel escribe aqui lo que va haciendo).
        # Se reserva ANTES que el panel (side=bottom): el panel lleva dentro un Notebook que pide
        # mucho alto, y si se empaqueta primero aplasta el registro a 1 px.
        marco_log = ttk.Frame(self.raiz, style="Panel.TFrame", padding=8)
        marco_log.pack(side="bottom", fill="x", padx=16, pady=(0, 8))
        self._texto(ttk.Label(marco_log, style="Panel.TLabel"),
                    "tools_log_titulo").pack(anchor="w")
        self.registro = tk.Text(marco_log, height=3, bg=COLOR_PANEL, fg=COLOR_SUAVE,
                                font=("Consolas", 9), bd=0, highlightthickness=0,
                                state="disabled", wrap="word")
        self.registro.pack(fill="x")

        # --- el panel de herramientas, tal cual: es el mismo modulo que usa la version completa
        self.panel = herramientas.PanelHerramientas(self.raiz, log=self.escribir, cabecera=False)
        self.panel.pack(fill="both", expand=True, padx=6)

    # ------------------------------------------------------------------ juego
    def _refrescar_juego(self):
        juego = ajustes.detectar_juego()
        if juego:
            self.etiq_juego.config(text=str(juego), foreground=COLOR_OK)
        else:
            self.etiq_juego.config(text=t("tools_sin_juego"), foreground=COLOR_AVISO)

    def elegir_juego(self):
        """Pide la carpeta del juego, la verifica y la guarda para que se recuerde."""
        inicial = ajustes.detectar_juego()
        carpeta = filedialog.askdirectory(
            title=t("tools_elegir_juego"),
            initialdir=str(inicial) if inicial else None)
        if not carpeta:
            return
        juego, bundles = ajustes.resolver_carpeta_juego(carpeta)
        if not bundles:
            messagebox.showwarning(ajustes.NOMBRE, t("tools_carpeta_no_valida"))
            return
        ajustes.guardar_config(carpeta_juego=str(juego))
        # los bundles son otros: se tira lo memorizado (catalogo e indice de recursos)
        herramientas.olvidar_catalogo()
        herramientas.olvidar_recursos()
        cuantos = ajustes.contar_bundles(bundles)
        self._refrescar_juego()
        self.escribir("")
        self.escribir(t("tools_carpeta_guardada", juego, cuantos))
        messagebox.showinfo(ajustes.NOMBRE, t("tools_carpeta_guardada", juego, cuantos))
        self.panel.explorar()
        self.panel.listar_media()
        self.panel._actualizar_estado_indice()

    # ------------------------------------------------------------------ registro
    def escribir(self, texto):
        self.registro.configure(state="normal")
        self.registro.insert("end", texto.rstrip() + "\n")
        self.registro.see("end")
        self.registro.configure(state="disabled")


def arrancar():
    ajustes.CACHE.mkdir(parents=True, exist_ok=True)
    ajustes.carpeta_herramientas()
    raiz = tk.Tk()
    VentanaHerramientas(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    arrancar()

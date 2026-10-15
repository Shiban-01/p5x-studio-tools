"""Interfaz de P5X Studio.

Una sola ventana, en el idioma elegido (espanol por defecto, ingles), sin consolas ni mensajes
tecnicos. El usuario:
  1. ve si el juego y las dependencias estan listos (con un boton para comprobarlo),
  2. busca un personaje por nombre o por numero,
  3. pulsa Extraer y mira una barra de progreso,
  4. abre la carpeta del modelo con un boton.

Todo el texto visible sale del modulo `idiomas`: al crear cada widget se registra una funcion que
le vuelve a poner el texto, y cambiar de idioma recorre ese registro (sin reconstruir la ventana,
asi que no se pierde la busqueda, la categoria ni la lista cargada).

Todo el trabajo pesado va en un hilo aparte para que la ventana nunca se congele.
"""
from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import (ajustes, bases, catalogo, dependencias, extractor, herramientas, idiomas, indice,
                   preview, sesion_unity, unity)
from .idiomas import t

COLOR_FONDO = "#1f2024"
COLOR_PANEL = "#2a2c32"
COLOR_TEXTO = "#e8e8ee"
COLOR_SUAVE = "#a8a8b4"
COLOR_ACENTO = "#e04a5a"
COLOR_OK = "#5fbf7f"
COLOR_AVISO = "#e0a94a"


class Aplicacion:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        # idioma guardado ANTES de construir nada, para que los primeros textos ya salgan bien
        idiomas.olvidar_registro()
        idiomas._ACTIVO["v"] = ajustes.idioma()
        self.raiz.title("%s %s" % (ajustes.NOMBRE, ajustes.VERSION))
        self.raiz.geometry("1020x860")
        self.raiz.minsize(900, 700)
        self.raiz.configure(bg=COLOR_FONDO)

        self.cola = queue.Queue()
        self.datos_indice = None
        self.personajes = []
        self.python_entorno = None
        self.ultima_carpeta = None
        self.trabajando = False
        self._estado_ultimo = {}          # clave -> (clave_texto, args, bien) para re-traducir
        self._estado_clave = ("pie_listo", ())

        self._estilo()
        self._construir()
        self.raiz.after(120, self._vaciar_cola)
        self.raiz.after(200, self.comprobar_todo)
        # la pestana de herramientas se rellena sola un poco despues, para no retrasar el arranque
        self.raiz.after(500, self.panel_herramientas.arrancar)

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
        st.configure("TLabel", background=COLOR_FONDO, foreground=COLOR_TEXTO, font=("Segoe UI", 10))
        st.configure("Panel.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXTO,
                     font=("Segoe UI", 10))
        st.configure("Titulo.TLabel", font=("Segoe UI Semibold", 17), foreground=COLOR_TEXTO)
        st.configure("Suave.TLabel", foreground=COLOR_SUAVE, font=("Segoe UI", 9))
        st.configure("SuavePanel.TLabel", background=COLOR_PANEL, foreground=COLOR_SUAVE,
                     font=("Segoe UI", 9))
        st.configure("TButton", font=("Segoe UI", 10), padding=6)
        st.configure("Grande.TButton", font=("Segoe UI Semibold", 12), padding=12)
        st.configure("TCheckbutton", background=COLOR_PANEL, foreground=COLOR_TEXTO,
                     font=("Segoe UI", 10))
        st.configure("Horizontal.TProgressbar", background=COLOR_ACENTO,
                     troughcolor=COLOR_PANEL, bordercolor=COLOR_PANEL)
        # pestanas de la ventana: la de extraccion de siempre y la nueva suite de herramientas
        st.configure("TNotebook", background=COLOR_FONDO, borderwidth=0)
        st.configure("TNotebook.Tab", background=COLOR_PANEL, foreground=COLOR_SUAVE,
                     padding=(14, 6), font=("Segoe UI Semibold", 10))
        st.map("TNotebook.Tab", background=[("selected", COLOR_FONDO)],
               foreground=[("selected", COLOR_TEXTO)])

    # ------------------------------------------------------------------ idiomas
    def _texto(self, widget, clave, *args):
        """Apunta un widget y le pone el texto de `clave`; se reaplica al cambiar de idioma."""
        idiomas.registrar(lambda w=widget, k=clave, a=args: w.config(text=t(k, *a)))
        return widget

    def _texto_tab(self, cuaderno, pestana, clave):
        idiomas.registrar(lambda c=cuaderno, p=pestana, k=clave: c.tab(p, text=t(k)))

    def cambiar_idioma(self, _evento=None):
        """Cambia el idioma al momento y lo guarda para el proximo arranque."""
        nombre = self.combo_idioma.get()
        codigo = self._idioma_por_nombre.get(nombre, "es")
        if codigo == idiomas.idioma_actual():
            return
        ajustes.guardar_config(idioma=codigo)
        idiomas.activar(codigo)          # recorre el registro y reaplica TODOS los textos
        # textos que se componen con datos: hay que rehacerlos con el idioma nuevo
        self._refrescar_estado()
        self._preparar_categorias(getattr(self, "categoria", "todo"))
        self._catalogo = None            # el catalogo lleva el sufijo de skin y la categoria
        self.filtrar()
        self._refrescar_trajes()
        self._actualizar_base()
        self._refrescar_progreso()

    def _construir(self):
        # --- pestanas.
        # La interfaz de siempre pasa TAL CUAL a la primera pestana: el Notebook solo anade la
        # tira de pestanas arriba, y como la barra de accion (el boton Extraer) va anclada al
        # fondo, conserva su sitio exacto (y=636..687 en la ventana de 701 px): la tira se come
        # alto de la zona que se estira (la lista), no del pie.
        self.cuaderno = ttk.Notebook(self.raiz)
        self.cuaderno.pack(fill="both", expand=True)
        self.pestana_extraccion = ttk.Frame(self.cuaderno)
        self.pestana_herramientas = ttk.Frame(self.cuaderno)
        self.cuaderno.add(self.pestana_extraccion, text="  Extraccion  ")
        self.cuaderno.add(self.pestana_herramientas, text="  Herramientas  ")
        self._texto_tab(self.cuaderno, self.pestana_extraccion, "tab_extraccion")
        self._texto_tab(self.cuaderno, self.pestana_herramientas, "tab_herramientas")
        cont = self.pestana_extraccion

        # --- cabecera (con el selector de idioma a la derecha)
        cab = ttk.Frame(cont, padding=(22, 12, 22, 4))
        cab.pack(fill="x")
        izquierda = ttk.Frame(cab)
        izquierda.pack(side="left", anchor="w")
        ttk.Label(izquierda, text="P5X Studio", style="Titulo.TLabel").pack(anchor="w")
        self._texto(ttk.Label(izquierda, style="Suave.TLabel"), "cab_lema").pack(anchor="w")

        derecha = ttk.Frame(cab)
        derecha.pack(side="right", anchor="ne")
        self._texto(ttk.Label(derecha, style="Suave.TLabel"), "comun_idioma").pack(side="left",
                                                                                    padx=(0, 6))
        self._idioma_por_nombre = {v: k for k, v in idiomas.IDIOMAS.items()}
        self.combo_idioma = ttk.Combobox(derecha, state="readonly", width=10,
                                         values=list(idiomas.IDIOMAS.values()))
        self.combo_idioma.pack(side="left")
        self.combo_idioma.set(idiomas.IDIOMAS[idiomas.idioma_actual()])
        self.combo_idioma.bind("<<ComboboxSelected>>", self.cambiar_idioma)

        # --- estado del sistema
        marco_estado = ttk.Frame(cont, style="Panel.TFrame", padding=(16, 12))
        marco_estado.pack(fill="x", padx=22, pady=(10, 12))
        fila = ttk.Frame(marco_estado, style="Panel.TFrame")
        fila.pack(fill="x")
        self._texto(ttk.Label(fila, style="Panel.TLabel", font=("Segoe UI Semibold", 11)),
                    "est_titulo").pack(side="left")
        self.boton_comprobar = ttk.Button(fila, command=self.comprobar_todo)
        self.boton_comprobar.pack(side="right")
        self._texto(self.boton_comprobar, "est_comprobar")

        self.etiquetas_estado = {}
        for clave, clave_texto in (("juego", "est_juego"),
                                   ("librerias", "est_librerias"),
                                   ("indice", "est_indice"),
                                   ("esqueleto", "est_esqueleto")):
            f = ttk.Frame(marco_estado, style="Panel.TFrame")
            f.pack(fill="x", pady=(5, 0))
            ttk.Label(f, text="•", style="Panel.TLabel",
                      foreground=COLOR_SUAVE, width=2).pack(side="left")
            self._texto(ttk.Label(f, style="Panel.TLabel", width=24), clave_texto).pack(side="left")
            et = ttk.Label(f, style="SuavePanel.TLabel")
            et.pack(side="left", fill="x", expand=True)
            self.etiquetas_estado[clave] = et
            self._estado_ultimo[clave] = ("comun_comprobando", (), None)
        idiomas.registrar(self._refrescar_estado)

        # Los tres botones van en una sola fila horizontal: en vertical gastaban 43 px de alto que
        # la ventana (701 px) no tiene de sobra, y a lo ancho el panel va sobrado.
        fila_botones = ttk.Frame(marco_estado, style="Panel.TFrame")
        fila_botones.pack(anchor="w", pady=(8, 0))
        self.boton_elegir = ttk.Button(fila_botones, command=self.elegir_carpeta_juego)
        self.boton_elegir.pack(side="left")
        self._texto(self.boton_elegir, "btn_elegir_carpeta")
        self.boton_actualizar = ttk.Button(fila_botones, command=self.actualizar_librerias)
        self.boton_actualizar.pack(side="left", padx=(8, 0))
        self._texto(self.boton_actualizar, "btn_actualizar_librerias")

        # Unity en modo lote (el que saca el esqueleto y los pesos) exige licencia. Unity Personal
        # se activa iniciando sesion UNA vez desde la ventana del editor; despues la licencia queda
        # guardada en el equipo. Por eso la herramienta no pide credenciales: abre el editor y el
        # usuario entra ahi.
        self.boton_unity = ttk.Button(fila_botones, command=self.sesion_unity)
        self.boton_unity.pack(side="left", padx=(8, 0))
        self._texto(self.boton_unity, "btn_sesion_unity")

        # --- barra de accion anclada abajo.
        # Antes vivia dentro de la columna derecha, y como esa columna lleva las seis casillas de
        # opciones, con la ventana a 720 de alto el boton de extraer se salia de la pantalla. Aqui
        # reserva su sitio antes que el resto, asi que siempre se ve.
        # El Notebook de este tema deja un borde interior de 2 px, que subiria el boton a 634..685;
        # se le quitan esos 2 px al relleno de abajo para que siga exactamente en y=636..687.
        pie = ttk.Frame(cont, style="Panel.TFrame", padding=(22, 14, 22, 12))
        pie.pack(side="bottom", fill="x")
        self.boton_extraer = ttk.Button(pie, style="Grande.TButton", command=self.extraer)
        self.boton_extraer.pack(side="left")
        self._texto(self.boton_extraer, "pie_extraer")
        self.boton_abrir = ttk.Button(pie, command=self.abrir_carpeta, state="disabled")
        self.boton_abrir.pack(side="left", padx=(10, 0))
        self._texto(self.boton_abrir, "pie_abrir")
        self.progreso = ttk.Progressbar(pie, mode="determinate", maximum=100, length=200)
        self.progreso.pack(side="right", padx=(12, 0))
        self.etiqueta_progreso = ttk.Label(pie, style="SuavePanel.TLabel", wraplength=300)
        self.etiqueta_progreso.pack(side="right")
        idiomas.registrar(self._refrescar_progreso)

        # --- eleccion de personaje
        cuerpo = ttk.Frame(cont, padding=(22, 0, 22, 0))
        cuerpo.pack(fill="both", expand=True)

        izq = ttk.Frame(cuerpo)
        izq.pack(side="left", fill="both", expand=True)

        # La fila del titulo lleva tambien el selector de categoria: asi el filtro no roba alto a
        # una ventana que ya esta justa. El buscador de abajo sigue filtrando dentro de la categoria.
        fila_titulo = ttk.Frame(izq)
        fila_titulo.pack(fill="x")
        self._texto(ttk.Label(fila_titulo), "lista_paso1").pack(side="left")
        self._texto(ttk.Label(fila_titulo, style="Suave.TLabel"), "lista_mostrar").pack(
            side="left", padx=(20, 4))
        self.combo_categoria = ttk.Combobox(fila_titulo, state="readonly", width=18)
        self.combo_categoria.pack(side="left")
        self.combo_categoria.bind("<<ComboboxSelected>>", self.cambiar_categoria)
        self.etiqueta_categoria = ttk.Label(fila_titulo, text="", style="Suave.TLabel")
        self.etiqueta_categoria.pack(side="left", padx=(10, 0))
        self.categoria = "todo"
        self._clave_categoria = {}
        self._preparar_categorias()

        caja = ttk.Frame(izq)
        caja.pack(fill="x", pady=(4, 8))
        self.entrada_busqueda = ttk.Entry(caja, font=("Segoe UI", 11))
        self.entrada_busqueda.pack(side="left", fill="x", expand=True)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar())
        self._texto(ttk.Button(caja, command=self.filtrar), "comun_buscar").pack(side="left",
                                                                                 padx=(6, 0))

        contenedor = ttk.Frame(izq)
        contenedor.pack(fill="both", expand=True)

        # --- selector de traje. Aparece SOLO cuando el personaje elegido tiene mas de un traje:
        # antes, extraer `skull` devolvia a la vez el traje de ladron y el uniforme. Va en la columna
        # izquierda (no roba alto a la ventana) y se empaqueta justo encima de la lista.
        self.fila_traje = ttk.Frame(izq)
        self._texto(ttk.Label(self.fila_traje), "traje_label").pack(side="left")
        self.combo_traje = ttk.Combobox(self.fila_traje, state="readonly", width=34)
        self.combo_traje.pack(side="left", padx=(6, 0))
        self.combo_traje.bind("<<ComboboxSelected>>", self.cambiar_traje)
        self.etiqueta_traje = ttk.Label(self.fila_traje, text="", style="Suave.TLabel")
        self.etiqueta_traje.pack(side="left", padx=(10, 0))
        self._trajes_activos = []
        self._traje_activo = None
        self._contenedor_lista = contenedor

        barra = ttk.Scrollbar(contenedor, orient="vertical")
        self.lista = tk.Listbox(contenedor, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                selectbackground=COLOR_ACENTO, selectforeground="#ffffff",
                                font=("Consolas", 10), bd=0, highlightthickness=0,
                                yscrollcommand=barra.set, activestyle="none")
        barra.config(command=self.lista.yview)
        barra.pack(side="right", fill="y")
        self.lista.pack(side="left", fill="both", expand=True)
        self.lista.bind("<<ListboxSelect>>", lambda e: self.mostrar_detalle())

        # --- opciones y accion
        der = ttk.Frame(cuerpo, style="Panel.TFrame", padding=(14, 12), width=300)
        der.pack(side="right", fill="y", padx=(16, 0))
        der.pack_propagate(False)

        self._texto(ttk.Label(der, style="Panel.TLabel", font=("Segoe UI Semibold", 11)),
                    "opt_titulo").pack(anchor="w", pady=(0, 8))
        self.opciones = {}
        for clave, clave_texto, defecto in (
                ("mallas", "opt_mallas", True),
                ("texturas", "opt_texturas", True),
                ("materiales", "opt_materiales", True),
                ("esqueleto", "opt_esqueleto", True),
                ("previas", "opt_previas", True),
                ("fbx", "opt_fbx", True),
                ("armas", "opt_armas", True)):
            v = tk.BooleanVar(value=defecto)
            casilla = ttk.Checkbutton(der, variable=v)
            casilla.pack(anchor="w", pady=1)
            self._texto(casilla, clave_texto)
            self.opciones[clave] = v

        self._texto(ttk.Label(der, style="Panel.TLabel", font=("Segoe UI Semibold", 11)),
                    "opt_paso3").pack(anchor="w", pady=(18, 6))
        self._texto(ttk.Label(der, style="SuavePanel.TLabel", wraplength=250),
                    "opt_pie").pack(anchor="w")

        # --- modelo base de las skins.
        # La mitad de los personajes del juego son SKINS: solo traen cuerpo y ropa, y la cara vive
        # en otro personaje. Esa relacion no esta en ningun fichero del juego, asi que aqui se
        # declara. El buscador mira los 895 actores y los 16.535 bundles, para no tener que saberse
        # el nombre exacto del base.
        self._texto(ttk.Label(der, style="Panel.TLabel", font=("Segoe UI Semibold", 11)),
                    "base_titulo").pack(anchor="w", pady=(16, 4))
        self.etiqueta_base = ttk.Label(der, style="SuavePanel.TLabel", wraplength=250)
        self.etiqueta_base.pack(anchor="w")
        idiomas.registrar(self._refrescar_base)
        caja_base = ttk.Frame(der, style="Panel.TFrame")
        caja_base.pack(fill="x", pady=(4, 2))
        self.entrada_base = ttk.Entry(caja_base, font=("Segoe UI", 10))
        self.entrada_base.pack(side="left", fill="x", expand=True)
        self.entrada_base.bind("<Return>", lambda e: self.buscar_base())
        self._texto(ttk.Button(caja_base, command=self.buscar_base), "comun_buscar").pack(
            side="left", padx=(4, 0))
        cont_base = ttk.Frame(der, style="Panel.TFrame")
        cont_base.pack(fill="both", expand=True, pady=(4, 0))
        barra_base = ttk.Scrollbar(cont_base, orient="vertical")
        self.lista_bases = tk.Listbox(cont_base, bg=COLOR_PANEL, fg=COLOR_TEXTO, height=4,
                                      selectbackground=COLOR_ACENTO, selectforeground="#ffffff",
                                      font=("Consolas", 9), bd=0, highlightthickness=0,
                                      yscrollcommand=barra_base.set, activestyle="none")
        barra_base.config(command=self.lista_bases.yview)
        barra_base.pack(side="right", fill="y")
        self.lista_bases.pack(side="left", fill="both", expand=True)
        fila_botones = ttk.Frame(der, style="Panel.TFrame")
        fila_botones.pack(fill="x", pady=(4, 0))
        self._texto(ttk.Button(fila_botones, command=self.fijar_base), "base_fijar").pack(side="left")
        self._texto(ttk.Button(fila_botones, command=self.quitar_base), "base_quitar").pack(
            side="left", padx=(4, 0))
        self._resultados_base = []
        self._personaje_activo = None

        # --- registro en lenguaje llano
        self._texto(ttk.Label(cont), "log_titulo").pack(anchor="w", padx=22, pady=(8, 3))
        marco_log = ttk.Frame(cont, style="Panel.TFrame", padding=8)
        marco_log.pack(side="bottom", fill="x", padx=22, pady=(6, 14))
        self.registro = tk.Text(marco_log, height=4, bg=COLOR_PANEL, fg=COLOR_SUAVE,
                                font=("Consolas", 9), bd=0, highlightthickness=0,
                                state="disabled", wrap="word")
        self.registro.pack(fill="x")

        # --- pestana de HERRAMIENTAS.
        # Suite para trastear con CUALQUIER fichero del juego, no solo modelos de personaje:
        # explorador de bundles, inspector de uno concreto, buscador global de recursos, visor de
        # texturas y video/audio. Vive en su propio modulo (`herramientas.py`) para no tocar ni una
        # linea de la logica de extraccion, que sigue igual.
        self.panel_herramientas = herramientas.PanelHerramientas(
            self.pestana_herramientas, log=self.escribir)
        self.panel_herramientas.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ refrescos por idioma
    def _refrescar_estado(self):
        for clave, (clave_texto, args, bien) in self._estado_ultimo.items():
            et = self.etiquetas_estado.get(clave)
            if et is None:
                continue
            if bien is None:
                et.config(text=t(clave_texto, *args))
            else:
                et.config(text=t(clave_texto, *args),
                          foreground=COLOR_OK if bien else COLOR_AVISO)

    def _refrescar_progreso(self):
        clave, args = self._estado_clave
        if clave:
            self.etiqueta_progreso.config(text=t(clave, *args))

    def _refrescar_trajes(self):
        """Vuelve a poner los nombres de traje en el idioma nuevo, sin perder la seleccion."""
        lista = getattr(self, "_trajes_activos", None) or []
        if len(lista) <= 1:
            return
        i = self.combo_traje.current()
        valores = [t("traje_valor", self._nombre_traje(tr), tr.get("n_mallas", 0),
                     tr.get("n_texturas", 0)) for tr in lista]
        self.combo_traje.config(values=valores)
        self.combo_traje.current(i if 0 <= i < len(valores) else 0)
        self.etiqueta_traje.config(text=t("traje_cuenta", len(lista)))

    @staticmethod
    def _nombre_traje(tr):
        from . import trajes as _trajes
        return _trajes.nombre_traje(tr.get("clave")) if tr.get("clave") else tr.get("nombre", "")

    def _refrescar_base(self):
        self._actualizar_base()

    # ------------------------------------------------------------------ utilidades
    def escribir(self, texto):
        self.registro.configure(state="normal")
        self.registro.insert("end", texto.rstrip() + "\n")
        self.registro.see("end")
        self.registro.configure(state="disabled")

    def _vaciar_cola(self):
        """Recoge lo que dejan los hilos de trabajo y lo aplica a la ventana."""
        try:
            while True:
                tipo, carga = self.cola.get_nowait()
                if tipo == "log":
                    self.escribir(carga)
                elif tipo == "progreso":
                    self.progreso["value"] = carga
                elif tipo == "estado":
                    self._estado_clave = (None, ())
                    self.etiqueta_progreso.config(text=carga)
                elif tipo == "fin":
                    self._terminar(carga)
                elif tipo == "error":
                    self._terminar(None, carga)
        except queue.Empty:
            pass
        self.raiz.after(120, self._vaciar_cola)

    def _en_hilo(self, funcion):
        if self.trabajando:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_ocupado"))
            return
        self.trabajando = True
        self.boton_extraer.config(state="disabled")
        self.boton_comprobar.config(state="disabled")
        threading.Thread(target=funcion, daemon=True).start()

    def _terminar(self, resultado, error=None):
        self.trabajando = False
        self.boton_extraer.config(state="normal")
        self.boton_comprobar.config(state="normal")
        if error:
            self.progreso["value"] = 0
            self._estado_clave = ("msg_no_completar", ())
            self.etiqueta_progreso.config(text=t("msg_no_completar"))
            self.escribir("")
            self.escribir(t("msg_no_completar_detalle", error))
            messagebox.showerror(ajustes.NOMBRE, str(error)[:1200])
            return
        if resultado:
            self.ultima_carpeta = resultado
            self.progreso["value"] = 100
            self._estado_clave = ("pie_extraido", ())
            self.etiqueta_progreso.config(text=t("pie_extraido"))
            self.boton_abrir.config(state="normal")
            self.escribir("")
            self.escribir(t("msg_listo_en", resultado))
            messagebox.showinfo(ajustes.NOMBRE, t("msg_extraido_titulo", resultado))

    # ------------------------------------------------------------------ estado
    def comprobar_todo(self):
        def trabajo():
            try:
                self.cola.put(("log", t("log_comprobando_instalacion")))
                juego = ajustes.detectar_juego()
                if juego:
                    self.cola.put(("log", t("log_juego_encontrado", juego)))
                    self.raiz.after(0, lambda: self._marcar("juego", "est_encontrado", True, juego))
                else:
                    self.raiz.after(0, lambda: self._marcar(
                        "juego", "est_no_encontrado", False))
                    self.cola.put(("log", t("log_juego_no")))
                    return

                self.cola.put(("log", t("log_preparando_librerias")))
                py = dependencias.asegurar_dependencias(lambda s: self.cola.put(("log", "  " + s)))
                self.python_entorno = py
                self.raiz.after(0, lambda: self._marcar("librerias", "est_listas", True))

                self.cola.put(("log", t("log_leyendo_indice")))
                datos = indice.cargar_indice(lambda s: self.cola.put(("log", "  " + s)))
                self.datos_indice = datos
                self.personajes = indice.personajes(datos)
                self.raiz.after(0, lambda: self._marcar(
                    "indice", "est_personajes", True, len(self.personajes)))
                self.raiz.after(0, self.filtrar)
                bien, clave, args = self._estado_unity()
                self.raiz.after(0, lambda: self._marcar("esqueleto", clave, bien, *args))
                self.cola.put(("log", t("log_todo_listo")))
                self.cola.put(("estado", t("estado_elige_extraer")))
            except Exception as e:
                self.cola.put(("log", t("log_aviso", e)))
                self.cola.put(("estado", t("estado_revisa_avisos")))
        threading.Thread(target=trabajo, daemon=True).start()

    def _estado_unity(self):
        """(bien, clave_texto, args): si el editor, su licencia y el proyecto decompilado estan listos.

        El esqueleto y los pesos de piel son lo unico que no sale de los bundles: hay que montarlos
        dentro de Unity, asi que hacen falta las tres cosas.
        """
        ed = sesion_unity.resumen()
        if not ed["editor_instalado"]:
            return False, "est_unity_sin_editor", ()
        if not ed["licencia"]:
            return False, "est_unity_sin_licencia", ()
        if not unity.buscar_proyecto():
            return False, "est_unity_sin_proyecto", ()
        return True, "est_unity_ok", ()

    def _marcar(self, clave, clave_texto, bien, *args):
        self._estado_ultimo[clave] = (clave_texto, args, bien)
        et = self.etiquetas_estado[clave]
        et.config(text=t(clave_texto, *args), foreground=COLOR_OK if bien else COLOR_AVISO)

    def sesion_unity(self):
        """Comprueba la licencia de Unity y, si falta, abre el editor para iniciar sesion."""
        estado = sesion_unity.resumen()
        if estado["listo"]:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_unity_ya"))
            return
        if not estado["editor_instalado"]:
            messagebox.showwarning(ajustes.NOMBRE, t("msg_unity_sin_editor"))
            return
        bien, mensaje = sesion_unity.abrir_para_iniciar_sesion()
        if bien:
            messagebox.showinfo(ajustes.NOMBRE, mensaje)
        else:
            messagebox.showwarning(ajustes.NOMBRE, mensaje)
        self.comprobar_todo()

    def elegir_carpeta_juego(self):
        """Pide la carpeta del juego, la verifica y la guarda para que se recuerde."""
        inicial = ajustes.detectar_juego()
        carpeta = filedialog.askdirectory(
            title=t("dlg_carpeta_juego_titulo"),
            initialdir=str(inicial) if inicial else None)
        if not carpeta:
            return
        juego, bundles = ajustes.resolver_carpeta_juego(carpeta)
        if not bundles:
            messagebox.showwarning(ajustes.NOMBRE, t("msg_carpeta_no_valida"))
            return
        ajustes.guardar_config(carpeta_juego=str(juego))
        cuantos = ajustes.contar_bundles(bundles)
        self.escribir("")
        self.escribir(t("log_carpeta_fijada", juego))
        self.escribir(t("log_bundles_encontrados", cuantos))
        self._marcar("juego", "est_encontrado", True, juego)
        messagebox.showinfo(ajustes.NOMBRE, t("msg_carpeta_guardada", juego, cuantos))
        self.comprobar_todo()

    def actualizar_librerias(self):
        def trabajo():
            try:
                py = self.python_entorno or dependencias.asegurar_dependencias(
                    lambda s: self.cola.put(("log", "  " + s)))
                self.cola.put(("log", t("log_buscando_versiones")))
                nuevas = dependencias.revisar_actualizaciones(
                    py, lambda s: self.cola.put(("log", "  " + s)))
                if not nuevas:
                    self.cola.put(("log", t("log_todo_aldia")))
                    return
                nombres = ", ".join(n["nombre"] for n in nuevas)
                if messagebox.askyesno(ajustes.NOMBRE, t("msg_hay_nuevas", nombres)):
                    dependencias.actualizar(py, [n["nombre"] for n in nuevas],
                                            lambda s: self.cola.put(("log", "  " + s)))
                    self.cola.put(("log", t("log_librerias_actualizadas")))
            except Exception as e:
                self.cola.put(("log", t("log_no_actualizar", e)))
        self._en_hilo(trabajo)

    # ------------------------------------------------------------------ lista
    def _asegurar_catalogo(self):
        """Carga una sola vez el catalogo clasificado del juego (o [] si no esta construido)."""
        if getattr(self, "_catalogo", None) is None:
            if catalogo.disponible():
                try:
                    self._catalogo = catalogo.personajes()
                except Exception:
                    self._catalogo = []
            else:
                self._catalogo = []
        return self._catalogo

    def _preparar_categorias(self, seleccion=None):
        """Rellena el selector con las categorias y su numero de entradas."""
        cuentas = {}
        if catalogo.disponible():
            try:
                cuentas = catalogo.cuantas_por_categoria()
            except Exception:
                cuentas = {}
        total = sum(cuentas.values())
        orden = (("todo", "comun_todo"), ("personaje", "cat_personaje"), ("objeto", "cat_objeto"),
                 ("escenario", "cat_escenario"), ("efecto", "cat_efecto"), ("camara", "cat_camara"))
        valores = []
        self._clave_categoria = {}
        for clave, clave_texto in orden:
            nombre = t(clave_texto)
            if total:
                texto = t("cat_valor", nombre, total if clave == "todo" else cuentas.get(clave, 0))
            else:
                texto = nombre
            valores.append(texto)
            self._clave_categoria[texto] = clave
        self.combo_categoria.config(values=valores)
        clave_sel = seleccion if seleccion is not None else getattr(self, "categoria", "todo")
        for texto, clave in self._clave_categoria.items():
            if clave == clave_sel:
                self.combo_categoria.set(texto)
                break
        else:
            if valores:
                self.combo_categoria.set(valores[0])

    def cambiar_categoria(self, _evento=None):
        self.categoria = self._clave_categoria.get(self.combo_categoria.get(), "todo")
        self.filtrar()

    def filtrar(self):
        texto = self.entrada_busqueda.get().strip().lower()
        self.lista.delete(0, "end")
        self.mostrar = []
        # El catalogo del juego sale de abrir los 906 bundles de modelo y anotar que llevan dentro,
        # asi que conoce 442 actores. El indice de bundles solo adivinaba 31, y unicamente los que
        # llevan el codigo en el nombre del fichero. Si el catalogo esta construido, manda el.
        fuente = self._asegurar_catalogo() or self.personajes
        categoria = getattr(self, "categoria", "todo")
        if getattr(self, "_catalogo", None) and categoria != "todo":
            fuente = [p for p in fuente if p.get("categoria") == categoria]
        for p in fuente:
            etiqueta = p["etiqueta"]
            if texto and texto not in etiqueta.lower():
                continue
            self.lista.insert("end", "  " + etiqueta)
            self.mostrar.append(p)
        et = getattr(self, "etiqueta_categoria", None)
        if et is not None:
            et.config(text=t("lista_cuenta", len(self.mostrar)))

    def mostrar_detalle(self):
        sel = self.lista.curselection()
        if not sel:
            return
        p = self.mostrar[sel[0]]
        self._personaje_activo = p
        self.escribir("")
        self.escribir(t("det_ficha", p["etiqueta"], len(p["ficheros"]), ", ".join(p["tipos"])))
        self._actualizar_trajes(p)
        if p.get("piezas"):
            self.escribir(t("det_trae", ", ".join(p["piezas"])))
        if p.get("es_skin"):
            self.escribir(t("det_skin"))
        for f in p["ficheros"]:
            self.escribir("   %s" % f)
        if p.get("ficheros_otros"):
            self.escribir(t("det_otros", len(p["ficheros_otros"])))
        self._actualizar_base()

    # ------------------------------------------------------------------ traje
    def _actualizar_trajes(self, p):
        """Rellena el selector de traje. Si el actor solo tiene uno, el control no se muestra.

        El traje es un dato real del juego (uniforme, traje de ladron, banador...), distinto de las
        variantes de calidad (`lodlow`) y de expresion (`bs`), que van dentro del mismo traje.
        """
        lista = p.get("trajes") or []
        self._trajes_activos = lista
        if len(lista) <= 1:
            self.fila_traje.pack_forget()
            self._traje_activo = lista[0] if lista else None
            return
        valores = [t("traje_valor", self._nombre_traje(tr), tr.get("n_mallas", 0),
                     tr.get("n_texturas", 0)) for tr in lista]
        self.combo_traje.config(values=valores)
        self.combo_traje.current(0)
        self._traje_activo = lista[0]
        self.fila_traje.pack(fill="x", pady=(0, 6), before=self._contenedor_lista)
        self.etiqueta_traje.config(text=t("traje_cuenta", len(lista)))
        self.escribir(t("det_trajes", ", ".join(self._nombre_traje(tr) for tr in lista)))
        self.escribir(t("det_traje_aviso"))

    def cambiar_traje(self, _evento=None):
        i = self.combo_traje.current()
        if 0 <= i < len(self._trajes_activos):
            self._traje_activo = self._trajes_activos[i]
            self.escribir(t("det_traje_elegido", self._nombre_traje(self._traje_activo),
                            len(self._traje_activo["ficheros"])))

    # ------------------------------------------------------------------ modelo base
    def _actualizar_base(self):
        """Muestra el base declarado del personaje elegido y, si no hay, propone uno."""
        p = self._personaje_activo
        if not p:
            return
        if p.get("categoria") and p["categoria"] != "personaje":
            self.etiqueta_base.config(
                text=t("base_msg_no_personaje"), foreground=COLOR_SUAVE)
            return
        try:
            declarado = bases.base_de(p["id"])
        except Exception:
            declarado = None
        if declarado:
            nombre = (bases.entrada(declarado) or {}).get("nombre") or declarado
            self.etiqueta_base.config(
                text=t("base_msg_declarado", nombre, declarado), foreground=COLOR_OK)
            self.escribir(t("det_base_declarado", nombre))
            return
        if not p.get("es_skin"):
            self.etiqueta_base.config(text=t("base_msg_propia"), foreground=COLOR_SUAVE)
            return
        # es una skin sin base: se intenta proponer uno con lo que dicen los bundles
        try:
            cand = bases.sugerencias(p["id"], limite=4)
        except Exception:
            cand = []
        if cand:
            self._resultados_base = cand
            self.lista_bases.delete(0, "end")
            for c in cand:
                self.lista_bases.insert("end", "  %s  (%s)" % (c["id"], ",".join(c["grupo"])))
            primero = cand[0]
            self.etiqueta_base.config(
                text=t("base_msg_posible", primero["id"]), foreground=COLOR_AVISO)
            self.escribir(t("det_base_posible", primero["id"], primero["motivo"]))
        else:
            self.lista_bases.delete(0, "end")
            self._resultados_base = []
            self.etiqueta_base.config(text=t("base_msg_sin_pista"), foreground=COLOR_AVISO)

    def buscar_base(self):
        texto = self.entrada_base.get().strip()
        if len(texto) < 2:
            messagebox.showinfo(ajustes.NOMBRE, t("base_err_corto"))
            return
        try:
            resultados = bases.buscar(texto, limite=40, solo_con_cara=True)
        except Exception as e:
            messagebox.showwarning(ajustes.NOMBRE, t("base_err_buscar", e))
            return
        self._resultados_base = [{"id": r["id"], "nombre": r["nombre"], "grupo": [r["id"]],
                                  "motivo": r["etiqueta"]} for r in resultados]
        self.lista_bases.delete(0, "end")
        for r in self._resultados_base:
            marca = t("base_marca_cara") if r.get("tiene_cara", True) else "    "
            self.lista_bases.insert("end", "  %s %-16s %s" % (marca, r["id"], r["nombre"]))
        if not self._resultados_base:
            self.lista_bases.insert("end", t("base_lista_vacia"))

    def fijar_base(self):
        p = self._personaje_activo
        if not p:
            messagebox.showinfo(ajustes.NOMBRE, t("base_err_sin_personaje"))
            return
        sel = self.lista_bases.curselection()
        if not sel or not self._resultados_base:
            messagebox.showinfo(ajustes.NOMBRE, t("base_err_sin_seleccion"))
            return
        cand = self._resultados_base[sel[0]]
        try:
            d = bases.declarar(p["id"], cand["id"], nota=cand.get("motivo", ""), origen="usuario")
        except Exception as e:
            messagebox.showwarning(ajustes.NOMBRE, str(e))
            return
        self.escribir(t("det_base_fijado", d.get("nombre") or cand["id"], p["id"]))
        self._actualizar_base()

    def quitar_base(self):
        p = self._personaje_activo
        if not p:
            return
        if bases.quitar(p["id"]):
            self.escribir(t("det_base_quitado", p["id"]))
        self._actualizar_base()

    # ------------------------------------------------------------------ extraccion
    def extraer(self):
        sel = self.lista.curselection()
        if not sel:
            messagebox.showinfo(ajustes.NOMBRE, t("extraer_err_sin_personaje"))
            return
        if not self.datos_indice:
            messagebox.showinfo(ajustes.NOMBRE, t("extraer_err_sin_indice"))
            return
        p = self.mostrar[sel[0]]
        elegidas = {k: v.get() for k, v in self.opciones.items()}
        # que traje: si el actor solo tiene uno, ese; si tiene varios, el elegido en el desplegable.
        lista_trajes = p.get("trajes") or []
        traje = None
        if len(lista_trajes) == 1:
            traje = lista_trajes[0]
        elif lista_trajes:
            i = self.combo_traje.current() if self._personaje_activo is p else -1
            traje = lista_trajes[i] if 0 <= i < len(lista_trajes) else lista_trajes[0]
        # El esqueleto y los pesos de piel necesitan Unity. Si no esta listo, se avisa antes de
        # lanzar nada: sin este paso el modelo sale completo salvo la armadura, y conviene que el
        # usuario sepa por que. Los escenarios, props y efectos NO tienen esqueleto de personaje,
        # asi que no se les pide Unity.
        es_personaje = p.get("categoria", "personaje") == "personaje"
        if not es_personaje:
            elegidas["esqueleto"] = False
        if elegidas.get("esqueleto") and es_personaje:
            bien, clave, args = self._estado_unity()
            if not bien:
                if not messagebox.askyesno(
                        ajustes.NOMBRE,
                        t("extraer_pregunta_unity", t(clave, *args))):
                    return
        self.progreso["value"] = 0
        base = None
        try:
            base = bases.base_de(p["id"])
        except Exception:
            base = None

        def trabajo():
            try:
                from . import extractor
                destino = extractor.extraer_personaje(
                    p, self.datos_indice, ajustes.carpeta_salida(), elegidas,
                    lambda s: self.cola.put(("log", "  " + s)),
                    lambda v: self.cola.put(("progreso", v)),
                    lambda s: self.cola.put(("estado", s)),
                    base=base, traje=traje)
                self.cola.put(("fin", str(destino)))
            except Exception as e:
                self.cola.put(("error", str(e)))
        self._en_hilo(trabajo)

    def abrir_carpeta(self):
        if not self.ultima_carpeta:
            return
        try:
            os.startfile(self.ultima_carpeta)  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", str(self.ultima_carpeta)])


def arrancar():
    ajustes.preparar_carpetas()
    raiz = tk.Tk()
    Aplicacion(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    arrancar()
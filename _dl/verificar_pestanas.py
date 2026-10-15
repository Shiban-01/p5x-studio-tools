"""Evidencia por pestana: la suite de Herramientas entera, en los dos idiomas.

Saca las cadenas visibles de cada pestana por separado (para demostrar que la suite de
herramientas tambien cambia) y el registro de mensajes tal como sale al arrancar en ingles.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")

import tkinter as tk

from p5x_studio import ajustes, idiomas
from p5x_studio.gui import Aplicacion


def cadenas_de(raiz):
    salida = []

    def visita(w):
        try:
            from tkinter import ttk
            if isinstance(w, ttk.Notebook):
                for tab in w.tabs():
                    salida.append(w.tab(tab, "text"))
            if isinstance(w, ttk.Treeview):
                for c in w["columns"]:
                    salida.append(w.heading(c)["text"])
            if isinstance(w, ttk.Combobox):
                salida.append(w.get())
            # el Listbox lleva DATOS (nombres de personaje), no texto de interfaz: se deja fuera
        except Exception:
            pass
        try:
            txt = w.cget("text")
            if isinstance(txt, str):
                salida.append(txt)
        except Exception:
            pass
        for h in w.winfo_children():
            visita(h)

    visita(raiz)
    return sorted({" ".join((s or "").split()) for s in salida if (s or "").strip()})


def asentar(raiz, segundos=6.0):
    t0 = time.time()
    while time.time() - t0 < segundos:
        raiz.update()
        time.sleep(0.05)


def main():
    ajustes.guardar_config(idioma="es")
    raiz = tk.Tk()
    app = Aplicacion(raiz)
    asentar(raiz)

    pan = app.panel_herramientas
    info = {"es": {}, "en": {}}
    info["es"]["extraccion"] = cadenas_de(app.pestana_extraccion)
    info["es"]["herramientas"] = cadenas_de(app.pestana_herramientas)
    info["es"]["subpestanas"] = [pan.cuaderno.tab(t, "text") for t in pan.cuaderno.tabs()]
    info["es"]["columnas_explorador"] = [pan.arbol_explorador.heading(c)["text"]
                                         for c in pan.arbol_explorador["columns"]]

    app.combo_idioma.set(idiomas.IDIOMAS["en"])
    app.cambiar_idioma()
    raiz.update()
    asentar(raiz, 1.0)
    info["en"]["extraccion"] = cadenas_de(app.pestana_extraccion)
    info["en"]["herramientas"] = cadenas_de(app.pestana_herramientas)
    info["en"]["subpestanas"] = [pan.cuaderno.tab(t, "text") for t in pan.cuaderno.tabs()]
    info["en"]["columnas_explorador"] = [pan.arbol_explorador.heading(c)["text"]
                                         for c in pan.arbol_explorador["columns"]]

    info["resumen"] = {
        "extraccion_es": len(info["es"]["extraccion"]),
        "extraccion_en": len(info["en"]["extraccion"]),
        "herramientas_es": len(info["es"]["herramientas"]),
        "herramientas_en": len(info["en"]["herramientas"]),
        "herramientas_cambian": len(set(info["es"]["herramientas"]) - set(info["en"]["herramientas"])),
        "subpestanas_es": info["es"]["subpestanas"],
        "subpestanas_en": info["en"]["subpestanas"],
        "columnas_es": info["es"]["columnas_explorador"],
        "columnas_en": info["en"]["columnas_explorador"],
    }
    # muestra de cadenas de la suite que han cambiado
    info["muestra_herramientas"] = [
        {"es": s} for s in info["es"]["herramientas"][:0]
    ]
    raiz.destroy()

    # registro tal cual sale al arrancar YA en ingles
    raiz2 = tk.Tk()
    app2 = Aplicacion(raiz2)
    asentar(raiz2, 6.0)
    log_en = app2.registro.get("1.0", "end").strip().splitlines()
    info["registro_arranque_en"] = log_en[:8]
    raiz2.destroy()

    ajustes.guardar_config(idioma="es")
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
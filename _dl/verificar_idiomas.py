"""Verificacion real del selector de idiomas de P5X Studio.

Mide, sobre la ventana de verdad (tkinter dibujado), no sobre el codigo:
  1. recuento de cadenas visibles en cada idioma y cuales NO cambian;
  2. que no queda espanol suelto cuando esta en ingles;
  3. que el cambio es en caliente y conserva categoria, busqueda y lista;
  4. geometria: donde cae el boton Extraer en cada idioma;
  5. persistencia: el idioma elegido se lee al arrancar de nuevo.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")

import tkinter as tk
from tkinter import ttk

from p5x_studio import ajustes, idiomas
from p5x_studio.gui import Aplicacion

CONFIG = r"C:/Users/Lukas/p5x-datamining/p5x_studio/config.json"

# nombres propios del juego que NO se traducen (personajes, trajes internos, ficheros)
INTOCABLES = {
    "wonder", "skull", "chord", "kotone", "theo", "theodore", "panther", "fox", "queen",
    "noir", "crow", "violet", "mona", "joker", "bundle", "bundles", "usm", "awb", "hca",
    "ffmpeg", "wannacri", "vgmstream", "assetstudio", "assetstudiomodcli", "blender",
    "unity", "fbx", "glb", "obj", "mtl", "png", "json", "md", "pc077", "pc079", "n040",
    "pathid", "lod", "skin", "bm", "mb", "pathid",
}


def cadenas_de(raiz) -> list[str]:
    """Recorre el arbol de widgets y saca TODO el texto visible."""
    salida: list[str] = []

    def visita(w):
        try:
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
    limpias = []
    for s in salida:
        s = " ".join((s or "").split())
        if s:
            limpias.append(s)
    return limpias


def asentar(raiz, segundos=6.0):
    """Deja correr los `after` (relleno del panel de herramientas, estado...) sin mainloop."""
    t0 = time.time()
    while time.time() - t0 < segundos:
        raiz.update()
        time.sleep(0.05)


def geometria(app):
    r = app.raiz
    b = app.boton_extraer
    y = b.winfo_rooty() - r.winfo_rooty()
    return {"ventana": (r.winfo_width(), r.winfo_height()),
            "extraer_y": y, "extraer_alto": b.winfo_height(),
            "extraer_rango": (y, y + b.winfo_height()),
            "extraer_texto": b.cget("text"),
            "header_idioma_y": app.combo_idioma.winfo_rooty() - r.winfo_rooty()}


def main():
    informe = {}
    # ---------------- arranque en espanol ----------------
    ajustes.guardar_config(idioma="es")
    raiz = tk.Tk()
    app = Aplicacion(raiz)
    asentar(raiz)
    es = cadenas_de(raiz)
    informe["es_arranque"] = {
        "idioma_activo": idiomas.idioma_actual(),
        "combo": app.combo_idioma.get(),
        "n_cadenas": len(set(es)),
        "n_cadenas_totales": len(es),
    }
    informe["geometria_es"] = geometria(app)

    # ---------------- estado que hay que conservar ----------------
    app.combo_categoria.set(next(t for t, c in app._clave_categoria.items() if c == "personaje"))
    app.combo_categoria.event_generate("<<ComboboxSelected>>")
    raiz.update()
    app.entrada_busqueda.insert(0, "pc079")
    app.filtrar()
    raiz.update()
    estado_antes = {
        "categoria": app.categoria,
        "busqueda": app.entrada_busqueda.get(),
        "n_lista": len(app.lista.get(0, "end")),
        "n_catalogo": len(app._catalogo or []),
    }

    # ---------------- cambio a ingles EN CALIENTE ----------------
    app.combo_idioma.set(idiomas.IDIOMAS["en"])
    app.cambiar_idioma()
    raiz.update()
    en = cadenas_de(raiz)
    informe["en_caliente"] = {
        "idioma_activo": idiomas.idioma_actual(),
        "combo": app.combo_idioma.get(),
        "n_cadenas": len(set(en)),
        "n_cadenas_totales": len(en),
    }
    informe["geometria_en"] = geometria(app)
    estado_despues = {
        "categoria": app.categoria,
        "busqueda": app.entrada_busqueda.get(),
        "n_lista": len(app.lista.get(0, "end")),
        "n_catalogo": len(app._catalogo or []),
    }
    informe["estado_conservado"] = {
        "antes": estado_antes, "despues": estado_despues,
        "igual": estado_antes == estado_despues,
    }

    # ---------------- que no queda espanol en ingles ----------------
    es_unicos = {v for k, v in idiomas.ES.items() if v != idiomas.EN.get(k)}
    restos = sorted({s for s in en if s in es_unicos})
    # cadenas compuestas: si empiezan por un valor espanol, tambien son resto
    compuestas = []
    for s in en:
        for v in es_unicos:
            if len(v) > 8 and s.startswith(v[:14]) and s not in es_unicos:
                compuestas.append(s)
                break
    informe["espanol_suelto_en_ingles"] = {
        "restos_exactos": restos,
        "restos_compuestos": sorted(set(compuestas)),
        "n": len(restos) + len(set(compuestas)),
    }
    informe["cambian"] = {
        "es": len(set(es)), "en": len(set(en)),
        "comunes": len(set(es) & set(en)),
        "solo_es": len(set(es) - set(en)), "solo_en": len(set(en) - set(es)),
        "ejemplos_solo_es": sorted(set(es) - set(en))[:6],
        "ejemplos_solo_en": sorted(set(en) - set(es))[:6],
    }

    # ---------------- persistencia ----------------
    config = json.loads(open(CONFIG, encoding="utf-8").read())
    informe["config_tras_cambio"] = config.get("idioma")
    raiz.destroy()

    raiz2 = tk.Tk()
    app2 = Aplicacion(raiz2)
    asentar(raiz2, 3.0)
    informe["rearranque"] = {
        "idioma_activo": idiomas.idioma_actual(),
        "combo": app2.combo_idioma.get(),
        "titulo_extraer": app2.boton_extraer.cget("text"),
        "tab0": app2.cuaderno.tab(app2.pestana_extraccion, "text"),
    }
    informe["geometria_rearranque_en"] = geometria(app2)
    raiz2.destroy()

    # ---------------- vuelta a espanol y persistencia ----------------
    ajustes.guardar_config(idioma="es")
    print(json.dumps(informe, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
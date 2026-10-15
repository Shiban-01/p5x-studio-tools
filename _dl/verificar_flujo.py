"""Verificacion del flujo completo dirigido desde la interfaz de verdad.

Elige un personaje con varios trajes (skull), elige el traje en el desplegable con RATON REAL,
comprueba que el personaje sigue seleccionado y pulsa Extraer (el boton real). Espera a que
termine y comprueba los ficheros. Repite con un personaje de un solo traje en espanol.

Uso: python _dl/verificar_flujo.py
"""
import json
import sys
import time
import ctypes
from pathlib import Path
import tkinter as tk

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, dependencias, gui  # noqa: E402

u = ctypes.windll.user32


def click(x, y, pausa=0.5):
    u.SetCursorPos(int(x), int(y)); time.sleep(0.12)
    u.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.06)
    u.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(pausa)


def foco(raiz):
    try:
        u.SetForegroundWindow(int(raiz.frame(), 16))
    except Exception:
        u.SetForegroundWindow(raiz.winfo_id())
    time.sleep(0.25)


ajustes.preparar_carpetas()
AVISOS = []
gui.messagebox.showinfo = lambda *a, **k: AVISOS.append(("info", a[1] if len(a) > 1 else ""))
gui.messagebox.showwarning = lambda *a, **k: AVISOS.append(("warn", a[1] if len(a) > 1 else ""))
gui.messagebox.showerror = lambda *a, **k: AVISOS.append(("error", a[1] if len(a) > 1 else ""))
# la comprobacion de librerias consulta PyPI: se salta SOLO eso
dependencias.asegurar_dependencias = lambda progreso=None: dependencias.python_entorno()

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
raiz.geometry("1020x701+0+0")
raiz.update()
raiz.lift(); raiz.attributes("-topmost", True)

ESTADO = {"t0": time.time()}


def paso_esperar_indice():
    if app.datos_indice is not None and app.mostrar:
        print("indice cargado: %d entradas en la lista" % len(app.mostrar))
        paso_english()
    elif time.time() - ESTADO["t0"] > 200:
        print("TIMEOUT esperando el indice")
        raiz.quit()
    else:
        raiz.after(300, paso_esperar_indice)


def seleccionar_con_raton(texto, pid, n_trajes):
    """Busca, hace clic en la fila correcta y (si aplica) en el traje. Devuelve True si quedo."""
    app.entrada_busqueda.delete(0, "end"); app.entrada_busqueda.insert(0, texto)
    app.filtrar(); raiz.update()
    idx = next((i for i, p in enumerate(app.mostrar) if p["id"] == pid), None)
    if idx is None:
        print("   no encuentro", pid); return False
    for intento in range(4):
        foco(raiz); raiz.update()
        lb = app.lista
        caja = lb.bbox(idx)  # (x, y, w, h) de la fila visible
        if not caja:
            print("   fila %d no visible" % idx); return False
        x, y, w, h = caja
        click(lb.winfo_rootx() + x + 40, lb.winfo_rooty() + y + h / 2)
        raiz.update()
        sel = app.lista.curselection()
        if sel and app.mostrar[sel[0]]["id"] == pid:
            break
        print("   reintento de clic (cayo en %s)" % (app._personaje_activo and app._personaje_activo["id"]))
    print("   clic en %s -> sel=%s personaje=%s" % (
        pid, app.lista.curselection(), app._personaje_activo and app._personaje_activo["id"]))
    if not app.lista.curselection():
        return False
    if n_trajes > 1:
        cb = app.combo_traje
        print("   fila traje visible:", bool(app.fila_traje.winfo_ismapped()),
              "valores:", list(cb.cget("values")))
        for intento in range(4):
            foco(raiz); raiz.update()
            click(cb.winfo_rootx() + 60, cb.winfo_rooty() + cb.winfo_height() / 2)
            raiz.update()
            pop = str(cb.tk.call("ttk::combobox::PopdownWindow", cb)) + ".f.l"
            if not cb.tk.call("winfo", "ismapped", pop):
                continue
            bx, by, bw, bh = cb.tk.call(pop, "bbox", 1)  # fila 1 del popdown
            click(int(cb.tk.call("winfo", "rootx", pop)) + bx + 40,
                  int(cb.tk.call("winfo", "rooty", pop)) + by + bh / 2)
            raiz.update()
            if cb.current() == 1:
                break
        print("   traje elegido: %s (combo idx %s)" % (
            app._traje_activo and app._traje_activo.get("clave"), cb.current()))
    return True


def paso_english():
    print("\n===== INGLES: skull (2 trajes), elegir 'uniform' =====")
    app.combo_idioma.set("English")
    app.combo_idioma.event_generate("<<ComboboxSelected>>")
    raiz.update()
    ok = seleccionar_con_raton("skull", "skull", 2)
    print("   personaje sigue seleccionado:", bool(app.lista.curselection()), "| extraer dira ok:", app._personaje_seleccionado() is not None)
    ESTADO["en_ok"] = ok
    ESTADO["en_sel"] = bool(app.lista.curselection())
    ESTADO["en_traje"] = app._traje_activo and app._traje_activo.get("clave")
    for k, v in app.opciones.items():
        v.set(k in ("mallas", "texturas", "materiales"))
    ESTADO["t1"] = time.time()
    ESTADO["destino_en"] = None
    app.boton_extraer.invoke()
    raiz.after(500, lambda: esperar_fin("en"))


def esperar_fin(cual):
    if (not app.trabajando) and app.ultima_carpeta:
        salida = Path(app.ultima_carpeta)
        ESTADO["destino_" + cual] = salida
        res = json.loads((salida / "SUMMARY.json").read_text(encoding="utf-8"))
        nm = sum(len(v["mallas"]) for v in res["partes"].values())
        nt = sum(len(v["texturas"]) for v in res["partes"].values())
        arch = [f for f in salida.rglob("*") if f.is_file()]
        print("   EXTRACCION OK en %.1fs -> %s" % (time.time() - ESTADO["t1"], salida.name))
        print("   RESUMEN: %d mallas, %d texturas, %d ficheros, %.1f MB, fbx=%s, TRAJE=%s" % (
            nm, nt, len(arch), sum(f.stat().st_size for f in arch) / 1048576, res.get("fbx"),
            res.get("traje")))
        ESTADO[cual + "_res"] = (nm, nt, len(arch), res.get("traje"))
        if cual == "en":
            print("   avisos durante el flujo ingles:", AVISOS[-2:])
            raiz.after(300, paso_espanol)
        else:
            raiz.after(300, paso_geometria)
        return
    if (not app.trabajando) and not app.ultima_carpeta:
        print("   la extraccion no dio resultado; avisos:", AVISOS[-3:])
        print(app.registro.get("1.0", "end"))
        raiz.quit(); return
    if time.time() - ESTADO["t1"] > 400:
        print("   TIMEOUT en la extraccion"); raiz.quit(); return
    raiz.after(500, lambda: esperar_fin(cual))


def paso_espanol():
    print("\n===== ESPANOL: personaje de UN solo traje (n_yiyuan) =====")
    app.combo_idioma.set("Español")
    app.combo_idioma.event_generate("<<ComboboxSelected>>")
    raiz.update()
    print("   idioma:", app.combo_idioma.get(), "| combo traje visible:",
          bool(app.fila_traje.winfo_ismapped()))
    ok = seleccionar_con_raton("n_yiyuan", "n_yiyuan", 1)
    print("   seleccionado:", bool(app.lista.curselection()), "| traje (unico):",
          app._traje_activo and app._traje_activo.get("clave"))
    ESTADO["es_sel"] = bool(app.lista.curselection())
    # probar tambien el aviso en espanol sin seleccion
    app.lista.selection_clear(0, "end"); raiz.update()
    antes = len(AVISOS)
    app.boton_extraer.invoke(); raiz.update()
    if len(AVISOS) > antes:
        print("   aviso sin personaje (ES):", repr(AVISOS[-1][1]))
    # volver a seleccionar y extraer
    seleccionar_con_raton("n_yiyuan", "n_yiyuan", 1)
    for k, v in app.opciones.items():
        v.set(k in ("mallas", "texturas", "materiales"))
    ESTADO["t1"] = time.time()
    app.boton_extraer.invoke()
    raiz.after(500, lambda: esperar_fin("es"))


def paso_geometria():
    print("\n===== GEOMETRIA (boton Extraer) =====")
    for idioma in ("Español", "English"):
        app.combo_idioma.set(idioma)
        app.combo_idioma.event_generate("<<ComboboxSelected>>")
        raiz.update(); raiz.update_idletasks(); raiz.update()
        b = app.boton_extraer
        y0 = b.winfo_rooty() - raiz.winfo_rooty()
        print("   %-8s ventana=%dx%d boton y=%d..%d (raiz h=%d)" % (
            idioma, raiz.winfo_width(), raiz.winfo_height(), y0, y0 + b.winfo_height(),
            raiz.winfo_height()))
    print("\nRESUMEN:", json.dumps({k: (str(v) if isinstance(v, Path) else v)
                                    for k, v in ESTADO.items() if k != "t0"}, ensure_ascii=False))
    raiz.quit()


raiz.after(500, paso_esperar_indice)
raiz.mainloop()
print("FIN")
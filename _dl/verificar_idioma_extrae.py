"""Extrae tras cambiar de idioma: confirma que el traje elegido (uniform) se mantiene."""
import json, sys, time
from pathlib import Path
import tkinter as tk
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, dependencias, gui
ajustes.preparar_carpetas()
avisos = []
gui.messagebox.showinfo = lambda *a, **k: avisos.append(a[1] if len(a) > 1 else "")
gui.messagebox.showerror = lambda *a, **k: avisos.append("ERROR " + (a[1] if len(a) > 1 else ""))
dependencias.asegurar_dependencias = lambda progreso=None: dependencias.python_entorno()
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x701+0+0"); raiz.update()
EST = {"t0": time.time()}

def esperar():
    if app.datos_indice and app.mostrar:
        arrancar()
    elif time.time() - EST["t0"] > 200:
        print("TIMEOUT"); raiz.quit()
    else:
        raiz.after(300, esperar)

def arrancar():
    app.combo_idioma.set("Español"); app.combo_idioma.event_generate("<<ComboboxSelected>>"); raiz.update()
    app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()
    idx = next(i for i,p in enumerate(app.mostrar) if p["id"]=="skull")
    app.lista.selection_clear(0,"end"); app.lista.selection_set(idx); app.lista.activate(idx)
    app.lista.event_generate("<<ListboxSelect>>"); raiz.update()
    app.combo_traje.current(1); app.combo_traje.event_generate("<<ComboboxSelected>>"); raiz.update()
    print("elegido: %s / %s (idioma %s)" % (app._personaje_activo["id"], app._traje_activo.get("clave"), app.combo_idioma.get()))
    # cambiar de idioma DESPUES de elegir
    app.combo_idioma.set("English"); app.combo_idioma.event_generate("<<ComboboxSelected>>"); raiz.update()
    print("tras cambiar idioma: sel=%s traje=%s" % (app.lista.curselection(), app._traje_activo.get("clave")))
    for k,v in app.opciones.items(): v.set(k in ("mallas","texturas","materiales"))
    EST["t1"]=time.time(); EST["ok"]=None
    app.boton_extraer.invoke(); raiz.after(400, fin)

def fin():
    if (not app.trabajando) and app.ultima_carpeta:
        d = Path(app.ultima_carpeta)
        res = json.loads((d/"SUMMARY.json").read_text(encoding="utf-8"))
        print("EXTRACCION tras cambio de idioma -> %s | TRAJE=%s | mallas=%d" % (
            d.name, res.get("traje"), sum(len(v["mallas"]) for v in res["partes"].values())))
        print("avisos:", avisos[-1:])
        raiz.quit(); return
    if (not app.trabajando) and not app.ultima_carpeta:
        print("no extrajo:", avisos[-2:]); raiz.quit(); return
    if time.time()-EST["t1"]>300: print("TIMEOUT extraccion"); raiz.quit(); return
    raiz.after(400, fin)

raiz.after(400, esperar); raiz.mainloop()
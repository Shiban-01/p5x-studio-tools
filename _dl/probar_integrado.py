"""Prueba la app COMPLETA: dos pestanas, geometria del boton Extraer, y cada herramienta."""
import sys
import time
import tkinter as tk

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, gui  # noqa: E402

ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None      # sin hilos ni indice para medir
raiz = tk.Tk()
app = gui.Aplicacion(raiz)


def bombear(segundos):
    fin = time.time() + segundos
    while time.time() < fin:
        raiz.update_idletasks()
        raiz.update()
        time.sleep(0.02)


def esperar_libre(limite=30):
    """Espera a que el panel no tenga una tarea en marcha (si no, _en_hilo abre un dialogo modal)."""
    fin = time.time() + limite
    while time.time() < fin:
        raiz.update_idletasks()
        raiz.update()
        if not app.panel_herramientas.trabajando:
            return True
        time.sleep(0.05)
    return False


raiz.update_idletasks()
raiz.update()
bombear(2.5)          # deja terminar el arranque automatico del panel
esperar_libre()


def caja_abs(w):
    x = y = 0
    p = w
    while p is not None:
        x += p.winfo_x()
        y += p.winfo_y()
        p = p.master
    return x, y, x + w.winfo_width(), y + w.winfo_height()


print("=== 1. ventana y pestanas ===")
print("ventana:", raiz.winfo_width(), "x", raiz.winfo_height(), " geometry:", raiz.geometry())
print("pestanas:", [app.cuaderno.tab(t, "text") for t in app.cuaderno.tabs()])

print("\n=== 2. boton Extraer ===")
bx0, by0, bx1, by1 = caja_abs(app.boton_extraer)
print("extraer (abs):", (bx0, by0, bx1, by1))
print("  -> dentro de la ventana:", 0 <= by0 and by1 <= raiz.winfo_height(),
      " (ventana de %d px)" % raiz.winfo_height())
# nada lo tapa: ningun otro widget mapeado se solapa con el boton
def _todos(w):
    yield w
    for h in w.winfo_children():
        yield from _todos(h)


def _ancestros(w):
    s = set()
    p = w.master
    while p is not None:
        s.add(str(p))
        p = p.master
    return s


anc = _ancestros(app.boton_extraer)
solapados = []
for w in _todos(raiz):
    if w is app.boton_extraer or str(w) in anc:
        continue
    if not w.winfo_ismapped():
        continue
    try:
        wx0, wy0, wx1, wy1 = caja_abs(w)
    except tk.TclError:
        continue
    if wx0 < bx1 and wx1 > bx0 and wy0 < by1 and wy1 > by0:
        solapados.append((str(w), (wx0, wy0, wx1, wy1)))
print("  -> widgets que solapan el boton:", solapados or "ninguno")
print("  -> nada lo tapa:", not solapados)
print("  -> ¿esta mapeado?:", bool(app.boton_extraer.winfo_ismapped()))

print("\n=== 3. cambiar de pestana ===")
app.cuaderno.select(app.pestana_herramientas)
raiz.update_idletasks()
raiz.update()
print("seleccionada:", app.cuaderno.tab(app.cuaderno.select(), "text"))
p = app.panel_herramientas
print("panel herramientas:", p.winfo_width(), "x", p.winfo_height(),
      "visible:", bool(p.winfo_ismapped()))
app.cuaderno.select(app.pestana_extraccion)
raiz.update_idletasks()
raiz.update()
print("vuelta a:", app.cuaderno.tab(app.cuaderno.select(), "text"))
bx0b, by0b, bx1b, by1b = caja_abs(app.boton_extraer)
print("extraer sigue en:", (bx0b, by0b, bx1b, by1b))

print("\n=== 4. herramientas dentro de la app ===")
app.cuaderno.select(app.pestana_herramientas)
raiz.update_idletasks()
raiz.update()
p.explorar()
bombear(0.4)
print("explorador:", p.etiq_explorador.cget("text"))
p.ent_recurso.delete(0, "end")
p.ent_recurso.insert(0, "chord_normal_face_bc")
p.buscar_recurso()
bombear(0.4)
print("buscador:", p.etiq_recursos.cget("text"))
for r in p.arbol_recursos.get_children()[:2]:
    print("   ", p.arbol_recursos.item(r, "values"))
p.ent_ruta.delete(0, "end")
p.ent_ruta.insert(0, "110/shared_merged_5c36cff7.bundle")
p.abrir_inspector()
esperar_libre()
print("inspector:", len(p.arbol_inspector.get_children()), "recursos;", p.estado.cget("text"))
p.comprobar_herramientas()
esperar_libre()
for k, et in p.etiquetas_herr.items():
    print("   %-10s %s" % (k, et.cget("text")))
p.listar_media()
bombear(0.5)
print("media:", p.etiq_media.cget("text"))

print("\n=== 4b. visor de texturas (con imagenes reales ya exportadas) ===")
p.ent_carpeta_img.delete(0, "end")
p.ent_carpeta_img.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl\herr_export")
p.listar_imagenes()
bombear(0.4)
print("visor:", p.info_img.cget("text"))
if p.lista_imgs.size():
    p.lista_imgs.selection_set(0)
    p.mostrar_imagen()
    bombear(0.4)
    print("imagen mostrada:", p.info_img.cget("text"))

print("\n=== 4c. extraer un video corto y un audio desde el panel ===")
p.listar_media()
bombear(0.3)
# elegir wonder_jump_2.usm (corto)
idx = next((i for i, m in enumerate(p._media_sel) if m["nombre"] == "wonder_jump_2.usm"), None)
if idx is not None:
    p.lista_media.selection_clear(0, "end")
    p.lista_media.selection_set(idx)
    p.extraer_video_sel()
    esperar_libre(60)
    print("estado video:", p.estado.cget("text"))
# audio: elegir BGM_P3R_FunClub.awb
p.combo_media.set("Audio (.awb)")
p.pintar_media()
bombear(0.3)
idx = next((i for i, m in enumerate(p._media_sel) if m["nombre"] == "BGM_P3R_FunClub.awb"), None)
if idx is not None:
    p.lista_media.selection_clear(0, "end")
    p.lista_media.selection_set(idx)
    p.extraer_audio_sel()
    esperar_libre(60)
    print("estado audio:", p.estado.cget("text"))

print("\n=== 5. capturas ===")
# captura de pantalla completa con la pestana de herramientas delante
try:
    from PIL import ImageGrab
    raiz.lift()
    raiz.attributes("-topmost", True)
    raiz.focus_force()
    p.cuaderno.select(p.tab_explorador)
    bombear(1.2)
    img = ImageGrab.grab()
    salida = r"C:\Users\Lukas\p5x-datamining\_dl\herr_integrado.png"
    img.save(salida)
    print("captura:", salida, img.size)
    # la pestana de video y audio
    p.cuaderno.select(p.tab_media)
    bombear(0.8)
    img3 = ImageGrab.grab()
    salida3 = r"C:\Users\Lukas\p5x-datamining\_dl\herr_media.png"
    img3.save(salida3)
    print("captura:", salida3, img3.size)
    # la pestana de texturas, con una imagen cargada
    p.cuaderno.select(p.tab_texturas)
    p.listar_imagenes()
    if p.lista_imgs.size():
        p.lista_imgs.selection_set(0)
        p.mostrar_imagen()
    bombear(0.8)
    img4 = ImageGrab.grab()
    salida4 = r"C:\Users\Lukas\p5x-datamining\_dl\herr_texturas.png"
    img4.save(salida4)
    print("captura:", salida4, img4.size)
    # y una segunda con la pestana de extraccion delante, para ver que sigue igual
    app.cuaderno.select(app.pestana_extraccion)
    bombear(0.8)
    img2 = ImageGrab.grab()
    salida2 = r"C:\Users\Lukas\p5x-datamining\_dl\herr_extraccion.png"
    img2.save(salida2)
    print("captura:", salida2, img2.size)
    raiz.attributes("-topmost", False)
except Exception as e:
    print("no se pudo capturar:", e)

raiz.destroy()
print("OK")
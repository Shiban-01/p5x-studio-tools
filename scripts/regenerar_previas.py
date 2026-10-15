"""Regenera las vistas previas de un modelo ya extraido y comprueba que tengan color.

Se usa para rehacer las previews sin volver a extraer. La comprobacion del final es objetiva: mide
la saturacion media de cada PNG, de modo que no hay que fiarse de una impresion visual.
"""
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import preview  # noqa: E402

raiz = Path(sys.argv[1] if len(sys.argv) > 1
            else r"C:\Users\Lukas\p5x-datamining\_dl\prueba_herramienta\pc079_Kotone_Shiomi")

carpeta_previas = raiz / "preview"
carpeta_previas.mkdir(parents=True, exist_ok=True)
for f in carpeta_previas.glob("*.png"):
    f.unlink()

dibujadas = []
t0 = time.time()
for parte in ("body", "face", "hair", "weapons", "other"):
    carpeta = raiz / "01_model/obj" / parte
    if not carpeta.is_dir():
        continue
    for obj in sorted(carpeta.glob("*.obj")):
        if any(obj.stem.lower().endswith(s) for s in ("_lod", "_lodlow", "_shadow", "_lodhigh")):
            continue
        salida = carpeta_previas / ("%s_%s.png" % (parte, obj.stem))
        r = preview.dibujar(obj, salida, ruta_mtl=obj.with_suffix(".mtl"), texturas={},
                            titulo="Kotone Shiomi - %s" % obj.stem)
        if r:
            dibujadas.append(r)
preview.hoja_de_contacto(dibujadas, carpeta_previas / "lamina_completa.png",
                         titulo="Kotone Shiomi (PC079)")
print("   %d vistas previas en %.1f s" % (len(dibujadas), time.time() - t0))

print()
con_color = 0
total = 0
for f in sorted(carpeta_previas.glob("*.png")):
    if f.name.startswith("lamina"):
        continue
    total += 1
    im = Image.open(f).convert("RGB").resize((80, 80))
    px = list(im.getdata())
    sat = sum(max(p) - min(p) for p in px) / len(px)
    if sat > 6:
        con_color += 1
    print("   %-58s color medio %5.1f" % (f.stem[:58], sat))
print()
print("   vistas con color apreciable: %d de %d" % (con_color, total))

"""Hace el icono de 512x512 que pide la Workshop a partir de un render de referencia."""
from PIL import Image
import sys
origen, destino = sys.argv[1], sys.argv[2]
im = Image.open(origen).convert("RGB")
lado = min(im.size)
im = im.crop(((im.width - lado) // 2, (im.height - lado) // 2,
              (im.width + lado) // 2, (im.height + lado) // 2)).resize((512, 512), Image.LANCZOS)
im.save(destino, "JPEG", quality=92)
print("icono:", destino, im.size)

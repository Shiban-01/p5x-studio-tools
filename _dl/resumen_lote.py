"""Resume el informe del lote y deja una copia reducida de la hoja para poder revisarla."""
import json
from collections import Counter
from pathlib import Path

from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
inf = json.loads((DL / "lote_bustups_informe.json").read_text(encoding="utf-8"))
emp = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))

print("=== informe del lote ===")
print("hechos: %d | ya estaban: %d | con aviso o fallo: %d"
      % (inf["hechos"], inf["saltados"], len(inf["fallos"])))

reales = [f for f in inf["fallos"] if not f[1].startswith("AVISO")]
avisos = [f for f in inf["fallos"] if f[1].startswith("AVISO")]
print("   fallos de verdad: %d | avisos de capas: %d" % (len(reales), len(avisos)))
for n, m in reales:
    print("      %-50s %s" % (n, m[:70]))

sin_ojos = [n for n, m in avisos if "saltada" in m]
print()
print("   renders a los que les falta alguna capa (necesitan el prefab): %d" % len(sin_ojos))
for n in sin_ojos:
    print("      ", n)

print()
print("=== emparejado ===")
print("emparejados: %d | sin emparejar: %d" % (len(emp["emparejados"]), len(emp["fallos"])))
print("   confianza:", dict(Counter(v["confianza"] for v in emp["emparejados"].values())))
print("   sin emparejar, motivos:",
      dict(Counter(m.split(":")[0] for _, m in emp["fallos"])))

hoja = Image.open(DL / "hoja_bustups.png")
escala = 1000 / hoja.width
pequena = hoja.resize((1000, int(hoja.height * escala)), Image.LANCZOS)
pequena.save(DL / "hoja_bustups_pequena.png")
print()
print("hoja:", hoja.size, "| reducida:", pequena.size)
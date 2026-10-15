
import os, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import lote
DEST = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")

CASOS = [
    ("shared", "wuhexi_thief_mianju_matcap2", "002/shared_6d4da9f8.bundle"),
    ("shared", "main_albedo", "088/shared_16c55f4f.bundle"),
    ("shared", "base_albedo", "088/shared_16c55f4f.bundle"),
    ("ui_font", "font_n_1_kr", "052/ui_font_1f4dd105.bundle"),
    ("ui_font", "asiakchd-b", "084/ui_font_23d5e34c.bundle"),
    ("uitex_berworld", "cyberworld-start3-pic1-i18n", "081/uitex_berworld24ed307a.bundle"),
    ("uitex_oguelite", "text-rogue-difficut-boss", "102/uitex_oguelite69a22c5.bundle"),
    ("part_nd_thief", "wind_weapon_04", "121/part_nd_thiefc7a3d35.bundle"),
]
for pista_conj, pista, bundle in CASOS:
    cat = lote.etiqueta(lote.categoria_de(bundle))
    conj = lote.nombre_conjunto(bundle)
    carpeta = DEST / cat / conj
    if not carpeta.exists():
        print("%-34s CARPETA NO EXISTE: %s" % (pista, carpeta)); continue
    encontrados = [p.name for p in carpeta.iterdir() if pista.lower() in p.name.lower()]
    print("%-34s -> %s  (%d coincidencias)" % (pista, encontrados[:4], len(encontrados)))

"""Los 15 bust-ups sin cara, montados desde el extracto de la version GLOBAL.

Reutiliza la extraccion ya hecha en `prueba_global` (no vuelve a leer el juego).
"""
import sys
from pathlib import Path

RAIZ = Path(r"C:/Users/Lukas/p5x-datamining/p5x_studio")
sys.path.insert(0, str(RAIZ))
from p5x_studio import bustups  # noqa: E402

BASE = Path(r"C:/Users/Lukas/AppData/Local/hermes/cache/scratch/prueba_global")

print("=== indice del extracto global ===")
ind = bustups.indice(BASE, refrescar=True)
print("   nombres:", len(ind))
con_cara = [k for k in ind if "yan1" in k or "zui1" in k]
print("   nombres con ojos/boca:", len(con_cara))
print("   ejemplos:", con_cara[:4])
print()

SIN_CARA = [
    "UI-DialogShader-guaidao01-bainiao", "UI-DialogShader-guaidao01-longchuanxueshi",
    "UI-DialogShader-guaidao01-qinyinmianju", "UI-DialogShader-guaidao01-qinyinsp",
    "UI-DialogShader-guaidao01-qinyintoufa", "UI-DialogShader-guaidao01-tengchuanxueshi",
    "UI-DialogShader-guaidao01-xisenyangcai-face", "UI-DialogShader-guaidao01-yemaopengzi01",
    "UI-DialogShader-guaidao01-yemaopengzi02", "UI-DialogShader-guaidaofu-chibo",
    "UI-DialogShader-guaidaofu01-qinyin", "UI-DialogShader-guaidaofu02-chibo",
    "UI-DialogShader-sifu01-lizi", "UI-DialogShader-yongzhuang-lizi",
    "UI-DialogShader-yongzhuang-yemaopengzi",
]
print("=== los 15, desde el extracto GLOBAL ===")
sin_cara = []
for clave in SIN_CARA:
    try:
        r = bustups.montar(clave, carpeta=BASE)
    except Exception as e:
        print("   %-30s error: %s" % (clave, e))
        continue
    if not r:
        print("   %-30s no monta" % clave)
        continue
    capas = r.get("capas", [])
    pasos = sorted({c.get("paso") for c in capas})
    cara = bool({"face", "eyes", "mouth"} & set(pasos))
    print("   %-30s %-2d capas  cara:%-3s %s" % (clave, len(capas), "SI" if cara else "NO",
                                                  ",".join(p for p in pasos if p)))
    if not cara:
        sin_cara.append(clave)
print()
print("sin cara con el juego global: %d de %d" % (len(sin_cara), len(SIN_CARA)))
print(sin_cara)
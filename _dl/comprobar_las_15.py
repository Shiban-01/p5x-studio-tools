"""Comprueba si los 15 bust-ups que salian sin cara ya la tienen tras ampliar el extracto."""
import sys
from pathlib import Path

APP = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
sys.path.insert(0, str(APP))
from p5x_studio import bustups  # noqa: E402

SIN_CARA = ["guaidao01-bainiao", "guaidao01-longchuanxueshi", "guaidao01-qinyinmianju",
            "guaidao01-qinyinsp", "guaidao01-qinyintoufa", "guaidao01-tengchuanxueshi",
            "guaidao01-xisenyangcai-face", "guaidao01-yemaopengzi01", "guaidao01-yemaopengzi02",
            "guaidaofu-chibo", "guaidaofu01-qinyin", "guaidaofu02-chibo",
            "sifu01-lizi", "yongzhuang-lizi", "yongzhuang-yemaopengzi"]

carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(bustups.carpeta_texturas())
print("texturas en: %s" % carpeta)
print("indice: %d nombres" % len(bustups.indice(carpeta, refrescar=True)))
print()
print("%-30s %-8s %-7s %s" % ("clave", "capas", "cara?", "partes"))
siguen = []
for corta in SIN_CARA:
    clave = "UI-DialogShader-" + corta
    r = bustups.montar(clave, None, carpeta, guardar=False)
    if not r.get("ok"):
        print("%-30s no monta: %s" % (corta, r.get("error")))
        siguen.append(corta)
        continue
    pasos = [c.get("paso") for c in (r.get("capas") or [])]
    hay_cara = any("cuerpo" in (p or "") or "face-" in (p or "") or "benti" in (p or "") for p in pasos)
    print("%-30s %-8d %-7s %s" % (corta, len(pasos), "si" if hay_cara else "NO", ",".join(pasos)[:70]))
    if not hay_cara:
        siguen.append(corta)
print()
print("sin cara ahora: %d de %d -> %s" % (len(siguen), len(SIN_CARA), siguen))
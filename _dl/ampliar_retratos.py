"""Amplia el extracto de retratos con los bundles que faltaban para las caras.

El indice del juego (`104/zeusBundleManifest.txt`, 16.845 bundles con 136.793 dependencias) dice que
los bust-ups necesitan texturas de 118 bundles, pero el extracto del visor solo miraba 80. De los 15
bust-ups que salian sin cara, 11 tienen sus texturas de cara en esos bundles que faltaban (bainiao,
yemaopengzi, qinyin*, chibo...), asi que se suman y se rehace el extracto.

Se apoya en `_dl/cara_fuera_del_visor.json`, que dejo el analisis del manifiesto.
"""
import json
import sys
from pathlib import Path

APP = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
sys.path.insert(0, str(APP))

from p5x_studio import ajustes, bustups, lote, motor  # noqa: E402

DATOS = APP / "p5x_studio" / "datos" / "retratos.json"


def main():
    actual = json.loads(DATOS.read_text(encoding="utf-8"))
    bundles = list(actual.get("bundles") or [])
    tenia = set(bundles)

    analisis = json.loads((DL / "cara_fuera_del_visor.json").read_text(encoding="utf-8"))
    faltan = set()
    for entrada in analisis:
        faltan |= set(entrada.get("bundles_cara_fuera_de_visor") or [])
    # tambien lo que el analisis del manifiesto marca como necesario y el extracto no tenia
    informe = json.loads((DL / "bustups_indice_informe.json").read_text(encoding="utf-8"))
    for nombre in (informe.get("resumen", {}).get("bundles_necesarios_fuera_de_retratos") or {}):
        faltan.add(nombre)

    nuevos = sorted(faltan - tenia)
    print("bundles en el extracto: %d" % len(bundles))
    print("bundles que faltaban  : %d" % len(nuevos))
    for n in nuevos:
        print("   +", n)
    if nuevos:
        todos = sorted(tenia | faltan)
        DATOS.write_text(json.dumps({"bundles": todos}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nextracto ampliado a %d bundles: %s" % (len(todos), DATOS))
    else:
        print("\nel fichero ya lista los 119 bundles: solo falta extraer")

    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(motor.carpeta_extraidas())
    print("carpeta de salida: %s" % base)

    def progreso(hechos, total, nombre=""):
        print("  %d/%d %s" % (hechos, total, nombre[:60]))

    n = lote.extraer_retratos(base, bustups.prefijos_retratos(),
                              reanudar=("reanudar" in sys.argv), progreso=progreso)
    print("\nPNG en el extracto: %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
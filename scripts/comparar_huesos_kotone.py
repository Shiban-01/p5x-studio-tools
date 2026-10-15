"""Compara la lista de huesos del rig nuevo con la del FBX que se entrego antes.

El FBX entregado esta en kotone_shiomi/Kotone_Shiomi_full.fbx. Si alli faltase un hueso que si
esta en el nuevo, sale en la columna de "perdidos". Si los dos tienen lo mismo, la perdida del
IK Ring fue en otro artefacto (el maniqui o el modelo de Source), no en este.
"""
import json
import struct
import sys
from pathlib import Path

VIEJO = Path(r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\Kotone_Shiomi_full.fbx")
NUEVO_TXT = Path(r"C:\Users\Lukas\p5x-datamining\_dl\kotone_rig_completo\huesos_completos.txt")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\kotone_rig_completo")


def huesos_del_fbx(ruta: Path) -> list[str]:
    """Saca los nombres de hueso de un FBX binario leyendo el bloque de objetos."""
    import re
    datos = ruta.read_bytes()
    # En un FBX binario los nombres van como texto plano en el bloque de propiedades.
    # Se buscan los que empiezan por los prefijos tipicos de este rig.
    texto = datos.decode("latin-1", errors="ignore")
    nombres = set(re.findall(r"(?:Bip01|exDummy:Jnt|Jnt|IK|ik)[A-Za-z0-9_ :]*", texto))
    return sorted(n.strip() for n in nombres if 2 < len(n.strip()) < 60)


def main() -> None:
    nuevos = [l.strip() for l in NUEVO_TXT.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("   huesos del rig nuevo: %d" % len(nuevos))

    if not VIEJO.is_file():
        print("   no encuentro el FBX entregado en %s" % VIEJO)
        return
    viejos = huesos_del_fbx(VIEJO)
    print("   nombres con pinta de hueso en el FBX entregado: %d" % len(viejos))

    nuevos_b = {n.lower() for n in nuevos}
    faltan = [v for v in viejos if v.lower() not in nuevos_b]
    print("   del viejo que NO estan en el nuevo: %d" % len(faltan))
    for f in faltan[:25]:
        print("      %s" % f)

    # lo que interesa: el IK
    print()
    print("   --- nodos con IK en cada uno ---")
    print("   nuevo: %s" % [n for n in nuevos if "ik" in n.lower()])
    print("   viejo: %s" % [v for v in viejos if "ik" in v.lower()])

    (SALIDA / "huesos_fbx_entregado.txt").write_text("\n".join(viejos), encoding="utf-8")


if __name__ == "__main__":
    main()
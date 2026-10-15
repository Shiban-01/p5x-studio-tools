#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
E / F3-bis — Localiza el chunk de escena de TARTARUS junto a la Puerta Prohibida.

El evento `TL_P3P_Event_side_prologue_04_04` ocurre en Tartarus (strings del bundle del timeline:
`Tartaros_FLD_ForbiddenDoor`, `FX_Tartaros_FLD_ForbiddenDoor_Pink_side_loop`), y su rig de cámara
vive en las coordenadas x≈279,7 / z≈284,3. El escenario que tenemos inyectado (Iwatodai) está en
153/211, así que los actores se ven sobre un decorado que no es el suyo.

Criterio (acordado en F3-bis): buscar por POSICIÓN, no por nombre — "Tartaros" aparece como
nombre de FX en muchas escenas y engaña. Se recorre `scn_*.bundle` (1598, 12,5 GB), se de-ofusca
y se leen las `Transform`; si alguna cae dentro del radio de (279,7 · 284,3) se reporta el bundle
con los nombres de sus GameObjects y la altura (y) para deducir el suelo real del nivel.

Es RESUMIBLE: lo ya escaneado queda en el JSON y en la siguiente pasada se salta.

Uso:
    python scripts/scan_tartarus.py                 # escanea todas
    python scripts/scan_tartarus.py --radio 60      # radio mayor
    python scripts/scan_tartarus.py --resumen       # solo lee el JSON y resume
"""
import argparse
import glob
import json
import os
import shutil
import sys
import traceback

RAIZ = r"C:\Users\Lukas\p5x-datamining"
BUNDLES = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows"
STAGE = os.path.join(RAIZ, "_dl", "scn_stage")
JSON = os.path.join(RAIZ, "_dl", "tartarus_scan.json")

OBJETIVO = (279.7, 284.3)          # coords del evento (x, z)

sys.path.insert(0, os.path.join(RAIZ, "scripts"))

ap = argparse.ArgumentParser()
ap.add_argument("--radio", type=float, default=40.0)
ap.add_argument("--resumen", action="store_true")
ap.add_argument("--max", type=int, default=0, help="limite de bundles por pasada (0 = todos)")
a = ap.parse_args()

estado = {"escaneados": [], "hallazgos": []}
if os.path.exists(JSON):
    try:
        estado = json.load(open(JSON, encoding="utf-8"))
    except Exception:
        pass


def carga(dst):
    import UnityPy
    UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
    return UnityPy.load(dst)


def main():
    if a.resumen:
        print(f"escaneados: {len(estado['escaneados'])}")
        print(f"hallazgos : {len(estado['hallazgos'])}")
        for h in estado["hallazgos"]:
            print(f"  {h['bundle']:34} n={h['n']:3} x={h['x']:7.1f} y={h['y']:7.1f} z={h['z']:7.1f}"
                  f"  {h['nombres']}")
        return

    from deobfuscate_bundles import fix

    os.makedirs(STAGE, exist_ok=True)
    fs = sorted(glob.glob(os.path.join(BUNDLES, "**", "scn_*.bundle"), recursive=True))
    hechos = set(estado["escaneados"])
    pend = [f for f in fs if os.path.basename(f) not in hechos]
    if a.max:
        pend = pend[:a.max]
    print(f"scn_* totales: {len(fs)}  ·  ya escaneados: {len(hechos)}  ·  esta pasada: {len(pend)}")

    for i, src in enumerate(pend, 1):
        nombre = os.path.basename(src)
        dst = os.path.join(STAGE, nombre)
        try:
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                fix(__import__("pathlib").Path(dst))
            env = carga(dst)
            hallados = []
            for o in env.objects:
                if o.type.name != "Transform":
                    continue
                try:
                    d = o.read()
                    p = d.m_LocalPosition
                except Exception:
                    continue
                if p is None:
                    continue
                dx, dz = float(p.x) - OBJETIVO[0], float(p.z) - OBJETIVO[1]
                if dx * dx + dz * dz <= a.radio * a.radio:
                    hallados.append((float(p.x), float(p.y), float(p.z)))
            if hallados:
                # nombres de los GameObjects con transform (primeros 6)
                nombres = []
                for o in env.objects:
                    if o.type.name == "GameObject":
                        try:
                            nombres.append(o.read().m_Name)
                        except Exception:
                            pass
                    if len(nombres) >= 6:
                        break
                xs = [h[0] for h in hallados]
                ys = [h[1] for h in hallados]
                zs = [h[2] for h in hallados]
                reg = {"bundle": nombre, "n": len(hallados),
                       "x": sum(xs) / len(xs), "y": sum(ys) / len(ys), "z": sum(zs) / len(zs),
                       "y_min": min(ys), "y_max": max(ys),
                       "nombres": [n for n in nombres if n][:6]}
                estado["hallazgos"].append(reg)
                print(f"  CANDIDATO [{i}/{len(pend)}] {nombre}  n={len(hallados)} "
                      f"y={reg['y']:.1f} ({reg['y_min']:.1f}..{reg['y_max']:.1f}) {reg['nombres'][:3]}")
            estado["escaneados"].append(nombre)
        except Exception as e:
            print(f"  error en {nombre}: {type(e).__name__}: {e}")
            estado["escaneados"].append(nombre)          # no reintentar indefinidamente
        finally:
            try:
                if os.path.exists(dst):
                    os.remove(dst)                       # el stage no crece sin limite
            except Exception:
                pass
        if i % 25 == 0:
            json.dump(estado, open(JSON, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"  ... {i}/{len(pend)} escaneados, {len(estado['hallazgos'])} candidatos")

    json.dump(estado, open(JSON, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"\n=== fin: escaneados {len(estado['escaneados'])}  ·  candidatos {len(estado['hallazgos'])} ===")
    for h in estado["hallazgos"][:20]:
        print(f"  {h['bundle']:34} n={h['n']:3} x={h['x']:7.1f} y={h['y']:7.1f} z={h['z']:7.1f}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
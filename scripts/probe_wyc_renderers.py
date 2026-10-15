"""F2.1 — Lee los renderers del bundle del escenario para recuperar lo que el export perdio:
nombre real de cada material y la asignacion de lightmap (m_LightmapIndex + m_LightmapTilingOffset).

Eso es lo que AssetRipper no escribio en la .unity exportada (34 materiales quedaron en el GUID
placeholder y la escena no tiene ni un m_LightmapIndex).
"""
import json
import os
from collections import Counter
from pathlib import Path

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
ROOT = Path(__file__).resolve().parent.parent
BUNDLES = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
STAGE = ROOT / "_dl/scene_wyc_stage"
NOMBRE = "scn_iwai_wyc718eb6dc.bundle"


def encontrar(nombre: str):
    for dirpath, _d, files in os.walk(BUNDLES):
        if nombre in files:
            return Path(dirpath) / nombre
    return None


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    destino = STAGE / NOMBRE
    if not destino.exists():
        origen = encontrar(NOMBRE)
        if not origen:
            print("no esta el bundle")
            return
        destino.write_bytes(origen.read_bytes())
        print(f"copiado {origen}")

    env = UnityPy.load(str(destino))
    # Resolver nombres de material: PPtr -> nombre
    nombres_por_pathid = {}
    for obj in env.objects:
        if obj.type.name in ("Material", "GameObject", "Mesh"):
            try:
                nombres_por_pathid[obj.path_id] = obj.read().m_Name
            except Exception:  # noqa: BLE001
                pass

    tipos = Counter(o.type.name for o in env.objects)
    print("tipos:", dict(tipos))

    renderers = [o for o in env.objects if o.type.name == "MeshRenderer"]
    print(f"MeshRenderer encontrados: {len(renderers)}")

    # PathIDs de materiales INTERNOS (los que si se exportaron)
    interno = {}
    for o in env.objects:
        if o.type.name == "Material":
            try:
                interno[o.path_id] = o.read().m_Name
            except Exception:  # noqa: BLE001
                pass
    print(f"materiales internos: {len(interno)} -> {sorted(set(interno.values()))[:8]}")

    vecinos = Counter()
    externos = 0
    salida = []
    renderers_todos = renderers[:400]
    for o in renderers_todos:
        r = o.read()
        for m in getattr(r, "m_Materials", []) or []:
            fid = getattr(m, "m_FileID", None)
            pid = getattr(m, "m_PathID", None)
            vecinos[(fid, interno.get(pid) is not None)] += 1
            if fid not in (0, None):
                externos += 1
        salida.append({
            "path_id": o.path_id,
            "mats": [[getattr(m, "m_FileID", None), getattr(m, "m_PathID", None),
                      interno.get(getattr(m, "m_PathID", None))] for m in (getattr(r, "m_Materials", []) or [])],
            "lm_index": getattr(r, "m_LightmapIndex", None),
            "lm_off": str(getattr(r, "m_LightmapTilingOffset", "")),
        })
    print("slots de material por (fileID, interno?):", dict(vecinos))
    print(f"referencias a materiales EXTERNOS (otro bundle): {externos}")

    # RenderSettings + fog: la atmosfera real de la noche
    for o in env.objects:
        if o.type.name == "RenderSettings":
            rs = o.read()
            campos = ("m_AmbientMode", "m_AmbientSkyColor", "m_AmbientEquatorColor",
                      "m_AmbientGroundColor", "m_AmbientIntensity", "m_Fog", "m_FogColor",
                      "m_FogMode", "m_FogDensity", "m_FogLinearStart", "m_FogLinearEnd",
                      "m_SkyboxMaterial", "m_DefaultReflectionMode", "m_DefaultReflectionResolution")
            print("=== RenderSettings de la escena ===")
            for c in campos:
                if hasattr(rs, c):
                    print(f"  {c} = {getattr(rs, c)}")

    # Dependencias del AssetBundle: donde viven los materiales externos
    for o in env.objects:
        if o.type.name == "AssetBundle":
            ab = o.read()
            deps = getattr(ab, "m_Dependencies", None)
            print("=== dependencias del bundle ===", deps)

    out = ROOT / "_dl/scene_wyc_renderers.json"
    out.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
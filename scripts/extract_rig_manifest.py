#!/usr/bin/env python3
"""Extrae el manifiesto de skinning MUActor de un rig prefab de P5X a JSON.

Parsea el YAML del prefab (los scripts MUActor* son stubs en Unity, pero el
YAML conserva los datos). Produce para cada parte: mesh, root bone, lista de
huesos y materiales (guids -> rutas), listo para que un script Editor arme
SkinnedMeshRenderers sobre el Actor prefab.

Uso: python extract_rig_manifest.py <prefab_rig> <dir_proyecto> <out.json>
"""
import sys, re, json
from pathlib import Path

def guid_index(proj: Path):
    idx = {}
    for meta in proj.rglob("*.meta"):
        try: t = meta.read_text(encoding="latin1")
        except OSError: continue
        g = re.search(r"guid: (\w{32})", t)
        if g: idx[g.group(1)] = str(meta.with_suffix("")).replace("\\", "/")
    return idx

def parse_blocks(text):
    """divide YAML de prefab en documentos --- !u!NNN &id"""
    docs = {}
    cur_id = None; buf = []
    for line in text.splitlines():
        m = re.match(r"^--- !u!(\d+) &(\d+)", line)
        if m:
            if cur_id: docs[cur_id] = "\n".join(buf)
            cur_id = m.group(2); cls = m.group(1); buf = [f"!u{cls}"]
        elif cur_id: buf.append(line)
    if cur_id: docs[cur_id] = "\n".join(buf)
    return docs

def yaml_list_field(block, name):
    m = re.search(rf"^  {name}:\s*\n((?:^    - .*\n?)+|^  \S)", block, re.M)
    if not m: return None
    items = re.findall(r"^\s+- (.+)$", m.group(1), re.M)
    return items

def yaml_ref_field(block, name):
    m = re.search(rf"^  {name}: \{{fileID: (-?\d+)(?:, guid: (\w+))?.*?\}}", block, re.M)
    if not m: return None
    return (m.group(1), m.group(2))

def main():
    prefab_path, proj_dir, out = sys.argv[1:4]
    text = Path(prefab_path).read_text(encoding="latin1")
    idx = guid_index(Path(proj_dir))
    docs = parse_blocks(text)
    parts = []
    for bid, block in docs.items():
        if "mHighMeshBoneNames" not in block: continue
        root = re.search(r"mHighRootBoneName: (\S*)", block)
        mesh = yaml_ref_field(block, "mMesh") or yaml_ref_field(block, "mLODMesh")
        lod  = yaml_ref_field(block, "mLODMesh")
        shad = yaml_ref_field(block, "mShadowMesh")
        bones = yaml_list_field(block, "mHighMeshBoneNames") or []
        mats = re.findall(r"- \{fileID: (-?\d+), guid: (\w{32})", (re.search(r"mHighMeshMaterials:\s*\n((?:\s+- .*\n)+)", block) or [None,""])[1] if re.search(r"mHighMeshMaterials:", block) else "")
        mesh_ref = mesh if mesh and mesh[1] else (lod if lod and lod[1] else shad)
        parts.append({
            "block": bid,
            "rootBone": root.group(1) if root and root.group(1) else bones[0] if bones else "",
            "bones": bones,
            "meshGuid": mesh_ref[1] if mesh_ref and mesh_ref[1] else None,
            "meshPath": idx.get(mesh_ref[1]) if mesh_ref and mesh_ref[1] else None,
            "matGuids": [g for _, g in mats],
        })
    # si mHighMeshMaterials venia vacio: MaterialData bloques? probar por nombre de mesh
    outj = {"rig": prefab_path.replace("\\","/"), "parts": parts}
    Path(out).write_text(json.dumps(outj, indent=1), encoding="utf-8")
    for p in parts:
        print(f"parte mesh={p['meshPath']} bones={len(p['bones'])} root={p['rootBone']} mats={len(p['matGuids'])}")
    print("->", out)

if __name__ == "__main__":
    main()

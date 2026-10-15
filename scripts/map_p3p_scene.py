"""Mapea la escena P3P: ActionGroup (actor) -> acciones -> nombres de clip.

- ActionGroup_*.asset: ActorIndex + lista de guids (savedActions)
- *.asset (PlayAnimationAction): AnimationParams -> AnimationName
El guid de cada asset vive en su .meta.
"""
import pathlib
import re

MB = pathlib.Path("unity_projects/kotone/ExportedProject/Assets/MonoBehaviour")

# guid -> nombre de asset (desde los .meta)
guid2file = {}
for meta in MB.glob("*.asset.meta"):
    t = meta.read_text(encoding="latin1")
    m = re.search(r"guid: (\w{32})", t)
    if m:
        guid2file[m.group(1)] = meta.name[:-5]
print(f"assets indexados: {len(guid2file)}")

# guid -> lista de clips que reproduce
guid2clips = {}
for f in MB.glob("*.asset"):
    t = f.read_text(encoding="latin1")
    if "AnimationParams:" not in t:
        continue
    clips = re.findall(r"AnimationName: (\S+)", t)
    if clips:
        guid2clips[f.name] = clips

# grupos
grupos = []
for f in MB.glob("ActionGroup_*.asset"):
    t = f.read_text(encoding="latin1")
    idx = re.search(r"ActorIndex: (\d+)", t)
    guids = re.findall(r"guid: (\w{32})", t)
    acciones = []
    for g in guids:
        nm = guid2file.get(g)
        if nm and nm in guid2clips:
            acciones.append((nm, guid2clips[nm]))
    grupos.append((int(idx.group(1)) if idx else -1, f.name, acciones))

print(f"\n=== {len(grupos)} actores en la escena TL_P3P_Event_side_prologue_04_04 ===")
for idx, nombre, acciones in sorted(grupos):
    print(f"\nActor {idx}  ({nombre.replace('.asset','')})")
    for nm, clips in acciones[:6]:
        print(f"   {nm.replace('.asset','')}: {clips[:6]}")

# quien es Kotone / wonder
print("\n=== reparto ===")
for idx, nombre, acciones in sorted(grupos):
    todos = [c for _, cs in acciones for c in cs]
    rigs = sorted({c.split("@")[0] for c in todos if "@" in c})
    print(f"  Actor {idx}: rigs={rigs}  ({len(todos)} clips)")
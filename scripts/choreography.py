"""Extrae la coreografia de un playable P5X: track (actor) -> [(clip, start, dur)].

Recorre m_Tracks y m_Children (sub-tracks en archivos separados) y resuelve
m_Asset a MUPlayableAnimationClip.AnimationName.

Uso: python choreography.py <dir_proyecto_assets> <tl_playable> [salida.json]
"""
import re, json, sys
from pathlib import Path

assets = Path(sys.argv[1])
playable = sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else "choreography.json"

DOCS = {}        # (path_str, fileID) -> body
GUID2PATH = {}   # guid -> Path
def index_docs():
    for f in list(assets.rglob("*.asset")) + list(assets.rglob("*.playable")):
        t = f.read_text(encoding="latin1")
        meta = f.with_suffix(f.suffix + ".meta")
        if meta.exists():
            m = re.search(r"guid: (\w{32})", meta.read_text(encoding="latin1"))
            if m: GUID2PATH[m.group(1)] = f
        for m in re.finditer(r"^--- !u!114 &(\d+)\n(MonoBehaviour:.*?)(?=^--- |\Z)", t, re.S | re.M):
            DOCS[(str(f), m.group(1))] = m.group(2)
index_docs()

def get_doc(path, fid):
    return DOCS.get((str(path), fid))

def anim_name(path, fid):
    body = get_doc(path, fid)
    if body is None: return None
    m = re.search(r"AnimationName: (\S+)", body)
    return m.group(1) if m else None

def walk(path, fid, depth, result, actor=None):
    body = get_doc(path, fid)
    if body is None: return
    nm = re.search(r"m_Name: (.*)", body)
    raw = (nm.group(1).strip() if nm else "")
    try: name = raw.encode("latin1").decode("utf-8")
    except Exception: name = raw or Path(path).stem
    actor = name if depth == 1 and name else actor   # los tracks raiz son los ACTORES
    clips = []
    for m in re.finditer(r"-\s*m_Version: 1\s*\n\s*m_Start: ([\d.E+-]+)\s*\n\s*m_ClipIn: ([\d.E+-]+)\s*\n\s*m_Asset: \{fileID: (-?\d+)(?:, guid: (\w{32}))?(?:, type: \w+)?\}", body):
        start = float(m.group(1)); cin = float(m.group(2))
        afid, aguid = m.group(3), m.group(4)
        a_path = GUID2PATH.get(aguid) if aguid else path
        anim = anim_name(a_path, afid) if a_path else None
        dm = re.search(r"m_Duration: ([\d.E+-]+)", body[m.end():m.end() + 500])
        if anim:  # solo tracks de animacion
            clips.append({"actor": actor, "clip": anim, "start": start, "clipIn": cin,
                          "dur": float(dm.group(1)) if dm else None})
    if clips:
        result.extend(clips)
    for key in ("m_Children", "m_Tracks"):
        ch = re.search(key + r":\s*\n((?:\s*- \{fileID.*\n?)+)", body)
        if not ch: continue
        for cm in re.finditer(r"\{fileID: (-?\d+)(?:, guid: (\w{32}))?(?:, type: \w+)?\}", ch.group(1)):
            c_fid, c_guid = cm.group(1), cm.group(2)
            c_path = GUID2PATH.get(c_guid, path)
            if c_path is None: continue
            walk(c_path, c_fid, depth + 1, result, actor)

pvp = assets / "MonoBehaviour" / (playable + ".playable")
t = pvp.read_text(encoding="latin1")
root_fid = None
for m in re.finditer(r"^--- !u!114 &(\d+)\n(MonoBehaviour:.*?)(?=^--- |\Z)", t, re.S | re.M):
    if "m_Tracks:" in m.group(2): root_fid = m.group(1); break
res = []
walk(pvp, root_fid, 0, res)
json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for r in res:
    print(f"{'  '*r['depth']}{r['track'][:30]:32s} clips={len(r['clips'])}")
    for c in r["clips"][:8]:
        print(f"{'  '*(r['depth']+1)}t={c['start']:6.2f} dur={c['dur']} {str(c['clip'])[:56]}")

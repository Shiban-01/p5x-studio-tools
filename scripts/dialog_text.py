"""Extrae textos de dialog de un playable (AdvancedDialogClip.template)."""
import re, sys
from pathlib import Path
assets = Path(sys.argv[1])
tl = sys.argv[2]

DOCS = {}; GUID2PATH = {}
for f in list(assets.rglob("*.asset")) + list(assets.rglob("*.playable")):
    t = f.read_text(encoding="latin1")
    meta = f.with_suffix(f.suffix + ".meta")
    if meta.exists():
        m = re.search(r"guid: (\w{32})", meta.read_text(encoding="latin1"))
        if m: GUID2PATH[m.group(1)] = f
    for m in re.finditer(r"^--- !u!114 &(\d+)\n(MonoBehaviour:.*?)(?=^--- |\Z)", t, re.S | re.M):
        DOCS[(str(f), m.group(1))] = m.group(2)

pv_t = (assets / "MonoBehaviour" / (tl + ".playable")).read_text(encoding="latin1")
docs_here = re.findall(r"^--- !u!114 &(\d+)\n(MonoBehaviour:.*?)(?=^--- |\Z)", pv_t, re.S | re.M)

def utf8(s):
    try: return s.encode("latin1").decode("utf-8")
    except Exception: return s

def find_dialogs(path_str, body):
    out = []
    if "m_Template" not in body and "speaker" not in body.lower() and "Content" not in body:
        pass
    # el template tiene campos: buscar claves comunes
    for key in ("m_DialogText","Content","content","text","m_Text","Dialog","m_Dialog","Speaker","speaker","m_Speaker","ActorName"):
        for m in re.finditer(rf"^\s*{key}:\s*(.+)$", body, re.M):
            v = m.group(1).strip()
            if v and v not in ("0","1",""):
                out.append((key, utf8(v)[:80]))
    return out

for fid, body in docs_here:
    for m in re.finditer(r"m_Asset: \{fileID: (-?\d+)(?:, guid: (\w{32}))?", body):
        p2 = GUID2PATH.get(m.group(2))
        b2 = DOCS.get((str(p2), m.group(1))) if p2 else DOCS.get((str(assets/"MonoBehaviour"/(tl+".playable")), m.group(1)))
        if b2:
            r = find_dialogs(p2, b2)
            if r: print("clip", m.group(1), "->", r)
# tambien los bloques AdvancedDialogClip dentro de cualquier archivo
for (p, fid), body in DOCS.items():
    if "AdvancedDialog" in body or "m_Template" in body:
        r = find_dialogs(p, body)
        if r: print(Path(p).name, "->", r[:6])

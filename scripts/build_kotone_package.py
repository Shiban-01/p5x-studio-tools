"""P5X — arma el paquete del modelo de Kotone Shiomi (PC079_01) para uso externo.

Entrada : _dl/kotone_dump/  (volcado desde Unity: malla, piel, huesos, expresiones, materiales)
          _dl/ast_part/     (texturas PNG originales del bundle de partes, via AssetStudio)
          _dl/ast_anim/     (FBX del esqueleto, via AssetStudio)
Salida  : kotone_shiomi/    (carpetas separadas: modelo, texturas, esqueleto, expresiones,
                             materiales, origen)

GLB = glTF 2.0 binario con piel (huesos + pesos + bind poses), expresiones (morph targets) y
materiales con las texturas embebidas. Conversion Unity (Y arriba, zurdo) -> glTF (Y arriba,
diestro): se niega la X en posiciones/normales y se invierte el orden de los triangulos.
Los OBJ se escriben ya en la misma orientacion que el GLB, para que no haya sorpresas.
"""
import hashlib
import json
import os
import shutil
import struct
import numpy as np

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
TEX = os.path.join(RAIZ, "_dl", "ast_part")
FBX_ESQ = os.path.join(RAIZ, "_dl", "ast_anim")
OUT = os.path.join(RAIZ, "kotone_shiomi")

NOMBRES = {
    "PC079_01_body_wholeexport_rig_PC079_01_body": ("cuerpo", "cuerpo_body", "Cuerpo completo"),
    "PC079_01_body_wholeexport_rig_PC079_01_qiang": ("armas", "arma_lanza", "Lanza"),
    "PC079_01_body_wholeexport_rig_PC079_01_qiangtao": ("armas", "arma_lanza_vaina", "Vaina de la lanza"),
    "PC079_01_body_wholeexport_rig_PC079_01_xiuzhang": ("cuerpo", "brazalete", "Brazalete"),
    "PC079_01_face_wholeexport_rig_bs_PC079_01_face": ("cara", "cara", "Cara (con las 20 expresiones)"),
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eye": ("cara", "ojo", "Ojo (3 expresiones)"),
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid": ("cara", "parpado", "Parpado (1 expresion)"),
    "PC079_01_hair_wholeexport_rig_PC079_01_hair": ("pelo", "pelo", "Pelo"),
    "PC079_01_gun_02_wholeexport_rig_wq_makpon_gun_02": ("armas", "arma_pistola", "Pistola"),
    # duplicados geometricos sin expresiones: se excluyen del paquete
    "PC079_01_face_wholeexport_rig_PC079_01_face": ("cara", "_dup_cara", ""),
    "PC079_01_face_wholeexport_rig_PC079_01_eye": ("cara", "_dup_ojo", ""),
    "PC079_01_face_wholeexport_rig_PC079_01_eyelid": ("cara", "_dup_parpado", ""),
}

# Materiales que AssetRipper no supo resolver (le quedo el "Standard" de relleno) y que hay que
# reponer: el parpado lo pinta el juego con la textura de la cara (comprobado: sus UV caen sobre
# la piel lisa del atlas de la cara), igual que la cara.
MATERIAL_DE = {
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid":
        "PC079_01_face_wholeexport_rig_bs_PC079_01_face",
}
# El material del cuerpo traia como _BumpMap la normal del LOD (lodlow); la del cuerpo real es
# PC079_01_body_nm.png. Se corrige el slot (solo afecta al sombreado, no al color).
ARREGLO_SLOTS = {"_BumpMap": {"PC079_01_body_lodlow_nm.png": "PC079_01_body_nm.png"}}

CATEGORIAS_TEX = [("PC079_01_body", "cuerpo"), ("PC079_01_face", "cara"), ("PC079_01_eye", "ojos"),
                  ("PC079_01_eyelid", "cara"), ("PC079_01_hair", "pelo"),
                  ("PC079_01_weapon", "armas"), ("PC079_01_qiang", "armas"), ("PC079_01_gun", "armas")]


def cat_tex(n):
    for p, c in CATEGORIAS_TEX:
        if n.startswith(p):
            return c
    return "otros"


def ruta_textura(nombre):
    """Localiza un PNG: primero en el export original de AssetStudio y, si ya no esta (p. ej.
    porque se limpio para liberar espacio), en las texturas ya copiadas dentro del paquete."""
    directo = os.path.join(TEX, nombre)
    if os.path.exists(directo):
        return directo
    raiz_tex = os.path.join(OUT, "02_texturas")
    for cat in os.listdir(raiz_tex) if os.path.isdir(raiz_tex) else []:
        candidato = os.path.join(raiz_tex, cat, nombre)
        if os.path.exists(candidato):
            return candidato
    return None


def cargar(parte, ext, dtype, shape=None):
    a = np.fromfile(os.path.join(DUMP, f"{parte}.{ext}"), dtype=dtype)
    return a.reshape(shape) if shape else a


def negx(a):
    """Unity -> glTF: espejo en X (paso de zurdo a diestro)."""
    b = a.copy()
    b[..., 0] = -b[..., 0]
    return b


def uv_gltf(parte):
    """Las UV del volcado vienen como las usa Unity: la V crece hacia ARRIBA (origen abajo).
    glTF (y los OBJ tal como los leen Blender/Maya) usan la V hacia ABAJO (origen arriba), igual
    que el PNG tal como esta en el bundle. Sin invertir la V, la textura cae espejada en vertical:
    los calcetines blancos salian negros y la cara salia lisa, sin rasgos."""
    uv = cargar(parte, "uv0.bin", "<f4", (-1, 2))
    uv[:, 1] = 1.0 - uv[:, 1]
    return uv


def orientar(a):
    """Espelo en X + rotacion -90 grados sobre X: deja el modelo Y-arriba y mirando a +Z, igual
    que la orientacion final del GLB (que lo consigue con el nodo raiz). Para los OBJ, que no
    tienen jerarquia, se hornea aqui."""
    b = negx(a)
    out = np.empty_like(b)
    out[..., 0] = b[..., 0]
    out[..., 1] = b[..., 2]
    out[..., 2] = -b[..., 1]
    return out


# ── escritor glTF/GLB ────────────────────────────────────────────────────────────────────────
class Gltf:
    def __init__(self):
        self.bin = bytearray()
        self.vistas = []
        self.acc = []
        self.j = {"asset": {"version": "2.0",
                            "generator": "p5x-datamining - Kotone Shiomi (PC079_01) "
                                         "Persona 5: The Phantom X"},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [],
                  "accessors": self.acc, "bufferViews": self.vistas, "buffers": []}

    def crudo(self, raw, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        off = len(self.bin)
        self.bin += raw
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(raw)}
        if target:
            v["target"] = target
        self.vistas.append(v)
        return len(self.vistas) - 1

    def acc_crear(self, arr, target=None, mm=False, tipo_forzado=None):
        ct = {np.dtype("uint16"): 5123, np.dtype("uint32"): 5125, np.dtype("float32"): 5126}[arr.dtype]
        tipo = tipo_forzado or {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4"}[
            1 if arr.ndim == 1 else arr.shape[1]]
        a = {"bufferView": self.crudo(arr.tobytes(), target), "componentType": ct,
             "count": len(arr), "type": tipo}
        if mm and arr.ndim == 2:
            a["min"] = [round(float(x), 6) for x in arr.min(axis=0)]
            a["max"] = [round(float(x), 6) for x in arr.max(axis=0)]
        self.acc.append(a)
        return len(self.acc) - 1

    def bytes_finales(self):
        self.j["buffers"] = [{"byteLength": len(self.bin)}]
        js = json.dumps(self.j, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        js += b" " * ((4 - len(js) % 4) % 4)
        b = bytes(self.bin) + b"\0" * ((4 - len(self.bin) % 4) % 4)
        total = 12 + 8 + len(js) + 8 + len(b)
        return (b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(js)) + b"JSON" + js
                + struct.pack("<I", len(b)) + b"BIN\0" + b)


def anadir_parte(g, parte, meta, mat_idx_por_parte):
    pos = negx(cargar(parte, "pos.bin", "<f4", (-1, 3)))
    nrm = negx(cargar(parte, "nrm.bin", "<f4", (-1, 3)))
    uv0 = uv_gltf(parte)
    bidx = cargar(parte, "bidx.bin", "<u2", (-1, 4))
    bwgt = cargar(parte, "bwgt.bin", "<f4", (-1, 4))
    ibm = cargar(parte, "ibm.bin", "<f4", (-1, 4, 4))

    huesos = meta["lista_huesos"]
    nb = len(huesos)
    base = len(g.j["nodes"])
    for h in huesos:
        n = {"name": h.get("nombre") or "hueso_vacio"}
        if h.get("nombre"):
            p, r, e = h["pos"], h["rot"], h["esc"]
            n["translation"] = [round(-p[0], 7), round(p[1], 7), round(p[2], 7)]
            n["rotation"] = [round(r[0], 7), round(-r[1], 7), round(-r[2], 7), round(r[3], 7)]
            n["scale"] = [round(e[0], 7), round(e[1], 7), round(e[2], 7)]
        g.j["nodes"].append(n)
    for i, h in enumerate(huesos):
        pa = h.get("padre", -1)
        if pa is not None and 0 <= pa < nb:
            g.j["nodes"][base + pa].setdefault("children", []).append(base + i)
    raices = [base + i for i, h in enumerate(huesos)
              if h.get("padre") is None or not (0 <= h["padre"] < nb)]

    # bind poses: fila-mayor -> columna-mayor + conjugacion con el espejo (M' = B M B)
    m = ibm.copy()
    m[:, 0, :] *= -1.0
    m[:, :, 0] *= -1.0
    acc_ibm = g.acc_crear(np.transpose(m, (0, 2, 1)).reshape(-1, 16).astype("<f4"),
                          tipo_forzado="MAT4")

    # los atributos se comparten entre submallas (si no, cada primitiva duplicaria la vertices)
    atrib = {"POSITION": g.acc_crear(pos.astype("<f4"), 34962, mm=True),
             "NORMAL": g.acc_crear(nrm.astype("<f4"), 34962),
             "TEXCOORD_0": g.acc_crear(uv0.astype("<f4"), 34962),
             "JOINTS_0": g.acc_crear(bidx, 34962),
             "WEIGHTS_0": g.acc_crear(bwgt.astype("<f4"), 34962)}

    prims = []
    for i in range(meta["submallas"]):
        tri = cargar(parte, f"tris{i}.bin", "<u4").reshape(-1, 3).reshape(-1)
        pr = {"attributes": dict(atrib),
              "indices": g.acc_crear(tri.astype("<u4"), 34963)}
        mi = mat_idx_por_parte.get((parte, i))
        if mi is not None:
            pr["material"] = mi
        objetivos, nombres = [], []
        for exp in meta["lista_expresiones"]:
            for fr in exp["frames"]:
                dv = negx(np.fromfile(os.path.join(DUMP, fr["bin"]), dtype="<f4").reshape(-1, 3))
                objetivos.append(g.acc_crear(dv.astype("<f4")))
                nombres.append(exp["nombre"])
        if objetivos:
            pr["targets"] = [{"POSITION": a} for a in objetivos]
        prims.append(pr)

    malla = {"name": meta["parte"], "primitives": prims}
    if nombres:
        malla["extras"] = {"targetNames": nombres}
        malla["weights"] = [0.0] * len(nombres)
    g.j.setdefault("meshes", []).append(malla)

    skin = {"joints": list(range(base, base + nb)), "inverseBindMatrices": acc_ibm}
    if raices:
        skin["skeleton"] = raices[0]
    g.j.setdefault("skins", []).append(skin)

    g.j["nodes"].append({"name": meta["parte"] + "_MALLA",
                         "mesh": len(g.j["meshes"]) - 1,
                         "skin": len(g.j["skins"]) - 1})
    return len(g.j["nodes"]) - 1, raices


def construir_glb(lista, metas, destino):
    g = Gltf()
    mat_por_nombre, mat_idx = {}, {}
    # solo se traen los materiales de otra pieza si alguna de "lista" los necesita
    extras = [MATERIAL_DE[p] for p in lista if p in MATERIAL_DE and MATERIAL_DE[p] in metas]
    piezas_material = list(lista) + [q for q in extras if q not in lista]
    for p in piezas_material:
        for i, mat in enumerate(metas[p]["materiales"]):
            nom = mat.get("nombre") or f"material_{i}"
            if nom not in mat_por_nombre:
                slots = {t["slot"]: t["textura"] for t in mat.get("texturas", [])}
                for slot, cambios in ARREGLO_SLOTS.items():
                    if slot in slots and slots[slot] in cambios:
                        slots[slot] = cambios[slots[slot]]
                mat_por_nombre[nom] = len(g.j.setdefault("materials", []))
                g.j["materials"].append({
                    "name": nom, "doubleSided": False,
                    "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1],
                                             "metallicFactor": 0.0, "roughnessFactor": 1.0},
                    "extras": {"slots_p5x": slots}})
            mat_idx[(p, i)] = mat_por_nombre[nom]

    hijos_raiz = []
    # piezas cuyo material se perdio en el export: se les pone el de su pieza de referencia
    for p in lista:
        if p in MATERIAL_DE:
            ref = mat_idx.get((MATERIAL_DE[p], 0))
            if ref is not None:
                for i in range(metas[p]["submallas"]):
                    mat_idx[(p, i)] = ref
    for p in lista:
        idx, raices = anadir_parte(g, p, metas[p], mat_idx)
        hijos_raiz.append(idx)
        hijos_raiz.extend(raices)
    # El modelo viene Z-arriba y mirando a -Y (asi esta en el juego). Esta rotacion (-90 grados
    # sobre X) lo deja en la convencion de glTF: Y arriba y mirando a +Z. Va como nodo raiz para
    # no tocar vertices, huesos ni bind poses: una rotacion global es rotar el resultado de la piel.
    g.j["nodes"].append({"name": "Kotone_Shiomi_raiz",
                         "rotation": [-0.70710678, 0.0, 0.0, 0.70710678],
                         "children": hijos_raiz})
    g.j["scenes"][0]["nodes"].append(len(g.j["nodes"]) - 1)

    # imagenes + texturas: se crean al final y se enganchan a los materiales
    usados = {}
    for mat in g.j["materials"]:
        for png in mat["extras"]["slots_p5x"].values():
            usados.setdefault(png, None)
    for png in sorted(usados):
        ruta = ruta_textura(png)
        if not ruta:
            continue
        with open(ruta, "rb") as fh:
            bv = g.crudo(fh.read())
        g.j.setdefault("images", []).append({"name": png, "bufferView": bv, "mimeType": "image/png"})
        g.j.setdefault("textures", []).append({"sampler": 0, "source": len(g.j["images"]) - 1})
        usados[png] = len(g.j["textures"]) - 1
    g.j.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987,
                                 "wrapS": 10497, "wrapT": 10497}])
    for mat in g.j["materials"]:
        s = mat["extras"]["slots_p5x"]
        b = s.get("_MainTex") or s.get("_BaseMap")
        if b in usados and usados[b] is not None:
            mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": usados[b]}
        n = s.get("_BumpMap") or s.get("_NormalMap")
        if n in usados and usados[n] is not None:
            mat["normalTexture"] = {"index": usados[n]}

    datos = g.bytes_finales()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as fh:
        fh.write(datos)
    return len(datos), len(g.j.get("images", []))


# ── OBJ ──────────────────────────────────────────────────────────────────────────────────────
def escribir_obj(destino, pos, nrm, uv, tris, grupo, material):
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Kotone Shiomi (PC079_01) - Persona 5: The Phantom X\n")
        f.write(f"# parte: {grupo}\n")
        f.write(f"# orientacion: Y arriba, diestro (igual que el GLB)\n")
        f.write(f"mtllib {os.path.basename(destino)[:-4]}.mtl\n")
        f.write(f"o {grupo}\n")
        for v in pos:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for v in uv:
            f.write(f"vt {v[0]:.6f} {v[1]:.6f}\n")
        for v in nrm:
            f.write(f"vn {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        f.write(f"usemtl {material}\n")
        for t in tris:
            a, b, c = int(t[0]) + 1, int(t[1]) + 1, int(t[2]) + 1
            f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")


def escribir_mtl(destino, nombre_mat, slots):
    base = slots.get("_MainTex") or slots.get("_BaseMap")
    nrm = slots.get("_BumpMap") or slots.get("_NormalMap")
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Kotone Shiomi (PC079_01) - materiales del juego (slots del shader P5X/Toon)\n")
        f.write(f"newmtl {nombre_mat}\n")
        f.write("Kd 1.000 1.000 1.000\nKa 0.000 0.000 0.000\nKs 0.000 0.000 0.000\nNs 10.0\nd 1.0\nillum 2\n")
        # el MTL vive en 01_modelo/obj/<categoria>/, las texturas en 02_texturas/<categoria>/
        if base:
            f.write(f"map_Kd ../../../02_texturas/{cat_tex(base)}/{base}\n")
        if nrm:
            f.write(f"map_Bump ../../../02_texturas/{cat_tex(nrm)}/{nrm}\n")
        for slot, png in slots.items():
            if slot in ("_MainTex", "_BaseMap", "_BumpMap", "_NormalMap"):
                continue
            f.write(f"# {slot} = {png}\n")


def main():
    partes = sorted(f[:-5] for f in os.listdir(DUMP) if f.endswith(".json") and f != "resumen.json")
    metas = {p: json.load(open(os.path.join(DUMP, p + ".json"), encoding="utf-8")) for p in partes}
    print(f"partes en el volcado: {len(partes)}")

    for d in ["01_modelo/glb", "01_modelo/obj", "02_texturas", "03_esqueleto",
              "04_expresiones", "05_materiales", "06_origen"]:
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    # ── 1. texturas ─────────────────────────────────────────────────────────────────────────
    if os.path.isdir(TEX):
        pngs = sorted(f for f in os.listdir(TEX) if f.lower().endswith(".png"))
        for f in pngs:
            dst = os.path.join(OUT, "02_texturas", cat_tex(f))
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(os.path.join(TEX, f), os.path.join(dst, f))
    else:
        # el export original ya no esta: se usan las texturas del propio paquete
        pngs = []
        for raiz, _d, fs in os.walk(os.path.join(OUT, "02_texturas")):
            pngs += [f for f in fs if f.lower().endswith(".png")]
        print(f"   (aviso: {TEX} no existe; se usan las {len(pngs)} texturas ya copiadas)")
    print(f"1. texturas: {len(pngs)} PNG -> {sorted(set(cat_tex(f) for f in pngs))}")

    # ── 2. GLB ──────────────────────────────────────────────────────────────────────────────
    principales = [p for p in partes if not NOMBRES.get(p, ("", "", ""))[1].startswith("_dup")]
    for p in principales:
        _, corto, _ = NOMBRES.get(p, ("modelo", p, p))
        n, nimg = construir_glb([p], metas, os.path.join(OUT, "01_modelo", "glb", corto + ".glb"))
        print(f"2. GLB {corto + '.glb':34s} {n/1024:7.0f} KB  ({nimg} texturas)")
    # el GLB "completo" lleva solo el personaje: las armas van sueltas porque en el juego se
    # enganchan por codigo a un hueso de la mano (el dato no viene en los bundles) y si no,
    # aparecen en el origen, entre los pies
    cuerpo_entero = [p for p in principales if NOMBRES.get(p, ("modelo", p, p))[0] != "armas"]
    n, nimg = construir_glb(cuerpo_entero, metas,
                            os.path.join(OUT, "01_modelo", "glb", "Kotone_Shiomi_completo.glb"))
    print(f"   GLB {'Kotone_Shiomi_completo.glb':34s} {n/1024:7.0f} KB  ({nimg} texturas)")

    # ── 3. OBJ + MTL ────────────────────────────────────────────────────────────────────────
    for p in principales:
        cat, corto, _ = NOMBRES.get(p, ("modelo", p, p))
        meta = metas[p]
        dst_dir = os.path.join(OUT, "01_modelo", "obj", cat)
        os.makedirs(dst_dir, exist_ok=True)
        pos = orientar(cargar(p, "pos.bin", "<f4", (-1, 3)))
        nrm = orientar(cargar(p, "nrm.bin", "<f4", (-1, 3)))
        uv = uv_gltf(p)
        # si el material se perdio en el export, se usa el de la pieza de referencia
        mats_pieza = meta["materiales"]
        if p in MATERIAL_DE and MATERIAL_DE[p] in metas:
            mats_pieza = metas[MATERIAL_DE[p]]["materiales"]
        for i in range(meta["submallas"]):
            tri = cargar(p, f"tris{i}.bin", "<u4").reshape(-1, 3)
            j = i if i < len(mats_pieza) else 0
            nom_mat = (mats_pieza[j].get("nombre") if mats_pieza else None) or corto
            suf = "" if meta["submallas"] == 1 else f"_mat{i}"
            escribir_obj(os.path.join(dst_dir, corto + suf + ".obj"), pos, nrm, uv, tri,
                         corto + suf, nom_mat)
            slots = {t["slot"]: t["textura"] for t in mats_pieza[j].get("texturas", [])} if mats_pieza else {}
            for slot, cambios in ARREGLO_SLOTS.items():
                if slot in slots and slots[slot] in cambios:
                    slots[slot] = cambios[slots[slot]]
            escribir_mtl(os.path.join(dst_dir, corto + suf + ".mtl"), nom_mat, slots)
    print(f"3. OBJ: escritos en 01_modelo/obj/<categoria>/")

    # ── 4. esqueleto ────────────────────────────────────────────────────────────────────────
    cuerpo = next(p for p in principales if p.endswith("_body"))
    huesos = metas[cuerpo]["lista_huesos"]
    with open(os.path.join(OUT, "03_esqueleto", "huesos.json"), "w", encoding="utf-8") as f:
        json.dump({"modelo": "Kotone Shiomi (PC079_01)",
                   "esqueleto": "Bip01 (3ds Max Biped)",
                   "total_huesos": len(huesos),
                   "nota": "pos/rot/esc son LOCALES respecto al hueso padre; rot en cuaternion (x,y,z,w)",
                   "huesos": huesos}, f, ensure_ascii=False, indent=1)
    for p in principales:
        with open(os.path.join(OUT, "03_esqueleto", f"huesos_{NOMBRES.get(p,('','  '+'p',''))[1]}.txt"),
                  "w", encoding="utf-8") as f:
            f.write(f"# huesos que usa la pieza {p} ({metas[p]['huesos']} huesos)\n")
            for h in metas[p]["lista_huesos"]:
                f.write((h.get("nombre") or "(vacio)") + "\n")
    hijos = {}
    for i, h in enumerate(huesos):
        hijos.setdefault(h.get("padre", -1), []).append(i)
    lineas = []
    def rec(i, prof):
        h = huesos[i]
        lineas.append("  " * prof + (h.get("nombre") or "(vacio)"))
        for c in hijos.get(i, []):
            rec(c, prof + 1)
    for r in hijos.get(-1, []) + [i for i in hijos.get(None, [])]:
        rec(r, 0)
    with open(os.path.join(OUT, "03_esqueleto", "esqueleto_arbol.txt"), "w", encoding="utf-8") as f:
        f.write(f"Arbol del esqueleto de Kotone Shiomi (PC079_01) - {len(huesos)} huesos\n")
        f.write("Esqueleto Bip01 (3ds Max Biped), como en el juego.\n\n")
        f.write("\n".join(lineas) + "\n")
    ibm = cargar(cuerpo, "ibm.bin", "<f4", (-1, 4, 4))
    with open(os.path.join(OUT, "03_esqueleto", "bindposes.bin"), "wb") as f:
        f.write(np.transpose(ibm, (0, 2, 1)).astype("<f4").tobytes())
    for src, dst in [(os.path.join(FBX_ESQ, "FBX_Animator", "PC079_01", "PC079_01.fbx"),
                      os.path.join(OUT, "03_esqueleto", "esqueleto_PC079_01.fbx"))]:
        if os.path.exists(src):
            shutil.copy2(src, dst)
    print(f"4. esqueleto: huesos.json, esqueleto_arbol.txt, bindposes.bin, FBX ({len(huesos)} huesos)")

    # ── 5. expresiones ───────────────────────────────────────────────────────────────────────
    resumen_exp = {"modelo": "Kotone Shiomi (PC079_01)", "piezas": []}
    carpeta_exp = os.path.join(OUT, "04_expresiones", "obj")
    os.makedirs(carpeta_exp, exist_ok=True)
    total = 0
    for p in principales:
        meta = metas[p]
        if not meta["lista_expresiones"]:
            continue
        _, corto, _ = NOMBRES.get(p, ("modelo", p, p))
        pos = orientar(cargar(p, "pos.bin", "<f4", (-1, 3)))
        nrm = orientar(cargar(p, "nrm.bin", "<f4", (-1, 3)))
        uv = uv_gltf(p)
        tri = cargar(p, "tris0.bin", "<u4").reshape(-1, 3)
        detalle = []
        for exp in meta["lista_expresiones"]:
            fr = exp["frames"][0]
            dv = orientar(np.fromfile(os.path.join(DUMP, fr["bin"]), dtype="<f4").reshape(-1, 3))
            movidos = int((np.abs(dv).sum(axis=1) > 1e-7).sum())
            dmax = float(np.abs(dv).max())
            nom = f"{corto}_{exp['nombre']}"
            escribir_obj(os.path.join(carpeta_exp, nom + ".obj"),
                         (pos + dv).astype(np.float32), nrm, uv, tri, nom, "cara")
            detalle.append({"nombre": exp["nombre"], "peso_frame": fr["peso"],
                            "vertices_movidos": movidos, "desplazamiento_max": round(dmax, 5),
                            "obj": f"obj/{nom}.obj"})
            total += 1
        resumen_exp["piezas"].append({"pieza": corto, "malla_de_origen": p,
                                      "expresiones": detalle})
    with open(os.path.join(OUT, "04_expresiones", "expresiones.json"), "w", encoding="utf-8") as f:
        json.dump(resumen_exp, f, ensure_ascii=False, indent=1)
    print(f"5. expresiones: {total} OBJ (uno por expresion) + expresiones.json")

    # ── 6. materiales ────────────────────────────────────────────────────────────────────────
    mats = {}
    for p in principales:
        for i, m in enumerate(metas[p]["materiales"]):
            nom = m.get("nombre") or f"{p}_{i}"
            mats[nom] = {"shader_origen": m.get("shader"),
                         "usado_por": mats.get(nom, {}).get("usado_por", []) + [p],
                         "texturas": {t["slot"]: t["textura"] for t in m.get("texturas", [])}}
    with open(os.path.join(OUT, "05_materiales", "materiales.json"), "w", encoding="utf-8") as f:
        json.dump({"modelo": "Kotone Shiomi (PC079_01)",
                   "shader_origen": "P5X/Toon (propietario del juego; aqui solo los slots de textura)",
                   "materiales": mats}, f, ensure_ascii=False, indent=1)
    SLOTS = [("_MainTex", "color base (difuso)"), ("_BaseMap", "color base (alias URP)"),
             ("_BumpMap", "mapa de normales"), ("_MetallicGlossMap", "metalico/brillo"),
             ("_ToonDarkMap", "color de sombra del toon"), ("_ShadePosition", "mascara de posicion de sombra"),
             ("_FaceShadowTex", "SDF de sombra de cara"), ("_OutlineTex", "textura del contorno"),
             ("_MatcapMask", "mascara de matcap")]
    with open(os.path.join(OUT, "05_materiales", "tabla_texturas.md"), "w", encoding="utf-8") as f:
        f.write("# Que textura es que\n\nEl juego usa un shader propio (`P5X/Toon`). Estas son las ranuras\n"
                "que trae, con su significado:\n\n| Ranura | Que es |\n|---|---|\n")
        for s, d in SLOTS:
            f.write(f"| `{s}` | {d} |\n")
        f.write("\n## Materiales del modelo\n\n| Material | Ranura | Textura |\n|---|---|---|\n")
        for nom, m in sorted(mats.items()):
            for s, t in sorted(m["texturas"].items()):
                f.write(f"| `{nom}` | `{s}` | `{t}` |\n")
    print(f"6. materiales: {len(mats)} materiales -> materiales.json + tabla_texturas.md")

    # ── 7. origen (procedencia y hashes) ─────────────────────────────────────────────────────
    clientes = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows"
    fuentes = [os.path.join(clientes, "145", "part_pc079_011ef29087.bundle"),
               os.path.join(clientes, "156", "role_pc079_0113713867.bundle")]
    origen = {"juego": "Persona 5: The Phantom X (cliente PC)",
              "personaje": "Kotone Shiomi (PC079_01)",
              "bundle_del_modelo": "part_pc079_011ef29087.bundle",
              "bundle_del_actor": "role_pc079_0113713867.bundle",
              "extraido_con": "AssetStudioModCLI (mallas OBJ + texturas PNG) y Unity 2022.3.49f1 "
                              "(piel, huesos, expresiones y GLB)",
              "fecha": "2026-09-27",
              "archivos_fuente": []}
    for f_ in fuentes:
        if os.path.exists(f_):
            h = hashlib.sha256()
            with open(f_, "rb") as fh:
                for blk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(blk)
            origen["archivos_fuente"].append({"nombre": os.path.basename(f_),
                                              "bytes": os.path.getsize(f_),
                                              "sha256": h.hexdigest()})
    with open(os.path.join(OUT, "06_origen", "procedencia.json"), "w", encoding="utf-8") as f:
        json.dump(origen, f, ensure_ascii=False, indent=1)
    print("7. origen: procedencia.json")

    # ── 8. resumen ───────────────────────────────────────────────────────────────────────────
    tot_v = sum(metas[p]["vertices"] for p in principales)
    tot_t = sum(sum(metas[p]["triangulos_por_submalla"]) for p in principales)
    tot_e = sum(metas[p]["expresiones"] for p in principales)
    with open(os.path.join(OUT, "RESUMEN.json"), "w", encoding="utf-8") as f:
        json.dump({"modelo": "Kotone Shiomi (PC079_01)",
                   "piezas": [{"nombre": NOMBRES.get(p, ("", p, ""))[1], "origen": p,
                               "vertices": metas[p]["vertices"],
                               "triangulos": sum(metas[p]["triangulos_por_submalla"]),
                               "materiales": metas[p]["submallas"],
                               "huesos": metas[p]["huesos"],
                               "expresiones": metas[p]["expresiones"]} for p in principales],
                   "totales": {"piezas": len(principales), "vertices": tot_v,
                               "triangulos": tot_t, "expresiones": tot_e,
                               "texturas": len(pngs)}}, f, ensure_ascii=False, indent=1)
    print(f"\nTOTALES: {len(principales)} piezas, {tot_v} vertices, {tot_t} triangulos, "
          f"{tot_e} expresiones, {len(pngs)} texturas")


if __name__ == "__main__":
    main()

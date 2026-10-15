"""Esqueleto y pesos SIN Unity: reconstruye el volcado que consume `glb_rig` leyendo los bundles.

Por que existe: la ruta de Unity (`unity.py` + `P5XSkeletonExport.cs`) solo funciona si el
personaje esta dentro del proyecto decompilado, y el proyecto solo trae los personajes que se
exportaron a mano. Con esto, cualquier personaje sale riggeado directamente de los bundles del
juego, que es donde viven de verdad los datos:

  * la malla trae la PIEL (pesos y indices de hueso en los canales 12 y 13 de m_VertexData) y las
    INVERSAS DE BIND en `m_BindPose` (una por hueso, en el orden de la lista del manifiesto);
  * el prefab del actor (bundle `role_*`) trae la JERARQUIA de huesos (GameObject + Transform);
  * el manifiesto del rig (MonoBehaviour `MUActorMeshExportInfo`) trae, por malla, la lista
    ORDENADA de nombres de hueso (`mHighMeshBoneNames`), que es lo que casa cada indice de hueso
    de la piel con un transform concreto.

Este modulo escribe exactamente el mismo volcado que el capturador de Unity (`esqueleto.json`,
`<parte>.json`, `<parte>.pos.bin`...) para no duplicar el ensamblador: `glb_rig` lo consume igual.

Ojo con el manifiesto: es un MonoBehaviour cuyo script es un stub de AssetRipper, asi que UnityPy
no lo sabe deserializar y se lee a mano. El formato es el de Unity: cabecera de MonoBehaviour
(12 + 4 + 12 bytes), `m_Name`, y luego los campos. La lista de huesos viene precedida de su
recuento; como los campos anteriores varian, la lista se localiza buscando la estructura
"entero n seguido de n cadenas validas de 4 en 4 bytes" y se comprueba que n coincide con el numero
de inversas de bind de la malla.
"""
from __future__ import annotations

import io
import json
import os
import re
import struct
from pathlib import Path

import UnityPy

from .idiomas import t

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"

# VertexAttributeFormat de Unity -> (letra de struct, tamano en bytes)
FMT = {0: ("f", 4), 1: ("e", 2), 2: ("B", 1), 3: ("b", 1), 4: ("H", 2), 5: ("h", 2),
       6: ("B", 1), 7: ("b", 1), 8: ("H", 2), 9: ("h", 2), 10: ("I", 4), 11: ("i", 4)}

# canales de m_VertexData (orden canonico de Unity)
CH_POS, CH_NRM, CH_TAN, CH_COL = 0, 1, 2, 3
CH_UV0, CH_UV1, CH_UV2, CH_UV3 = 4, 5, 6, 7
CH_WGT, CH_IDX = 12, 13

DESCARTABLES = ("_lod", "_lodlow", "_lodhigh", "_shadow")


# --------------------------------------------------------------------------- lectura de bundles

def _offset_desofuscado(nombre: str) -> int:
    """Los bundles de OuterPackage llevan un prefijo de hash; hay que saltarlo para abrirlos."""
    n = 0
    for c in nombre:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return (n & 0x7FFFFFFF) % 32 + 8


def _abrir(ruta: Path):
    datos = Path(ruta).read_bytes()
    off = _offset_desofuscado(Path(ruta).name)
    return UnityPy.load(io.BytesIO(datos[off:]))


def _rigs_del_catalogo(actor: str) -> list:
    """Rutas completas de los bundles `role_*` que son el rig del actor (segun el indice de assets).

    Respaldo para cuando el catalogo no los engancho: el juego no siempre llama `role_<actor>` al
    prefab (`closer` -> `role__uniform5f23c883.bundle`), asi que se pregunta por el nombre del
    prefab. Importa perezosamente para no crear un ciclo con `catalogo`.
    """
    try:
        from . import ajustes, catalogo
    except Exception:
        return []
    carpeta = ajustes.carpeta_bundles()
    if not carpeta:
        return []
    return [carpeta / f for f in catalogo.rigs_de(actor) if (carpeta / f).is_file()]


# --------------------------------------------------------------------------- manifiesto del rig

def _buscar_lista_huesos(raw: bytes, n_esperado: int | None = None, idx_max: int | None = None):
    """Localiza la lista ordenada de huesos dentro de los bytes de un MonoBehaviour.

    Devuelve (nombres, offset) o None. Se busca un entero `n` seguido de `n` cadenas validas; si se
    conoce el numero de inversas de bind de la malla, se exige que coincida, y si se conoce el mayor
    indice de hueso usado por la piel, se exige que la lista lo cubra. Asi no se confunde con otras
    listas del mismo componente.
    """
    mejor = None
    limite = min(len(raw), 4096)
    for off in range(28, limite, 4):
        nn = struct.unpack_from("<i", raw, off)[0]
        if not (1 <= nn <= 4096):
            continue
        if n_esperado is not None and nn != n_esperado:
            continue
        if idx_max is not None and nn <= idx_max:
            continue
        p = off + 4
        strs = []
        ok = True
        for _ in range(nn):
            if p + 4 > len(raw):
                ok = False
                break
            ln = struct.unpack_from("<i", raw, p)[0]
            p += 4
            if not (0 < ln <= 200) or p + ln > len(raw):
                ok = False
                break
            trozo = raw[p:p + ln]
            p += ln
            while p % 4:
                p += 1
            try:
                texto = trozo.decode("utf-8")
            except Exception:
                ok = False
                break
            if any(ord(c) < 9 or ord(c) > 126 for c in texto):
                ok = False
                break
            strs.append(texto)
        if ok and len(strs) == nn:
            if mejor is None or nn > mejor[0]:
                mejor = (nn, strs, off)
    if not mejor:
        return None
    return mejor[1], mejor[2]


# --------------------------------------------------------------------------- datos de la malla

def _strides(vd) -> dict:
    out = {}
    for c in vd.m_Channels:
        if not c.dimension:
            continue
        _, tam = FMT[c.format]
        out[c.stream] = max(out.get(c.stream, 0), c.offset + c.dimension * tam)
    return out


def _cuatro(fila):
    """Normaliza a 4 influencias: hay mallas (los ojos) que solo guardan 2 por vertice."""
    if fila is None:
        return [0.0, 0.0, 0.0, 0.0]
    v = [float(x) for x in fila]
    return (v + [0.0, 0.0, 0.0, 0.0])[:4]


class _Malla:
    """Vista de una Mesh con lo que hace falta para el volcado."""

    def __init__(self, obj):
        m = obj.read()
        self.m = m
        self.nombre = m.m_Name
        self.vertices = int(m.m_VertexData.m_VertexCount)
        self.submallas = len(m.m_SubMeshes)
        self.bindpose = [list(x) for x in _matrices(m.m_BindPose)]
        vd = m.m_VertexData
        self._datos = vd.m_DataSize
        self._strides = _strides(vd)
        self._ch = {i: c for i, c in enumerate(vd.m_Channels) if c.dimension}
        self._base = {}
        pos = 0
        for s in sorted(self._strides):
            self._base[s] = pos
            pos += self.vertices * self._strides[s]
            pos = (pos + 15) & ~15   # Unity alinea el inicio de cada stream a 16 bytes

    def tiene(self, canal) -> bool:
        return canal in self._ch

    def _leer(self, canal, n):
        c = self._ch.get(canal)
        if c is None:
            return [None] * n
        letra, _ = FMT[c.format]
        dim = c.dimension
        stride = self._strides[c.stream]
        base = self._base[c.stream] + c.offset
        fmt = "<%d%s" % (dim, letra)
        datos = self._datos
        return [struct.unpack_from(fmt, datos, base + i * stride) for i in range(n)]

    def pos(self):
        v = self._leer(CH_POS, self.vertices)
        return [list(x) if x is not None else [0.0, 0.0, 0.0] for x in v]

    def nrm(self):
        v = self._leer(CH_NRM, self.vertices)
        return [list(x) if x is not None else [0.0, 0.0, 1.0] for x in v]

    def uv0(self):
        v = self._leer(CH_UV0, self.vertices)
        return [list(x) if x is not None else [0.0, 0.0] for x in v]

    def pesos(self):
        return [_cuatro(x) for x in self._leer(CH_WGT, self.vertices)]

    def indices_hueso(self):
        return [[int(y) for y in _cuatro(x)] for x in self._leer(CH_IDX, self.vertices)]

    def triangulos(self, i: int):
        sm = self.m.m_SubMeshes[i]
        ib = self.m.m_IndexBuffer
        ancho = 4 if self.m.m_IndexFormat == 1 else 2
        n = sm.indexCount
        off = sm.firstByte
        if isinstance(ib, (bytes, bytearray)):
            datos = bytes(ib)
        else:
            # UnityPy devuelve `m_IndexBuffer` como lista de BYTES crudos, no de indices ya
            # parseados: hay que empaquetarla antes de leerla como u16/u32. Leerla tal cual daba
            # indices en 0..255 y el FBX salia con la geometria destrozada.
            datos = bytes(x & 0xFF for x in ib)
        letra = "I" if ancho == 4 else "H"
        return list(struct.unpack_from("<%d%s" % (n, letra), datos, off))


def _matrices(mats):
    """Matrix4x4 de UnityPy -> 16 floats en orden fila-mayor (como las escribe el capturador)."""
    out = []
    for m in mats:
        out.append([m.e00, m.e01, m.e02, m.e03, m.e10, m.e11, m.e12, m.e13,
                    m.e20, m.e21, m.e22, m.e23, m.e30, m.e31, m.e32, m.e33])
    return out


# --------------------------------------------------------------------------- jerarquia de huesos

def _jerarquia(env, actor: str = "", requeridos: set | None = None):
    """(nombre, padre, pos, rot, esc) del subarbol del actor, en orden de aparicion.

    El bundle `role_*` trae el prefab del actor y, a veces, copias o props sueltos. Interesa SOLO el
    arbol del actor: se eligen las raices (transforms sin padre) y se toma la que lleva su nombre; si
    no, la de mayor subarbol. Coger todo el bundle inflaba el esqueleto con cientos de nodos ajenos.

    OJO con fiarse del NOMBRE: `closer` tiene un GameObject raiz de malla que se llama
    `closer_uniform_shoes_wholeexport_rig` (empieza por `closer`, asi que casaba) y su arbol son 3
    nodos sin un solo hueso; el rig de verdad (`closer_uniform`, 218 nodos) vive en OTRO bundle. Por
    eso, si se conocen los huesos que piden las mallas (`requeridos`), se elige la raiz cuyo subarbol
    los CUBRE, y solo despues se mira el nombre y el tamano.
    """
    trans = {}
    for obj in env.objects:
        if obj.type.name == "Transform":
            try:
                trans[obj.path_id] = obj.read()
            except Exception:
                pass

    def nombre_de(t):
        try:
            return getattr(t.m_GameObject.read(), "m_Name", "") or ""
        except Exception:
            return ""

    info = {}
    hijos = {}
    raices = []
    for pid, t in trans.items():
        nombre = nombre_de(t)
        if not nombre:
            continue
        try:
            padre_id = t.m_Father.path_id if t.m_Father else None
        except Exception:
            padre_id = None
        lp, lr, ls = t.m_LocalPosition, t.m_LocalRotation, t.m_LocalScale
        info[pid] = {"nombre": nombre, "padre_id": padre_id,
                     "pos": [lp.x, lp.y, lp.z], "rot": [lr.x, lr.y, lr.z, lr.w],
                     "esc": [ls.x, ls.y, ls.z]}
        if padre_id and padre_id in trans and padre_id in info:
            hijos.setdefault(padre_id, []).append(pid)
        else:
            raices.append(pid)
    # el padre puede haberse añadido despues; recalcular hijos de forma robusta
    hijos = {}
    raices = []
    for pid, h in info.items():
        p = h["padre_id"]
        if p and p in info:
            hijos.setdefault(p, []).append(pid)
        else:
            raices.append(pid)

    def subarbol(pid):
        out = [pid]
        for h in hijos.get(pid, []):
            out += subarbol(h)
        return out

    if not raices:
        return []
    bajo = (actor or "").lower()
    req = set(requeridos or ())

    def cobertura(pid):
        if not req:
            return 0
        return len({info[p]["nombre"] for p in subarbol(pid)} & req)

    def por_nombre(pid):
        n = info[pid]["nombre"].lower()
        return n == bajo or n == bajo + "_nocontroller" or (bajo and n.startswith(bajo))

    # 1) la raiz que de verdad monta los huesos que piden las mallas; 2) la que lleva el nombre del
    # actor; 3) la de mayor subarbol. Cada criterio solo se usa si el anterior no decide nada.
    raiz = None
    if req:
        mejor = max(raices, key=lambda p: (cobertura(p), len(subarbol(p))))
        if cobertura(mejor) > 0:
            raiz = mejor
    if raiz is None and bajo:
        nombradas = [p for p in raices if por_nombre(p)]
        if nombradas:
            raiz = max(nombradas, key=lambda p: (cobertura(p), len(subarbol(p))))
    if raiz is None:
        raiz = max(raices, key=lambda p: (cobertura(p), len(subarbol(p))))

    orden = subarbol(raiz)
    idx = {pid: i for i, pid in enumerate(orden)}
    huesos = []
    for pid in orden:
        h = info[pid]
        padre = info.get(h["padre_id"])
        huesos.append({"nombre": h["nombre"], "padre": padre["nombre"] if padre and
                       h["padre_id"] in idx else None,
                       "pos": h["pos"], "rot": h["rot"], "esc": h["esc"]})
    return huesos


# --------------------------------------------------------------------------- escritura del volcado

def _limpia(n: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", n).strip().rstrip(".")


def _escribe_bin(ruta: Path, valores, forma: int, tipo: str):
    """Escribe filas de `forma` componentes. Si una fila trae menos, se rellena con ceros.

    No es cosmetico: el ensamblador lee estos ficheros con un ancho fijo, asi que una fila corta
    desplazaba todas las siguientes (los ojos traen solo 2 influencias por vertice).
    """
    relleno = 0.0 if tipo in ("f", "d") else 0
    plano = []
    for v in valores:
        fila = list(v) if isinstance(v, (list, tuple)) else [v]
        fila = (fila + [relleno] * forma)[:forma]
        plano.extend(fila)
    ruta.write_bytes(struct.pack("<%d%s" % (len(plano), tipo), *plano))


def volcar(ficheros, dump, actor: str = "", log=print, texturas=None, filtro=None) -> dict:
    """Reconstruye el volcado desde los bundles y lo escribe en `dump`.

    `filtro` es un predicado opcional `nombre_malla -> bool`: deja fuera las mallas que no son del
    traje que se esta extrayendo (el bundle del modelo trae varios trajes mezclados).
    """
    dump = Path(dump)
    dump.mkdir(parents=True, exist_ok=True)
    log = log or (lambda s: None)

    entornos = []
    for f in ficheros:
        try:
            entornos.append(_abrir(f))
        except Exception as e:
            log(t("ru_bundle_error", Path(f).name, str(e)[:120]))

    # --- mallas con piel (sin las de baja calidad ni las sombras)
    mallas: dict[str, _Malla] = {}
    for env in entornos:
        for obj in env.objects:
            if obj.type.name != "Mesh":
                continue
            try:
                mm = _Malla(obj)
            except Exception:
                continue
            bajo = mm.nombre.lower()
            if "_wholeexport_rig" not in bajo:
                continue
            if any(d in bajo for d in DESCARTABLES):
                continue
            # las armas ALTERNATIVAS (`<actor>_weapon_NN_wholeexport_rig`) no son parte del modelo
            # puesto: el juego las nombra aparte y el capturador de Unity tambien las excluye.
            if re.search(r"_weapon_\d+_wholeexport_rig", bajo):
                continue
            if filtro is not None and not filtro(mm.nombre):
                continue
            if mm.vertices <= 0 or not mm.bindpose:
                continue
            # la cara con expresiones (_bs) sustituye a la llana, como en el capturador de Unity
            mallas[mm.nombre] = mm
    if not mallas:
        raise RuntimeError(t("ru_err_sin_malla"))

    # --- manifiestos: por malla, la lista ordenada de huesos
    huesos_por_malla: dict[str, list] = {}
    for env in entornos:
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                raw = obj.get_raw_data()
            except Exception:
                continue
            for nombre_malla, mm in mallas.items():
                if nombre_malla in huesos_por_malla:
                    continue
                if nombre_malla.encode("utf-8", "ignore") not in raw:
                    continue
                idx_max = max((max(f) for f in mm.indices_hueso()), default=0)
                hallado = _buscar_lista_huesos(raw, len(mm.bindpose), idx_max)
                if hallado:
                    huesos_por_malla[nombre_malla] = hallado[0]
                    break
    log(t("ru_manifiestos", len(huesos_por_malla), len(mallas)))

    # --- jerarquia del actor. Se prueban TODOS los entornos y se elige el subarbol que de verdad
    # monta los huesos que piden los manifiestos: el bundle del modelo puede traer un GameObject raiz
    # que empieza por el nombre del actor pero no es su rig (le pasa a `closer`).
    requeridos = set()
    for lista in huesos_por_malla.values():
        requeridos |= set(lista)
    huesos, mejor_cob = [], -1
    for env in entornos:
        h = _jerarquia(env, actor, requeridos)
        if not h:
            continue
        cob = len({x["nombre"] for x in h} & requeridos) if requeridos else len(h)
        if (cob, len(h)) > (mejor_cob, len(huesos)):
            huesos, mejor_cob = h, cob
    # Respaldo: si ninguno de los bundles dados trae el rig (el catalogo no lo engancho), se busca
    # por el nombre del prefab en el indice de assets y se abre el bundle que lo tiene.
    if not huesos or mejor_cob <= 0:
        for extra in _rigs_del_catalogo(actor):
            try:
                env = _abrir(extra)
            except Exception:
                continue
            h = _jerarquia(env, actor, requeridos)
            if not h:
                continue
            cob = len({x["nombre"] for x in h} & requeridos) if requeridos else len(h)
            if (cob, len(h)) > (mejor_cob, len(huesos)):
                huesos, mejor_cob = h, cob
    if not huesos:
        raise RuntimeError(t("ru_err_sin_jerarquia"))
    (dump / "esqueleto.json").write_text(
        json.dumps({"total": len(huesos), "huesos": huesos}, ensure_ascii=False), encoding="utf-8")
    log(t("ru_jerarquia", len(huesos)))

    # --- texturas/materiales del bundle (el PNG lo resuelve el ensamblador por nombre)
    catalogo = _catalogo_materiales(entornos)

    # --- una parte por malla
    partes = []
    mallas_con_pesos = 0
    huesos_unicos = set()
    for nombre_malla, mm in sorted(mallas.items()):
        lista = huesos_por_malla.get(nombre_malla)
        if not lista:
            log(t("ru_sin_manifiesto", nombre_malla[-40:]))
            continue
        parte = _limpia(nombre_malla)
        pos = mm.pos()
        nrm = mm.nrm()
        uv = mm.uv0()
        if mm.tiene(CH_WGT) and mm.tiene(CH_IDX):
            wgt = mm.pesos()
            bidx = mm.indices_hueso()
        else:
            # malla con inversa de bind pero sin canal de piel (props de un solo hueso): Unity la
            # sirve con todos los vertices a peso 1 sobre el hueso 0; se replica para que la malla
            # cuente como riggeada.
            wgt = [[1.0, 0.0, 0.0, 0.0]] * mm.vertices
            bidx = [[0, 0, 0, 0]] * mm.vertices
        con_peso = sum(1 for w in wgt if sum(w) > 1e-6)
        if con_peso:
            mallas_con_pesos += 1
        _escribe_bin(dump / (parte + ".pos.bin"), pos, 3, "f")
        _escribe_bin(dump / (parte + ".nrm.bin"), nrm, 3, "f")
        _escribe_bin(dump / (parte + ".uv0.bin"), uv, 2, "f")
        _escribe_bin(dump / (parte + ".bwgt.bin"), wgt, 4, "f")
        idx16 = [[min(int(x), 65535) for x in fila] for fila in bidx]
        _escribe_bin(dump / (parte + ".bidx.bin"), idx16, 4, "H")
        _escribe_bin(dump / (parte + ".ibm.bin"), mm.bindpose, 16, "f")
        tri_por_sub = []
        for i in range(mm.submallas):
            tri = mm.triangulos(i)
            tri_por_sub.append(len(tri) // 3)
            _escribe_bin(dump / (parte + ".tris%d.bin" % i), tri, 1, "I")

        # lista de huesos con su padre (indice dentro de la lista) y transform local del actor
        trs = {h["nombre"]: h for h in huesos}
        lista_json = []
        for nom in lista:
            h = trs.get(nom)
            if h is None:
                lista_json.append({"nombre": nom, "padre": -1, "pos": [0, 0, 0],
                                   "rot": [0, 0, 0, 1], "esc": [1, 1, 1]})
                huesos_unicos.add(nom)
                continue
            padre = -1
            if h.get("padre") in lista:
                padre = lista.index(h["padre"])
            lista_json.append({"nombre": nom, "padre": padre, "pos": h["pos"],
                               "rot": h["rot"], "esc": h["esc"]})
            huesos_unicos.add(nom)

        meta = {
            "parte": parte, "malla": nombre_malla, "submallas": mm.submallas,
            "vertices": mm.vertices, "vertices_con_peso": con_peso,
            "triangulos_por_submalla": tri_por_sub, "huesos": len(lista),
            "expresiones": 0, "bounds_centro": [0, 0, 0], "bounds_tamano": [0, 0, 0],
            "lista_huesos": lista_json, "lista_expresiones": [],
            "materiales": _materiales(mm, catalogo),
        }
        (dump / (parte + ".json")).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        partes.append({"parte": parte, "vertices": mm.vertices, "vertices_con_peso": con_peso,
                       "huesos": len(lista), "expresiones": 0,
                       "triangulos": sum(tri_por_sub)})
        log(t("ru_parte", parte[-34:], mm.vertices, con_peso, len(lista)))

    (dump / "resumen.json").write_text(json.dumps({
        "actor": actor, "unity": "bundles", "partes": len(partes),
        "mallas_con_pesos": mallas_con_pesos, "huesos_unicos": len(huesos_unicos),
        "lista": partes}, ensure_ascii=False), encoding="utf-8")
    return {"partes": len(partes), "mallas_con_pesos": mallas_con_pesos,
            "huesos_unicos": len(huesos_unicos)}


def _catalogo_materiales(entornos) -> dict:
    """Nombre de material -> {nombre, texturas:[{slot, textura}]} con el PNG de cada textura."""
    out = {}
    for env in entornos:
        for obj in env.objects:
            if obj.type.name != "Material":
                continue
            try:
                m = obj.read()
            except Exception:
                continue
            nombre = getattr(m, "m_Name", "") or ""
            if not nombre or nombre in out:
                continue
            texturas = []
            try:
                for slot, te in m.m_SavedProperties.m_TexEnvs:
                    try:
                        tn = te.m_Texture.read().m_Name
                    except Exception:
                        tn = None
                    if tn:
                        texturas.append({"slot": slot, "textura": tn + ".png"})
            except Exception:
                pass
            out[nombre] = {"nombre": nombre, "texturas": texturas}
    return out


def _token_rig(nombre_malla: str) -> str:
    """El trozo del nombre tras `_wholeexport_rig` (el prefijo del rig): casa malla con material."""
    i = nombre_malla.lower().find("_wholeexport_rig")
    if i < 0:
        return nombre_malla
    tok = nombre_malla[i + len("_wholeexport_rig"):]
    return tok.lstrip("_")


def _materiales(mm, catalogo: dict):
    """Materiales de una malla: los del bundle cuyo nombre encaja con el token del rig.

    La comparacion es SIN distinguir mayusculas: la malla se llama `..._rig_pc077_01_body` (en
    minusculas) y su material `PC077_01_body`, y antes no casaban, asi que el cuerpo se quedaba sin
    material ni texturas en el GLB. Se prefiere la coincidencia EXACTA sobre las variantes (`_01`,
    `_02`, `_lodlow`), que son subpiezas o copias de baja calidad.

    Ojo: hay materiales cuyo nombre si casa pero cuyas texturas viven en un bundle de dependencia
    (los `cab-...`) que aqui no se abre; esos salen con la lista de texturas vacia. No es un fallo
    de este modulo: el ensamblador del GLB completa esas texturas por nombre desde los PNG ya
    extraidos (ver `glb_rig`).
    """
    token = _token_rig(mm.nombre).lower()
    exacto = [v for k, v in catalogo.items() if k.lower() == token]
    cand = exacto or [v for k, v in catalogo.items() if k.lower().startswith(token)]
    if not cand:
        cand = [v for k, v in catalogo.items() if token and token.startswith(k.lower())]
    # de las variantes, primero las que traen texturas resueltas y luego las que no son `lodlow`
    cand.sort(key=lambda v: (0 if v["texturas"] else 1,
                             1 if "lodlow" in v["nombre"].lower() else 0, v["nombre"]))
    out = []
    for i in range(mm.submallas):
        if i < len(cand):
            out.append({"indice": i, "nombre": cand[i]["nombre"], "texturas": cand[i]["texturas"]})
        elif cand:
            out.append({"indice": i, "nombre": cand[-1]["nombre"], "texturas": cand[-1]["texturas"]})
        else:
            out.append({"indice": i, "nombre": None})
    return out
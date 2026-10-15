"""Genera los diagramas del tutorial de extraccion (PIL, sin dependencias raras).

Salida: tutorial_extraccion_3d/img/*.png
Todo lo que aparece escrito son datos medidos en el proyecto, no ilustraciones inventadas.
"""
import os
from PIL import Image, ImageDraw, ImageFont

SALIDA = r"C:/Users/Lukas/p5x-datamining/tutorial_extraccion_3d/img"
FONDOS = (26, 28, 32)
PANEL = (38, 42, 48)
BORDE = (86, 94, 104)
TEXTO = (232, 234, 238)
SUAVE = (160, 168, 178)
AZUL = (86, 156, 214)
VERDE = (106, 190, 116)
ROJO = (214, 106, 96)
AMARILLO = (222, 186, 106)


def fuente(px, negrita=False):
    for ruta in (r"C:/Windows/Fonts/segoeuib.ttf" if negrita else r"C:/Windows/Fonts/segoeui.ttf",
                 r"C:/Windows/Fonts/arialbd.ttf" if negrita else r"C:/Windows/Fonts/arial.ttf",
                 r"C:/Windows/Fonts/calibrib.ttf" if negrita else r"C:/Windows/Fonts/calibri.ttf"):
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, px)
    return ImageFont.load_default()


def caja(d, x, y, w, h, titulo, lineas, color=BORDE, relleno=PANEL, f_tit=22, f_txt=17):
    d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=relleno, outline=color, width=2)
    ft, fx = fuente(f_tit, True), fuente(f_txt)
    d.text((x + 14, y + 11), titulo, font=ft, fill=TEXTO)
    yy = y + 11 + f_tit + 8
    for ln in lineas:
        d.text((x + 14, yy), ln, font=fx, fill=SUAVE)
        yy += f_txt + 6


def flecha(d, x1, y1, x2, y2, color=AZUL):
    d.line([x1, y1, x2, y2], fill=color, width=3)
    # punta
    if abs(x2 - x1) >= abs(y2 - y1):
        signo = 1 if x2 > x1 else -1
        d.polygon([(x2, y2), (x2 - 12 * signo, y2 - 7), (x2 - 12 * signo, y2 + 7)], fill=color)
    else:
        signo = 1 if y2 > y1 else -1
        d.polygon([(x2, y2), (x2 - 7, y2 - 12 * signo), (x2 + 7, y2 - 12 * signo)], fill=color)


# --------------------------------------------------------------------------------------
def pipeline():
    """El recorrido completo: del juego al FBX en Blender."""
    W, H = 1500, 900
    im = Image.new("RGB", (W, H), FONDOS)
    d = ImageDraw.Draw(im)
    d.text((40, 30), "Cómo sale un modelo 3D de P5X (recorrido completo)", font=fuente(30, True), fill=TEXTO)
    d.text((40, 72), "Cada caja es un paso. Debajo, lo que hay que saber para no atascarse ahí.",
           font=fuente(18), fill=SUAVE)

    y = 130
    alto = 122
    ancho = 250
    sep = 60
    pasos = [
        ("1. El juego", ["P5X cliente PC (gratis)", "bin\\_vfileIndexV2.fb", "+ _vfileContent*"]),
        ("2. El contenedor", ["P5X_vFileContentExtract", "Lo ya desofuscado:", ".bundle + .bytes + .txt"]),
        ("3. AssetStudioMod", ["Carga la carpeta", "Mira y exporta:", "PNG · OBJ · FBX · JSON"]),
        ("4. Unity 2022.3", ["Aquí se monta el rig", "El prefab es solo", "huesos: hay que armarlo"]),
        ("5. Exportar", ["Editor script propio", "Vuelca malla+huesos", "pesos+bindposes"]),
        ("6. Blender", ["Importas el FBX", "y ya puedes posar,", "texturizar, renderizar"]),
    ]
    x = 40
    centros = []
    for i, (t, ln) in enumerate(pasos):
        caja(d, x, y, ancho, alto, t, ln)
        centros.append((x + ancho, y + alto // 2))
        if i < len(pasos) - 1:
            flecha(d, x + ancho + 6, y + alto // 2, x + ancho + sep - 6, y + alto // 2)
        x += ancho + sep

    # aviso grande
    y2 = y + alto + 60
    d.rounded_rectangle([40, y2, W - 40, y2 + 96], radius=10, fill=(46, 38, 30), outline=AMARILLO, width=2)
    d.text((60, y2 + 14), "El atasco número uno (y por qué este tutorial tiene 5 capítulos de trampas):",
           font=fuente(21, True), fill=AMARILLO)
    d.text((60, y2 + 48), "en P5X los personajes NO son un prefab normal de Unity. El prefab que exporta AssetRipper trae 272 nodos",
           font=fuente(18), fill=TEXTO)
    d.text((60, y2 + 72), "de hueso y CERO mallas visibles. Si arrastras el personaje a la escena ves el esqueleto y nada más.",
           font=fuente(18), fill=TEXTO)

    # segunda via
    y3 = y2 + 130
    d.text((40, y3), "Hay dos caminos, y conviene saber cuál estás siguiendo:", font=fuente(21, True), fill=TEXTO)
    caja(d, 40, y3 + 40, 690, 150,
         "Vía A — la de la comunidad (la más corta)",
         ["P5X Character Importer + los scripts de P5X_Research montan el rig DENTRO de Unity,",
          "se compila el reproductor con LZ4 (data.unity3d) y ESE fichero se abre en AssetStudioMod,",
          "que sí saca un FBX ya riggeado con sus clips de animación.",
          "",
          "Necesita: Unity con licencia (hay que iniciar sesión una vez, a mano)."], color=VERDE)
    caja(d, 760, y3 + 40, 700, 150,
         "Vía B — la que usé aquí (sin Unity con licencia)",
         ["AssetStudioMod saca texturas y mallas sueltas; un proyecto Unity rearmado vuelca a binario",
          "vértices, huesos, pesos, bind poses y expresiones; y un script de Python escribe el GLB a mano.",
          "",
          "Más trabajo, pero no depende de que ningún exportador ajeno haga bien su parte."], color=AZUL)

    d.text((40, H - 46), "Regla que vale para todo el recorrido: mide, no mires. La vista se equivoca y te hará perder el día.",
           font=fuente(18, True), fill=AMARILLO)
    im.save(os.path.join(SALIDA, "01_recorrido.png"))
    return "01_recorrido.png"


def rig_mua():
    """Por que el prefab del personaje sale sin malla, y como se arma."""
    W, H = 1500, 780
    im = Image.new("RGB", (W, H), FONDOS)
    d = ImageDraw.Draw(im)
    d.text((40, 30), "El sistema de rig propio de P5X (MUActor) y el problema que genera",
           font=fuente(28, True), fill=TEXTO)

    caja(d, 40, 100, 430, 210, "Lo que espera Unity normalmente",
         ["Un prefab de personaje con:", "",
          "  · SkinnedMeshRenderer  (la malla con piel)",
          "  · materials           (sus texturas)",
          "  · Animator            (los clips)"], color=SUAVE)

    caja(d, 530, 100, 430, 210, "Lo que trae P5X",
         ["El prefab del actor es SOLO el esqueleto:", "",
          "  · 272 nodos de hueso (exDummy:Jnt_*)",
          "  · 0 SkinnedMeshRenderer",
          "  · MonoBehaviours MUActor* de configuración"],
         color=ROJO)

    caja(d, 1020, 100, 440, 210, "Por qué",
         ["Esos MonoBehaviour son scripts del juego. En el",
          "volcado quedan como stubs vacíos, así que las",
          "herramientas no ven ninguna malla que montar",
          "y no escriben el renderer.", "",
          "La malla y los pesos SÍ existen: están en otro sitio."], color=AMARILLO)

    flecha(d, 960, 205, 1014, 205, ROJO)

    y = 360
    d.text((40, y), "Dónde están de verdad los datos", font=fuente(23, True), fill=TEXTO)

    caja(d, 40, y + 42, 440, 220, "En el manifiesto del rig",
         ["prefabs/..._body_wholeexport_rig.prefab", "",
          "mHighRootBoneName    hueso raíz",
          "mHighMeshBoneNames[] orden de los huesos",
          "mHighMeshMaterials[] qué material lleva",
          "mLODMesh             el fichero de malla"], color=AZUL)

    caja(d, 530, y + 42, 440, 220, "En la malla (.asset)",
         ["Lleva los canales estándar de Unity:", "",
          "  BoneWeights  (stream2, formato 0, dim 4)",
          "  BoneIndices  (stream2, formato 10, dim 4)",
          "  bindPose     (matrices de enlace)", "",
          "Verificado en el cuerpo de PC063: 2214 verts, 27 huesos"], color=AZUL)

    caja(d, 1020, y + 42, 440, 220, "En un prefab de texto plano",
         ["Los MonoBehaviour no se serializan (son stubs),",
          "PERO el YAML del fichero SÍ conserva el",
          "manifiesto como texto.", "",
          "→ Se lee con una expresión regular y se",
          "   construye el SkinnedMeshRenderer desde",
          "   un script que se pega en Assets/Editor/."], color=VERDE)

    flecha(d, 480, y + 152, 524, y + 152, AZUL)
    flecha(d, 970, y + 152, 1014, y + 152, AZUL)

    d.text((40, H - 44), "La lista de huesos del manifiesto viene indentada: el patrón que la captura es  ^\\s*-\\s*(.+?)\\s*$",
           font=fuente(18, True), fill=AMARILLO)
    im.save(os.path.join(SALIDA, "02_rig_mua.png"))
    return "02_rig_mua.png"


def uv_v():
    """El volteo de la V, con los numeros medidos."""
    W, H = 1420, 700
    im = Image.new("RGB", (W, H), FONDOS)
    d = ImageDraw.Draw(im)
    d.text((40, 30), "La trampa que más tiempo cuesta: la V de las UV", font=fuente(28, True), fill=TEXTO)
    d.text((40, 70), "Unity guarda la V de abajo arriba; el PNG y glTF/OBJ van de arriba abajo. Sin voltearla, todo cae al revés.",
           font=fuente(18), fill=SUAVE)

    y = 130
    caja(d, 40, y, 640, 330, "Sin invertir  ->  mi primera entrega",
         ["Zona        color medido            lo que decía el arte",
          "",
          "  espinilla    (28, 28, 28)   negro      media BLANCA",
          "  tobillo      (59, 57, 54)   oscuro     media blanca",
          "  cara         87% de texels = piel lisa  cejas, iris, pestañas",
          "",
          "El modelo se veía bien de forma. Los calcetines salían",
          "negros y la cara como una máscara sin rasgos."], color=ROJO)

    caja(d, 740, y, 640, 330, "Con  v -> 1 - v  ->  correcto",
         ["Zona        color medido            lo que dice el arte",
          "",
          "  espinilla    (205, 199, 191) claro     media BLANCA",
          "  tobillo      (176, 168, 159) claro     media blanca",
          "  cara         rasgos: cejas, iris,      cara con rasgos",
          "               pestañas",
          "",
          "Arreglado en el constructor del GLB (helper uv_gltf),",
          "y afecta a GLB y OBJ por igual."], color=VERDE)

    # muestra de color real
    y2 = y + 360
    d.text((40, y2), "Los dos colores, tal cual se midieron:", font=fuente(21, True), fill=TEXTO)
    d.rectangle([40, y2 + 40, 300, y2 + 130], fill=(28, 28, 28), outline=BORDE, width=2)
    d.text((50, y2 + 148), "sin invertir  (28,28,28)", font=fuente(17), fill=SUAVE)
    d.rectangle([330, y2 + 40, 590, y2 + 130], fill=(205, 199, 191), outline=BORDE, width=2)
    d.text((340, y2 + 148), "correcto  (205,199,191)", font=fuente(17), fill=SUAVE)

    d.text((660, y2 + 40), "Cómo decidirlo sin fiarse de la vista:", font=fuente(20, True), fill=AMARILLO)
    d.text((660, y2 + 76), "toma una parte del cuerpo cuyo color conozcas por el arte oficial (aquí, la media blanca),", font=fuente(17), fill=TEXTO)
    d.text((660, y2 + 100), "busca en el atlas los texeles que caen bajo esas UV y compara las MEDIANAS de color.", font=fuente(17), fill=TEXTO)
    d.text((660, y2 + 124), "El modelo de visión describió colores que no existían: midiendo se resuelve en un minuto.", font=fuente(17), fill=AMARILLO)
    im.save(os.path.join(SALIDA, "03_uv_v.png"))
    return "03_uv_v.png"


def ejes():
    """Zurdo vs diestro y por que el espejo importa."""
    W, H = 1420, 760
    im = Image.new("RGB", (W, H), FONDOS)
    d = ImageDraw.Draw(im)
    d.text((40, 30), "Los ejes: el error que produce un modelo espejado sin que nada avise", font=fuente(28, True), fill=TEXTO)

    # eje zurdo (juego)
    ox, oy = 200, 400
    d.text((100, 110), "El espacio del JUEGO (zurdo)", font=fuente(21, True), fill=TEXTO)
    d.text((100, 140), "X derecha · Y arriba · Z adelante", font=fuente(17), fill=SUAVE)
    flecha(d, ox, oy, ox + 150, oy, VERDE)      # X
    flecha(d, ox, oy, ox, oy - 150, VERDE)      # Y
    flecha(d, ox, oy, ox + 110, oy + 110, AMARILLO)  # Z
    d.text((ox + 158, oy - 12), "X", font=fuente(20, True), fill=VERDE)
    d.text((ox - 8, oy - 180), "Y", font=fuente(20, True), fill=VERDE)
    d.text((ox + 118, oy + 112), "Z (adelante)", font=fuente(17, True), fill=AMARILLO)

    # eje diestro (glTF / Blender)
    ox2 = 700
    d.text((600, 110), "El espacio de glTF / Blender (diestro)", font=fuente(21, True), fill=TEXTO)
    d.text((600, 140), "Mano contraria: hay que decidir bien la conversión", font=fuente(17), fill=SUAVE)
    flecha(d, ox2, oy, ox2 + 150, oy, VERDE)
    flecha(d, ox2, oy, ox2, oy - 150, VERDE)
    flecha(d, ox2, oy, ox2 - 110, oy + 110, AMARILLO)
    d.text((ox2 + 158, oy - 12), "X", font=fuente(20, True), fill=VERDE)
    d.text((ox2 - 8, oy - 180), "Y", font=fuente(20, True), fill=VERDE)
    d.text((ox2 - 200, oy + 112), "Z (adelante)", font=fuente(17, True), fill=AMARILLO)

    caja(d, 40, 470, 640, 220, "La conversión que parece correcta y te espeja el modelo",
         ["Leer un espacio zurdo y escribirlo en uno diestro con un giro (x,y,z)->(-x, z, y)",
          "tiene determinante +1: es una rotación normal y corriente... y produce el ESPEJO.",
          "",
          "Lo peor: todas tus comprobaciones numéricas darán OK, porque el volcado del juego",
          "está espejado exactamente igual. Comparar exportación contra volcado solo demuestra",
          "que los dos coinciden entre sí. Nunca demuestra que sea el original."], color=ROJO)

    caja(d, 740, 470, 640, 220, "Cómo se detecta de verdad",
         ["La conversión correcta es impropia: (x,y,z)->(x, z, y), determinante -1. Es un espejo,",
          "así que hay que voltear también el bobinado de las caras.",
          "",
          "Síntomas que solo produce un espejo:",
          "  · texto del modelo que se lee al revés (las letras S.E.E.S. de la banda)",
          "  · un accesorio en la extremidad contraria a la del arte oficial"], color=VERDE)

    d.text((40, H - 44), "Un giro de 180 grados sobre la vertical NUNCA cambia una pieza de brazo: solo gira al personaje. Espejo y giro no son lo mismo.",
           font=fuente(17, True), fill=AMARILLO)
    im.save(os.path.join(SALIDA, "04_ejes.png"))
    return "04_ejes.png"


if __name__ == "__main__":
    os.makedirs(SALIDA, exist_ok=True)
    for f in (pipeline(), rig_mua(), uv_v(), ejes()):
        print("escrito:", os.path.join(SALIDA, f))

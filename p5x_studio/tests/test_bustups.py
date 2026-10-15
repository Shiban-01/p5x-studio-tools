"""Prueba del visor de bust-ups: nombres de capa, orden de apilado, montaje real y exportacion.

El montaje de verdad solo se prueba si hay texturas. La app no lleva ninguna ruta absoluta del
equipo, asi que la carpeta se busca en `extracted/textures` o en la que diga P5X_STUDIO_TEXTURAS
(asi la prueba sirve igual en otro equipo). Sin texturas se comprueban las piezas que no dependen
de ficheros: el troceado de nombres, el orden de apilado y el mapa que viaja en el ejecutable.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, bustups, lote, motor, sombreado  # noqa: E402

# --------------------------------------------------------------------------- 1) nombres de capa
CASOS = [
    # nombre del asset, personaje, ropa del JSON -> (expresion, parte)
    ("xiachuanling-changfu-benti", "xiachuanling", "changfu", ("base", "benti")),
    ("xiachuanling-changfu-benti-toufa", "xiachuanling", "changfu", ("base", "toufa")),
    ("xiachuanling-changfu-benti-lunkuo", "xiachuanling", "changfu", ("base", "lunkuo")),
    ("xiachuanling-changfu-tongchang-yan1", "xiachuanling", "changfu", ("tongchang", "yan1")),
    ("xiachuanling-changfu-beiai-zui2", "xiachuanling", "changfu", ("beiai", "zui2")),
    # la ropa puede venir con variante: el troceado tiene que aguantar las dos formas
    ("xiachuanling-changfu-benti", "xiachuanling", "changfu01", ("base", "benti")),
    ("xiachuanling-changfu-xiao-zui1", "xiachuanling", "changfu01", ("xiao", "zui1")),
]
for nombre, personaje, ropa, esperado in CASOS:
    obtenido = bustups.partir_nombre(nombre, personaje, ropa)
    comun.comprobar(obtenido == esperado,
                    "%s -> %s (esperado %s)" % (nombre, obtenido, esperado))

# --------------------------------------------------------------------------- 2) paso de apilado
comun.comprobar(bustups.paso_de("benti") == "body", "benti -> cuerpo")
comun.comprobar(bustups.paso_de("toufa") == "hair", "toufa -> pelo")
comun.comprobar(bustups.paso_de("yan1") == "eyes", "yan1 -> ojos (el numero no estorba)")
comun.comprobar(bustups.paso_de("zui2") == "mouth", "zui2 -> boca")
comun.comprobar(bustups.paso_de("saihong") == "blush", "saihong -> rubor")
comun.comprobar(bustups.paso_de("yanjing") == "glasses", "yanjing -> gafas")
comun.comprobar(bustups.paso_de("mojing") == "glasses", "mojing -> gafas de sol")
comun.comprobar(bustups.paso_de("mask01") == "mask", "mask01 -> mascara")
comun.comprobar(bustups.paso_de("mianju") == "mask", "mianju -> mascara")
comun.comprobar(bustups.paso_de("maozi") == "hat", "maozi -> sombrero")
comun.comprobar(bustups.paso_de("han") == "marks", "han -> gotas")
comun.comprobar(bustups.paso_de("lei") == "marks", "lei -> lagrimas")
comun.comprobar(bustups.paso_de("zapato") is None, "una parte que no existe no se coloca")

# la cara: `benti-<expresion>` no es una parte, es la cara de ese gesto (sin esto la cabeza sale
# negra, que es el fallo que se vio en jianajun)
comun.comprobar(bustups.partir_nombre("jianajun-changfu-benti-tongchang", "jianajun", "changfu")
                == ("tongchang", "cara"), "benti-tongchang -> cara de tongchang")
# hay ropas cuyo numero forma parte del nombre: si se recorta, se pierden ojos, boca y cara
comun.comprobar(bustups.partir_nombre("gaojuanxing-guaidao01-beiai-yan1", "gaojuanxing", "guaidao01")
                == ("beiai", "yan1"), "la ropa con numero (guaidao01) no se recorta")
comun.comprobar(bustups.partir_nombre("xiachuanling-changfu-benti", "xiachuanling", "changfu01")
                == ("base", "benti"), "y cuando los sprites van sin numero, se prueba la otra forma")
# errata del propio juego: el shader y sus mascaras dicen `aochuncun` y el resto de sus sprites
# `aocunchun`; sin el alias su retrato salia con una mascara suelta
comun.comprobar(bustups.ALIAS_PERSONAJE.get("aochuncun") == "aocunchun", "alias de la errata aochuncun")

# --------------------------------------------------------------------------- 3) orden de apilado
PASOS = [p for p, _ in bustups.ORDEN]
comun.comprobar(PASOS[0] == "outline", "el contorno va DEBAJO de todo")
comun.comprobar(PASOS.index("hair") > PASOS.index("eyes")
                and PASOS.index("hair") > PASOS.index("mouth"),
                "el pelo tapa el borde de ojos y boca")
comun.comprobar(PASOS.index("hair") > PASOS.index("face"),
                "el pelo va por encima de la cara (si no, se ve piel sobre el negro del flequillo)")
comun.comprobar(PASOS.index("eyes") > PASOS.index("body"), "los ojos van sobre la cara")
comun.comprobar(PASOS.index("eyes") > PASOS.index("face"), "los ojos van sobre la cara")
comun.comprobar(PASOS.index("glasses") > PASOS.index("eyes")
                and PASOS.index("glasses") > PASOS.index("hair"),
                "las gafas van por encima de todo (peticion del usuario)")
comun.comprobar(PASOS.index("hat") > PASOS.index("hair"), "el sombrero va sobre el pelo")

# --------------------------------------------------------------------------- 3b) el lienzo
comun.comprobar(bustups._lienzo_dominante([(612, 652)] * 5 + [(1076, 2020)] * 2) == (612, 652),
                "gana el lienzo del retrato, no la silueta de cuerpo entero")
comun.comprobar(bustups._lienzo_dominante([(648, 648)] * 32 + [(652, 652)]) == (652, 652),
                "del grupo ganador se usa el tamano mayor (ninguna capa se sale)")
comun.comprobar(bustups._encaja((612, 652), (610, 650)), "4 px de diferencia son el mismo lienzo")

# --------------------------------------------------------------------------- 3c) la expresion `0`
# `0` es el cuerpo por defecto (`<personaje>-<ropa>-0-benti`): si se elige, los ojos y la boca tienen
# que caer a `tongchang` en vez de quedarse fuera (el retrato salia sin cara)
_CAPAS_0 = [{"paso": "eyes", "expresion": "tongchang", "parte": "yan1", "nombre": "ojos-tongchang"},
            {"paso": "eyes", "expresion": "beiai", "parte": "yan1", "nombre": "ojos-beiai"},
            {"paso": "body", "expresion": "0", "parte": "benti", "nombre": "cuerpo-0"}]
comun.comprobar(bustups._elegir_capa(_CAPAS_0, "eyes", "0")["nombre"] == "ojos-tongchang",
                "con la expresion 0 los ojos caen a tongchang")
comun.comprobar(bustups._elegir_capa(_CAPAS_0, "eyes", None)["nombre"] == "ojos-tongchang",
                "sin expresion tambien se coge la del gesto neutro")
comun.comprobar(bustups._elegir_capa(_CAPAS_0, "eyes", "beiai")["nombre"] == "ojos-beiai",
                "con una expresion de verdad se coge la suya")
comun.comprobar(bustups._elegir_capa(_CAPAS_0, "body", "beiai")["nombre"] == "cuerpo-0",
                "el cuerpo sin expresion propia cae a la capa 0")
comun.comprobar("0" not in bustups.expresiones("UI-DialogShader-guaidao01-youjie"),
                "la expresion 0 (el cuerpo) no sale en el selector")

# --------------------------------------------------------------------------- 4) el mapa que viaja
EMPAREJADOS = (bustups.emparejado().get("emparejados") or {})
comun.comprobar(len(EMPAREJADOS) >= 100, "el mapa de bust-ups viaja en el ejecutable (%d)" % len(EMPAREJADOS))
CLAVE = "UI-DialogShader-changfu01-xiachuanling"
comun.comprobar(CLAVE in EMPAREJADOS, "el bust-up de referencia esta en el mapa")
comun.comprobar(bustups.expresiones(CLAVE) == sorted(bustups.expresiones(CLAVE)),
                "las expresiones salen ordenadas (el selector no baila)")
comun.comprobar(len(bustups.expresiones(CLAVE)) >= 5,
                "el de referencia tiene varias expresiones (%s)" % bustups.expresiones(CLAVE))

# --------------------------------------------------------------------------- 5) montaje de verdad
CARPETA = Path(os.environ.get("P5X_STUDIO_TEXTURAS") or "")
if not CARPETA:
    CARPETA = ajustes.carpeta_herramientas() / "textures"
r = motor.bustups_ver(CLAVE, "tongchang", CARPETA)
if not r.get("ok"):
    print("   (sin texturas en %s: se saltan las pruebas de montaje)" % CARPETA)
else:
    comun.comprobar(Path(r["ruta"]).exists(), "el PNG del montaje se escribe")
    pasos = [c["paso"] for c in r["capas"]]
    comun.comprobar("body" in pasos and "hair" in pasos,
                    "el montaje trae cuerpo y pelo (%s)" % pasos)
    comun.comprobar(pasos.index("hair") == len(pasos) - 1,
                    "el pelo es la ultima capa pegada (encima de todo)")
    comun.comprobar(r["lienzo"][0] > 0 and r["lienzo"][1] > 0, "el lienzo tiene tamano")
    for capa in r["capas"]:
        if capa["fiable"]:
            comun.comprobar(capa["difiere"] < 25.0,
                            "%s: la posicion medida cuadra (difiere %.2f%%)"
                            % (capa["nombre"], capa["difiere"]))
    # dos expresiones distintas tienen que dar imagenes distintas (los ojos y la boca cambian)
    otra = motor.bustups_ver(CLAVE, "fennu", CARPETA)
    comun.comprobar(otra.get("ok") and otra["ruta"] != r["ruta"],
                    "cambiar de expresion monta otro fichero")
    comun.comprobar(Path(otra["ruta"]).read_bytes() != Path(r["ruta"]).read_bytes(),
                    "cambiar de expresion cambia la imagen")
    # una expresion que no existe cae en la primera y lo dice
    rara = motor.bustups_ver(CLAVE, "noexiste", CARPETA)
    comun.comprobar(rara.get("ok") and rara["expresion"] in bustups.expresiones(CLAVE),
                    "una expresion inventada no rompe: se usa una que existe")
    # exportar deja el PNG en la carpeta de salida
    tmp = Path(tempfile.mkdtemp(prefix="bustups_prueba_"))
    try:
        exp = motor.bustups_exportar(CLAVE, "tongchang", tmp, CARPETA)
        comun.comprobar(exp.get("ok") and Path(exp["destino"]).exists(),
                        "exportar deja el PNG en la carpeta pedida")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # el fallo que reporto el usuario: hay bust-ups que traen ADEMAS una silueta de cuerpo entero
    # (1076x2020) en las mismas texturas; si el lienzo se coge de ahi, el retrato sale con la cabeza
    # en negro y las capas sueltas
    JIANA = "UI-DialogShader-changfu01-jianajun"
    if JIANA in EMPAREJADOS:
        rj = motor.bustups_ver(JIANA, None, CARPETA)
        if rj.get("ok"):
            comun.comprobar(rj["lienzo"][1] < 1000,
                            "jianajun usa el lienzo del retrato, no el cuerpo entero (%s)" % rj["lienzo"])
            pasos_j = [c["paso"] for c in rj["capas"]]
            comun.comprobar("face" in pasos_j,
                            "jianajun coloca la cara, que es lo que deja la cabeza negra (%s)" % pasos_j)
            comun.comprobar("body" not in pasos_j or rj["lienzo"][1] < 1000,
                            "jianajun no mezcla el cuerpo entero con el retrato")

    # la errata del juego (aochuncun / aocunchun): su retrato tiene que traer cuerpo y ojos, no solo
    # la mascara suelta
    AO = "UI-DialogShader-guaidao01-aochuncun"
    if AO in EMPAREJADOS:
        ra = motor.bustups_ver(AO, None, CARPETA)
        if ra.get("ok"):
            pasos_a = [c["paso"] for c in ra["capas"]]
            comun.comprobar("body" in pasos_a and "eyes" in pasos_a,
                            "la errata aochuncun/aocunchun no deja el retrato en una mascara suelta (%s)"
                            % pasos_a)
            comun.comprobar(len(ra["expresiones"]) >= 4,
                            "y su selector tiene expresiones de verdad (%s)" % ra["expresiones"][:4])

# --------------------------------------------------------------------------- 6) extracto de retratos
# El visor no tiene por que arrastrar los 63 GB del bulk: el extracto saca solo los bundles que
# apunta el mapa y tira lo que no es de ningun retrato. Aqui se comprueban las piezas que deciden
# que se guarda y de donde se lee, que es lo que hace al visor autosuficiente.

# el motor deja los recortes como `nombre_#NN` y el lienzo como `nombre`: los dos son del retrato
comun.comprobar(lote.es_de_retrato("xiachuanling-changfu-benti-toufa.png",
                                   ("xiachuanling-changfu-",)),
                "el lienzo de un retrato entra en el extracto")
comun.comprobar(lote.es_de_retrato("xiachuanling-changfu-benti-toufa_#1356.png",
                                   ("xiachuanling-changfu-",)),
                "y su recorte `_#NN` tambien (el sufijo no cuenta)")
comun.comprobar(not lote.es_de_retrato("uitex_alattack70748f63.png", ("xiachuanling-changfu-",)),
                "una textura de interfaz que no es de ningun retrato se queda fuera")
comun.comprobar(not lote.es_de_retrato("xiachuanling-yinying-benti.png", ("xiachuanling-changfu-",)),
                "y la de otra ropa del mismo personaje tambien")

PREFIJOS = bustups.prefijos_retratos()
comun.comprobar(len(PREFIJOS) >= 70,
                "hay un prefijo por bust-up (personaje + ropa) para el extracto (%s)" % len(PREFIJOS))
comun.comprobar(all(p.endswith("-") for p in PREFIJOS),
                "los prefijos cierran con guion, que es lo que corta el nombre del sprite")
comun.comprobar(len(set(PREFIJOS)) == len(PREFIJOS), "sin repetidos")
comun.comprobar("xiachuanling-changfu-" in PREFIJOS,
                "el prefijo del par que fijo el usuario esta (%s)" % list(PREFIJOS)[:3])
comun.comprobar(any(p.startswith("aocunchun-") for p in PREFIJOS),
                "y el del retrato de la errata va con su grafia buena (aocunchun)")
comun.comprobar(all(b.strip() == b and b for b in PREFIJOS), "los prefijos van limpios")

# los bundles medidos al emparejar: van aparte del mapa (que se recorta para el ejecutable), y sin
# ellos el extracto tendria que mirar 1.506 familias de interfaz en vez de 80
BUNDLES = lote.bundles_de_retratos()
comun.comprobar(len(BUNDLES) >= 70, "el mapa apunta los bundles de los retratos (%s)" % len(BUNDLES))
comun.comprobar(all("uitex" in b for b in BUNDLES),
                "y todos son de texturas de interfaz (%s)" % [b for b in BUNDLES if "uitex" not in b][:2])
comun.comprobar(len(set(BUNDLES)) == len(BUNDLES), "sin repetidos")

# de donde lee el visor: si el extracto esta completo manda el; si no, el bulk (que esta entero)
CARPETA_VISOR = bustups.carpeta_texturas()
comun.comprobar(isinstance(CARPETA_VISOR, Path) and str(CARPETA_VISOR),
                "el visor sabe en que carpeta leer (%s)" % CARPETA_VISOR)
RETRATOS = Path(motor.carpeta_extraidas()) / bustups.CARPETA_RETRATOS
if lote.retratos_listos(RETRATOS):
    comun.comprobar(CARPETA_VISOR == RETRATOS,
                    "con el extracto completo, el visor lee de el y no del bulk (%s)" % CARPETA_VISOR)
elif CARPETA_VISOR == RETRATOS:
    comun.comprobar(not (Path(motor.carpeta_extraidas()) / "textures").is_dir(),
                    "el extracto solo manda si esta completo o si no hay bulk (%s)" % CARPETA_VISOR)

# --------------------------------------------------------------------------- 7) copias del motor
# El juego vuelve a exportar el mismo dibujo con sufijo de copia (`lunkuo_2`, `toufa_2`). Si ese
# sufijo no se limpia, `benti-lunkuo_2` no se reconoce como contorno y cae en la regla de la CARA: el
# visor pinta encima el dibujo entero de la variante (otro busto) creyendo que es el rostro, y de paso
# ofrece `lunkuo_2` como expresion. Pasaba en 14 de los 120 retratos (xiachuanling y aocunchun entre
# ellos). Es el mismo lio de texturas compartidas que ya salio con los modelos.
comun.comprobar(bustups.paso_de("lunkuo_2") == "outline",
                "una copia del contorno sigue siendo contorno")
comun.comprobar(bustups.paso_de("toufa_2") == "hair", "y la del pelo, pelo (no una cara)")
comun.comprobar(bustups.paso_de("mianju_2") == "mask", "y la de la mascara, mascara")
comun.comprobar(bustups.paso_de("benti_2") == "body", "y la del cuerpo, cuerpo")
comun.comprobar(bustups.paso_de("yan2_2") == "eyes", "y la de los ojos, ojos")
comun.comprobar(bustups.partir_nombre("quien-guaidaofu-benti-lunkuo_2", "quien", "guaidaofu")
                == ("base", "lunkuo_2"),
                "una copia del contorno NO se toma por la cara de una expresion")
comun.comprobar(bustups.partir_nombre("quien-changfu-benti-tongchang", "quien", "changfu")
                == ("tongchang", "cara"),
                "y la cara de verdad (benti-<gesto>) se sigue reconociendo")

# --------------------------------------------------------------------------- 8) el shader de dialogo
# Los parametros van empaquetados en `datos/shaders.json` (los 120 retratos) y el sombreado los aplica
# sin numpy, con una tabla por nivel de coordenada. Dos cosas que se comprueban aqui porque ya se
# equivocaron una vez: las paradas del degradado son las del JSON (no una reconstruccion equiespaciada,
# que solo vale para degradados de 2 paradas) y el tono del degradado se recorta, que es lo que evita
# el tono amarillo tostado de los personajes con GraSaturation/GraContrast altos.
emparejados = bustups.emparejado()["emparejados"]
con_shader = [k for k in emparejados if sombreado.parametros(k)]
comun.comprobar(len(con_shader) >= 120,  # solo ~124 de 266 tienen shader JSON propio  # los P3R no tienen shader JSON propio
                "los %d retratos tienen sus parametros de shader (%d)" % (len(emparejados), len(con_shader)))
comun.comprobar(sombreado.parametros("UI-DialogShader-no-existe") is None,
                "y una clave que no existe no los tiene")

CLAVE_SHADER = "UI-DialogShader-changfu01-xiachuanling"
PARAMS = sombreado.parametros(CLAVE_SHADER)
comun.comprobar(bool(PARAMS), "la clave de la captura del juego tiene parametros (%s)" % CLAVE_SHADER)
if PARAMS:
    comun.comprobar(2 <= len(PARAMS["paradas"]) <= 8,
                    "el degradado trae sus paradas del JSON (%d)" % len(PARAMS["paradas"]))
    comun.comprobar(all(0.0 <= t <= 1.0 for t, _ in PARAMS["paradas"]),
                    "y sus tiempos estan en 0..1")
    comun.comprobar(0.0 <= PARAMS["alfa_pos_abajo"] <= PARAMS["alfa_pos_arriba"] <= 1.0,
                    "la rampa de alfa va de menos a mas")
    comun.comprobar(abs(PARAMS["alfa_pos_abajo"] - 0.0) < 1e-9
                    and abs(PARAMS["alfa_pos_arriba"] - 1.0) < 1e-9,
                    "la rampa de alfa va de 0 a 1: son las posiciones que escribe el codigo del juego"
                    " (GameAssembly.dll, UIMultipleMaterial.Update RVA 0x23C3DA0), no las paradas del JSON")
    comun.comprobar(0.0 <= PARAMS["alfa_abajo"] <= PARAMS["alfa_arriba"] <= 1.0,
                    "los valores siguen siendo GradientAlphaBottom/Top, en 0..1")
    TABLAS = sombreado.tablas_degradado(PARAMS)
    comun.comprobar(TABLAS is not None and len(TABLAS) == 4, "el degradado da sus tablas")
    if TABLAS:
        col_r, col_g, col_b, rampa = TABLAS
        comun.comprobar(all(len(t) == sombreado.NIVELES for t in TABLAS),
                        "una entrada por nivel de coordenada (%d)" % sombreado.NIVELES)
        comun.comprobar(sombreado.TOPE is False,
                        "el tono del degradado NO se recorta a 0..1: el GLSL no lo hace, y el"
                        " recorte era un parche que tapaba la rampa de alfa mal puesta")
        comun.comprobar(all(0.0 <= v <= 1.0 for v in rampa), "y la rampa de alfa si esta en 0..1")

# el retrato sombreado se guarda aparte del limpio, para poder alternar en el visor
comun.comprobar(sombreado.disponible(CLAVE_SHADER), "el visor puede pedir el retrato con shader")

comun.resumen()
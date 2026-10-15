"""La herramienta tiene que valer para las DOS versiones del juego.

La china instala los bundles en `Client/OuterPackage/Bundles/Windows` (con C mayuscula, bajo la
carpeta que elige el usuario) y la global los pone en `client/OuterPackage/Bundles/Windows`, dentro
de `steamapps/common/P5X` de Steam. Aqui se comprueban las dos, con carpetas de mentira: la prueba
no depende de que el juego este instalado en este equipo.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="p5x_versiones_"))


def _juego(nombre, sub):
    """Crea una carpeta de juego de mentira con esa subruta de bundles dentro."""
    raiz = TMP / nombre
    (raiz / sub).mkdir(parents=True, exist_ok=True)
    return raiz


# --------------------------------------------------------------------- 1) las dos subrutas conocidas
china = _juego("china", "Client/OuterPackage/Bundles/Windows")
global_ = _juego("global", "client/OuterPackage/Bundles/Windows")
suelta = _juego("suelta", "OuterPackage/Bundles/Windows")

comun.comprobar(ajustes.subruta_bundles(china) == Path("Client/OuterPackage/Bundles/Windows"),
                "la version china se reconoce por `Client/OuterPackage/Bundles/Windows`")
comun.comprobar(ajustes.subruta_bundles(global_) == Path("client/OuterPackage/Bundles/Windows"),
                "la global (Steam) se reconoce por `client/OuterPackage/Bundles/Windows`")
comun.comprobar(ajustes.subruta_bundles(suelta) is not None,
                "tambien vale una instalacion que cuelga `OuterPackage` de la raiz")
comun.comprobar(ajustes.subruta_bundles(TMP / "no_es_el_juego") is None,
                "una carpeta cualquiera NO se confunde con el juego")

# ------------------------------------------------------- 2) elegir la carpeta del juego o la de bundles
raiz, bundles = ajustes.resolver_carpeta_juego(global_)
comun.comprobar(raiz == global_ and bundles == global_ / "client/OuterPackage/Bundles/Windows",
                "se acepta la carpeta del juego de la version global")

# el usuario puede senalar la propia carpeta de bundles: en Windows `client` y `Client` son la misma
# carpeta, pero en Python no, asi que la comparacion tiene que ir sin distinguir mayusculas
raiz2, bundles2 = ajustes.resolver_carpeta_juego(global_ / "client/OuterPackage/Bundles/Windows")
comun.comprobar(raiz2 == global_ and bundles2 is not None,
                "se acepta la carpeta de bundles de la global (con `client` en minuscula)")

raiz3, bundles3 = ajustes.resolver_carpeta_juego(china / "Client/OuterPackage/Bundles/Windows")
comun.comprobar(raiz3 == china and bundles3 is not None,
                "y la de la china (con `Client` en mayuscula)")

comun.comprobar(ajustes.resolver_carpeta_juego(TMP / "no_es_el_juego") == (None, None),
                "una carpeta que no es del juego se rechaza")

# ------------------------------------------------------------- 3) los sitios donde se busca el juego
bibliotecas = ajustes._bibliotecas_steam()
comun.comprobar(len(bibliotecas) == len({str(b).lower() for b in bibliotecas}),
                "las bibliotecas de Steam no se repiten")
comun.comprobar(all(str(b).lower().endswith("common") for b in bibliotecas),
                "cada biblioteca de Steam acaba en `steamapps/common`")

candidatos = [str(c).lower() for c in ajustes._candidatos_juego()]
comun.comprobar(any("steamapps" in c and c.endswith("p5x") for c in candidatos),
                "la carpeta del juego de Steam esta entre los candidatos")
comun.comprobar(len(candidatos) == len(set(candidatos)),
                "los candidatos no se repiten")

# la carpeta del juego guardada en la configuracion manda sobre la busqueda automatica
original = ajustes._leer_config
try:
    ajustes._leer_config = lambda: {"carpeta_juego": str(global_)}
    comun.comprobar(ajustes.detectar_juego() == global_,
                    "si el usuario ya fijo la carpeta, se respeta")
    ajustes._leer_config = lambda: {"carpeta_juego": str(TMP / "ya_no_esta")}
    detectado = ajustes.detectar_juego()
    comun.comprobar(detectado is None or detectado != TMP / "ya_no_esta",
                    "si la carpeta fijada ya no existe, se busca de nuevo en vez de fallar")
finally:
    ajustes._leer_config = original

import shutil  # noqa: E402
shutil.rmtree(TMP, ignore_errors=True)
comun.resumen()
"""Exporta bundles a un proyecto de Unity usando AssetRipper en modo headless (API HTTP).

Uso:  python assetripper_export.py <carpeta_con_bundles> <carpeta_destino> [puerto]

Levanta AssetRipper como servidor, espera a que responda, reinicia el estado, carga la carpeta
y lanza la exportacion del proyecto de Unity, sondeando el log hasta que termine.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

RAIZ = r"C:\Users\Lukas\p5x-datamining"
EXE = os.path.join(RAIZ, "tools", "AssetRipper13", "AssetRipper.GUI.Free.exe")


def post(base, ruta, params=None, timeout=600):
    """AssetRipper lee los parametros como formulario (application/x-www-form-urlencoded),
    no como query string: con la query devuelve 'Incorrect Content-Type' y no hace nada."""
    url = base + ruta
    datos = urllib.parse.urlencode(params).encode() if params else b""
    req = urllib.request.Request(url, data=datos or None, method="POST")
    if datos:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        cuerpo = r.read().decode("utf-8", "replace")
        return r.status, cuerpo


def esperar(base, segundos=180):
    t0 = time.time()
    while time.time() - t0 < segundos:
        try:
            with urllib.request.urlopen(base + "/", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def main():
    entrada = sys.argv[1]
    salida = sys.argv[2]
    puerto = int(sys.argv[3]) if len(sys.argv) > 3 else 57973
    base = f"http://127.0.0.1:{puerto}"
    print(f"entrada : {entrada}")
    print(f"salida  : {salida}")
    os.makedirs(salida, exist_ok=True)

    proc = subprocess.Popen([EXE, "--headless", "--port", str(puerto)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"AssetRipper lanzado (pid {proc.pid}); esperando a que escuche en {base} ...")
    try:
        if not esperar(base):
            print("ERROR: AssetRipper no respondio")
            return 1
        print("escuchando. Reiniciando estado...")
        print("  /Reset ->", post(base, "/Reset", timeout=120))
        print("Cargando carpeta...")
        print("  /LoadFolder ->", post(base, "/LoadFolder", {"path": entrada}, timeout=3600))
        print("Exportando proyecto de Unity... (esto tarda)")
        print("  /Export/UnityProject ->", post(base, "/Export/UnityProject", {"path": salida},
                                              timeout=7200))
        print("exportacion terminada")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
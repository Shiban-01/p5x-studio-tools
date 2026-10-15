"""Piloto para manejar un .exe YA CONGELADO por el protocolo de depuracion de WebView2 (CDP).

Por que existe: al .exe publicado no se le puede inyectar JavaScript como al codigo fuente, asi que
hasta ahora solo se podia comprobar por fuera (capturas) o de refilon (autotest). Con esto se pulsa
lo que pulsa un usuario -el boton de dependencias, el de extraer- y se lee lo que sale en pantalla,
en el ejecutable de verdad.

Se usa asi:
    with Piloto(puerto=9222) as p:
        p.js("document.querySelector('#deps-open').click()")
        print(p.texto("#deps-consola"))
"""
from __future__ import annotations

import json
import time
import urllib.request

import websocket


class Piloto:
    def __init__(self, puerto: int = 9222, espera: float = 40.0):
        self.puerto = puerto
        self.ws = None
        self._id = 0
        objetivo = self._buscar_objetivo(espera)
        # suppress_origin: Chromium rechaza (403) las conexiones que traen cabecera Origin propia
        # salvo que se le pase --remote-allow-origins. Sin cabecera, la acepta.
        self.ws = websocket.create_connection(objetivo, timeout=60, suppress_origin=True)
        self._esperar_pagina()

    def _esperar_pagina(self, espera: float = 60.0) -> None:
        """Espera a que la pagina este cargada de verdad.

        Chromium crea el objetivo en `about:blank` y navega despues: si se pregunta enseguida,
        `document.title` esta vacio y no hay ni un solo elemento. No es que la app falle, es que se
        le pregunta antes de que exista.
        """
        t0 = time.time()
        while time.time() - t0 < espera:
            try:
                listo = self.js("document.readyState === 'complete' && document.title !== ''", timeout=20)
            except Exception:  # noqa: BLE001
                listo = False
            if listo:
                return
            time.sleep(1)

    # ------------------------------------------------------------------ conexion
    def _buscar_objetivo(self, espera: float) -> str:
        """Direccion websocket de la pagina, esperando a que la ventana exista."""
        t0 = time.time()
        ultimo = ""
        while time.time() - t0 < espera:
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json" % self.puerto, timeout=5) as r:
                    for t in json.load(r):
                        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                            return t["webSocketDebuggerUrl"]
            except Exception as e:  # noqa: BLE001
                ultimo = str(e)
            time.sleep(1)
        raise RuntimeError("no encontre la ventana que depurar (%s)" % ultimo)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.cerrar()

    def cerrar(self):
        try:
            self.ws.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ hablar con la pagina
    def js(self, expresion: str, timeout: float = 60.0):
        """Evalua JavaScript en la ventana y devuelve el valor."""
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": "Runtime.evaluate", "params": {
            "expression": expresion, "returnByValue": True, "awaitPromise": True}}))
        limite = time.time() + timeout
        while time.time() < limite:
            datos = json.loads(self.ws.recv())
            if datos.get("id") != mid:
                continue
            if "error" in datos:
                raise RuntimeError(datos["error"])
            res = datos.get("result", {}).get("result", {})
            if res.get("subtype") == "error":
                raise RuntimeError(res.get("description"))
            return res.get("value")
        raise TimeoutError("la ventana no contesto a: %s" % expresion[:80])

    # ------------------------------------------------------------------ atajos de lectura
    def texto(self, selector: str) -> str:
        return self.js("(document.querySelector(%r)||{}).textContent || ''" % selector) or ""

    def visible(self, selector: str) -> bool:
        # rect en vez de offsetParent: los elementos con position:fixed (el modal, sin ir mas lejos)
        # tienen offsetParent === null aunque se vean perfectamente.
        return bool(self.js("(() => { const e=document.querySelector(%r); if(!e || e.hidden) return false; "
                            "const r=e.getBoundingClientRect(); return r.width>0 && r.height>0; })()"
                            % selector))

    def pulsar(self, selector: str) -> bool:
        return bool(self.js("(() => { const e=document.querySelector(%r); if(!e) return false; "
                            "e.click(); return true; })()" % selector))

    def filas(self, selector: str) -> int:
        return int(self.js("document.querySelectorAll(%r).length" % selector) or 0)

    def esperar_texto(self, selector: str, trozo: str, timeout: float = 900.0,
                      cada: float = 3.0) -> bool:
        """Espera a que un elemento contenga un texto (para 'ya esta' / 'fin')."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if trozo.lower() in self.texto(selector).lower():
                return True
            time.sleep(cada)
        return False

    def errores_js(self) -> list:
        return self.js("window.__errs || []") or []

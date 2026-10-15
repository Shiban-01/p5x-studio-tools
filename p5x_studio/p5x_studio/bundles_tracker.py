"""Detección de bundles nuevos y modificados tras updates del juego."""
import json, time
from pathlib import Path

_RUTA = Path(__file__).parent.parent / "_dl" / "bundles_conocidos.json"

def _snapshot() -> dict:
    if _RUTA.exists():
        return json.loads(_RUTA.read_text(encoding="utf-8"))
    return {}

def _guardar(snap: dict) -> None:
    _RUTA.parent.mkdir(parents=True, exist_ok=True)
    _RUTA.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")

def comparar(bundles: list[dict]) -> dict:
    """Compara la lista de bundles actuales con el snapshot guardado.
    Devuelve {'nuevos': [...], 'modificados': [...], 'eliminados': [...], ...}"""
    snap = _snapshot()
    actuales = {}
    for b in bundles:
        ruta = b.get("ruta") or b.get("fichero") or ""
        if ruta:
            actuales[ruta] = {
                "id": b.get("id", ""),
                "tipo": b.get("tipo", ""),
                "mb": b.get("mb", 0),
                "fichero": b.get("fichero", ""),
            }

    if not snap:
        _guardar(actuales)
        return {"hay_base": False, "nuevos": [], "modificados": [], "eliminados": [],
                "n_nuevos": 0, "n_modificados": 0, "n_eliminados": 0, "n_total": len(actuales)}

    nuevos = sorted(r for r in actuales if r not in snap)
    eliminados = sorted(r for r in snap if r not in actuales)
    modificados = sorted(
        r for r in actuales if r in snap and actuales[r].get("mb") != snap[r].get("mb")
    )

    return {
        "hay_base": True,
        "nuevos": nuevos,
        "modificados": modificados,
        "eliminados": eliminados,
        "n_nuevos": len(nuevos),
        "n_modificados": len(modificados),
        "n_eliminados": len(eliminados),
        "n_total": len(actuales),
    }

def marcar_vistos(bundles: list[dict]) -> int:
    """Guarda el estado actual como snapshot. Devuelve el total guardado."""
    actuales = {}
    for b in bundles:
        ruta = b.get("ruta") or b.get("fichero") or ""
        if ruta:
            actuales[ruta] = {
                "id": b.get("id", ""),
                "tipo": b.get("tipo", ""),
                "mb": b.get("mb", 0),
                "fichero": b.get("fichero", ""),
            }
    _guardar(actuales)
    return len(actuales)

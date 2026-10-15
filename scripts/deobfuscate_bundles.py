#!/usr/bin/env python3
"""P5X bundle deobfuscator (port de P5XBundleDeobfuscate de DeathChaos25, GPL-3.0).

Los bundles de P5X traen basura al inicio; el offset de basura se deriva del
nombre del archivo:  offset = hash(name) % 32 + 8   (hash polinomico base 131).

En el flujo normal NO necesitas esto: el paso 1 (P5X_vFileContentExtract) ya
desofusca los bundles al extraerlos. Usalo solo si consigues *.bundle por otra
via (ej. los "OuterPackage" descargados del CDN) y AssetStudio no los abre.

Uso:
    python deobfuscate_bundles.py <carpeta_con_bundles>
Reemplaza los archivos in-place (hace backup .orig solo si hace falta).
"""
import sys
from pathlib import Path

UNITYFS_MAGIC = b"UnityFS"  # 0x74449D35 little-endian int32 == 1953066581


def hash_code(s: str) -> int:
    num2 = 0
    for ch in s:
        num2 = (num2 * 131 + ord(ch)) & 0xFFFFFFFF
    return num2 & 0x7FFFFFFF


def obfuscate_offset(name: str) -> int:
    return hash_code(name) % 32 + 8


def fix(path: Path) -> str:
    data = path.read_bytes()
    off = obfuscate_offset(path.name)
    # buscar el magic UnityFS a partir del offset esperado (y en una ventana corta)
    idx = data.find(UNITYFS_MAGIC, off, off + 8)
    if idx == -1:
        idx = data.find(UNITYFS_MAGIC)
    if idx == -1:
        return "skip (no UnityFS)"
    if idx == 0:
        return "ya limpio"
    path.write_bytes(data[idx:])
    if not path.with_suffix(path.suffix + ".orig").exists():
        path.with_suffix(path.suffix + ".orig").write_bytes(data)
    return f"limpiado (se quitaron {idx} bytes)"


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    bundles = [p for p in root.rglob("*.bundle*") if p.is_file() and not p.name.endswith(".orig")]
    print(f"{len(bundles)} archivos candidates en {root}")
    for p in bundles:
        try:
            print(f"  {p.name}: {fix(p)}")
        except Exception as e:  # noqa: BLE001
            print(f"  {p.name}: ERROR {e}")


if __name__ == "__main__":
    main()

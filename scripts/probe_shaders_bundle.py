"""Inspecciona shaders.bundle: que contiene y si los Shader salen como assets utilizables."""
import os
from collections import Counter
from pathlib import Path

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
BUNDLES = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
TIPO = {48: "Shader", 21: "Material", 28: "Texture2D", 49: "TextAsset",
        74: "AnimationClip", 83: "AudioClip", 43: "Mesh", 114: "MonoBehaviour"}


def encontrar(nombre: str, base=None):
    if base:
        for dirpath, _d, files in os.walk(base):
            if nombre in files:
                return Path(dirpath) / nombre
        return None
    for dirpath, _d, files in os.walk(BUNDLES):
        if nombre in files:
            return Path(dirpath) / nombre
    return None


def main():
    p = encontrar("shaders.bundle")
    if not p:
        print("no encontrado")
        return
    print(f"{p.name}: {p.stat().st_size / 1e6:.2f} MB")
    env = UnityPy.load(str(p))
    tipos = Counter()
    nombres = []
    for obj in env.objects:
        tipos[obj.type.name] += 1
        if obj.type.name in ("Shader", "TextAsset", "Material"):
            try:
                d = obj.read()
                nombres.append((obj.type.name, getattr(d, "m_Name", getattr(d, "name", "?"))))
            except Exception as e:  # noqa: BLE001
                nombres.append((obj.type.name, f"<error {type(e).__name__}>"))
    print("tipos:", dict(tipos))
    for t, n in nombres[:40]:
        print(f"  {t:12} {n}")
    print(f"total objetos: {sum(tipos.values())}")


if __name__ == "__main__":
    main()
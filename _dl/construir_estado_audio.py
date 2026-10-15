"""Construye el cache `estado_audio_video.json` (stem -> estado de audio) para el distintivo
de la lista de videos. Sin rutas absolutas: solo el estado y datos del banco.

Estados: "audio" (pista con sonido), "silencio" (la pista existe pero es silencio) y "mudo"
(no hay cue/pista emparejada). Usa las MISMAS funciones que la app (herramientas.buscar_audio_video
y _wav_es_silencio) para que el distintivo coincida con lo que hace la extraccion.
"""
from __future__ import annotations
import json, sys, time, subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent            # _dl
PROY = RAIZ.parent / "p5x_studio"
sys.path.insert(0, str(PROY))
from p5x_studio import herramientas as H  # noqa: E402


def decodifica_y_mira_silencio(vgm, acb, subsong, wav):
    r = subprocess.run(vgm + ["-s", str(subsong), "-o", str(wav), acb],
                       capture_output=True, text=True, timeout=600,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0 or not wav.is_file():
        return None
    return H._wav_es_silencio(wav)


def main():
    t0 = time.time()
    media = H.listar_media()
    usm = media["usm"]
    print("videos .usm:", len(usm))
    vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
    print("vgmstream:", bool(vgm))
    tmp = RAIZ / "_tmp_badge"
    tmp.mkdir(exist_ok=True)
    salida = {}
    n_audio = n_silencio = n_mudo = 0
    for i, m in enumerate(usm, 1):
        stem = Path(m["nombre"]).stem
        info = H.buscar_audio_video(m["ruta"])
        if not info:
            salida[stem] = {"estado": "mudo"}
            n_mudo += 1
        else:
            wav = tmp / (stem + ".wav")
            silencio = decodifica_y_mira_silencio(vgm, info["acb"], info["subsong"], wav)
            try:
                wav.unlink()
            except OSError:
                pass
            if silencio is None:
                estado = "silencio" if False else "error"
            elif silencio:
                estado = "silencio"; n_silencio += 1
            else:
                estado = "audio"; n_audio += 1
            salida[stem] = {"estado": estado, "banco": info["banco"],
                            "cue": info["cue"], "pista": info["pista"],
                            "segundos": info["segundos"]}
        if i % 25 == 0:
            print("  %d/%d  (%.1fs)" % (i, len(usm), time.time() - t0))
    (RAIZ / "estado_audio_video.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("audio=%d silencio=%d mudo=%d  total=%d  en %.1fs"
          % (n_audio, n_silencio, n_mudo, len(salida), time.time() - t0))


if __name__ == "__main__":
    main()

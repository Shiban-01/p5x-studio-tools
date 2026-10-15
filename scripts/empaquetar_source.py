"""Empaqueta el modelo de Kotone como mod de Source para L4D2 (VPK) y Garry's Mod (GMA).

Genera ademas la malla de fisica (una caja por hueso, para el ragdoll) y compila la version de
Garry's Mod, que va en models/player.

Uso: python empaquetar_source.py
"""
import os
import shutil
import struct
import subprocess
import sys
import zlib

RAIZ = r"C:\Users\Lukas\p5x-datamining\kotone_source"
GAMEDIR = os.path.join(RAIZ, "gamedir")
BUILD = os.path.join(RAIZ, "build")
STUDIOMDL = r"C:\Program Files (x86)\Steam\steamapps\common\Portal 2 Community Edition\bin\win64\studiomdl.exe"
VPKEXE = r"C:\Program Files (x86)\Steam\steamapps\common\Portal\bin\vpk.exe"

TITULO = "Kotone Shiomi (Persona 5: The Phantom X)"
AUTOR = "Lukas"
VERSION = "1.0"
DESCRIPCION = ("Kotone Shiomi de Persona 5: The Phantom X como superviviente de Left 4 Dead 2 "
               "(reemplaza a Rochelle). Esqueleto ValveBiped, arma en la mano y cajas de impacto.")


# --------------------------------------------------------------------------- utilidades
def correr(cmd, log):
    with open(log, "w") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    texto = open(log, encoding="utf-8", errors="replace").read()
    return p.returncode, texto


def fisica_smd(destino):
    """Malla de fisica: una caja por hueso, con los vertices al 100% de ese hueso.

    Se usan las mismas cajas que los hitboxes. Es mucho mas rapido (y el .phy sale infinitamente
    mas pequeno) que darle a studiomdl los 21.000 triangulos del cuerpo.
    """
    cajas = {}
    for l in open(os.path.join(BUILD, "kotone_l4d2.qc"), encoding="utf-8"):
        if l.startswith("$hbox "):
            v = l.split()
            hueso = v[2].strip('"')          # en el .qc el nombre va entre comillas
            cx, cy, cz, tx, ty, tz = [float(x) for x in v[3:9]]
            cajas[hueso] = (cx, cy, cz, tx / 2, ty / 2, tz / 2)
    nodos = [l.split('"')[1] for l in open(os.path.join(BUILD, "Kotone_Shiomi.smd"), encoding="utf-8")
             if l.strip().startswith(tuple("0123456789")) and '"' in l]
    nombres = []
    for l in open(os.path.join(BUILD, "Kotone_Shiomi.smd"), encoding="utf-8"):
        if '"' in l and l.split()[0].isdigit() and "ValveBiped" in l:
            nombres.append(l.split('"')[1])
    esqueleto = []
    dentro = False
    for l in open(os.path.join(BUILD, "Kotone_Shiomi.smd"), encoding="utf-8"):
        if l.strip() == "skeleton":
            dentro = True
            continue
        if l.strip() == "end" and dentro:
            break
        if dentro and l.strip() and not l.startswith("time"):
            esqueleto.append(l.strip())

    out = ["version 1", "nodes"]
    for i, n in enumerate(nombres):
        padre = -1
        out.append('%d "%s" %d' % (i, n, padre))
    # el padre real lo copiamos del SMD original para que la jerarquia sea la misma
    padres = {}
    for l in open(os.path.join(BUILD, "Kotone_Shiomi.smd"), encoding="utf-8"):
        v = l.split()
        if len(v) >= 3 and v[0].isdigit() and '"' in l:
            padres[v[0]] = v[-1]
    out = ["version 1", "nodes"]
    for i, n in enumerate(nombres):
        out.append('%d "%s" %d' % (i, n, int(padres.get(str(i), -1))))
    out.append("end")
    out.append("skeleton")
    out.append("time 0")
    out.extend(esqueleto)
    out.append("end")
    out.append("triangles")
    for i, nombre in enumerate(nombres):
        if nombre not in cajas:
            continue
        cx, cy, cz, hx, hy, hz = cajas[nombre]
        esquinas = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    esquinas.append((cx + sx * hx, cy + sy * hy, cz + sz * hz))
        caras = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
                 (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
        for cara in caras:
            # el nombre del material va antes de cada triangulo, igual que en la malla: si se
            # escribe una sola vez, studiomdl cuenta las lineas de vertice como materiales y aborta.
            # Se usa body01 (que existe, y su $surfaceprop es flesh) para que la fisica herede
            # la superficie correcta del cuerpo.
            out.append("body01")
            for k in cara:
                x, y, z = esquinas[k]
                out.append("%d %.4f %.4f %.4f 0 0 1 0 0 1 %d 1.0" % (i, x, y, z, i))
    out.append("end")
    open(destino, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    emitidas = sum(1 for n in nombres if n in cajas)
    if emitidas == 0:
        raise SystemExit("la malla de fisica saldria vacia: los nombres de los $hbox no coinciden "
                         "con los huesos del SMD")
    print("   cajas emitidas: %d de %d huesos (12 triangulos cada una)" % (emitidas, len(nombres)))
    return emitidas


def qc_fisica():
    """Anade a un .qc las lineas de collisionjoints para el ragdoll."""
    cajas = []
    for l in open(os.path.join(BUILD, "kotone_l4d2.qc"), encoding="utf-8"):
        if l.startswith("$hbox "):
            v = l.split()
            cajas.append(v[2].strip('"'))
    lineas = ['$collisionjoints "fisica.smd"',
              "{", "\t$mass 70", "\t$inertia 1", "\t$damping 0.05", "\t$rotdamping 1.5",
              "\t$rootbone \"ValveBiped.Bip01_Pelvis\""]
    for hueso in cajas:
        if hueso.endswith("Pelvis"):
            continue
        lineas.append('\t$jointconstrain "%s" x limit -35 35 0' % hueso)
        lineas.append('\t$jointconstrain "%s" y limit -35 35 0' % hueso)
        lineas.append('\t$jointconstrain "%s" z limit -35 35 0' % hueso)
    lineas.append("}")
    return "\n".join(lineas)


def vpk(destino):
    """Crea el VPK de L4D2 en version 1, que es el formato de todo lo que el juego carga.

    El vpk.exe de Valve escribe version 2 (comprobado con el de Portal y con el de Portal 2 CE),
    mientras que el pak01 del propio juego y los 37 VPK del taller del usuario son version 1.
    Se escribe con scripts/escribir_vpk.py, que hace version 1 y esta verificado contra ellos.
    """
    salida = os.path.join(RAIZ, "kotone_shiori_l4d2.vpk")
    p = subprocess.run([sys.executable, os.path.join(RAIZ, "..", "scripts", "escribir_vpk.py"),
                        destino, salida], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def gma(carpeta, destino, nombre, descripcion, autor, version=3):
    """Escribe un .gma de Garry's Mod. Formato: cabecera GMAD, nombres, directorio y datos."""
    archivos = []
    for base, _, ficheros in os.walk(carpeta):
        for f in ficheros:
            completo = os.path.join(base, f)
            rel = os.path.relpath(completo, carpeta).replace("\\", "/")
            archivos.append((rel, os.path.getsize(completo), completo))
    archivos.sort()
    cabecera = b"GMAD" + struct.pack("<B", version) + struct.pack("<Q", 0) + \
        struct.pack("<Q", int(os.path.getmtime(carpeta))) + b"\x00"
    cabecera += nombre.encode() + b"\x00" + descripcion.encode() + b"\x00" + autor.encode() + b"\x00"
    cabecera += struct.pack("<I", 1)
    directorio = b""
    for i, (rel, tam, _) in enumerate(archivos, start=1):
        crc = zlib.crc32(open(_ , "rb").read()) & 0xFFFFFFFF
        directorio += struct.pack("<I", i) + rel.encode() + b"\x00" + struct.pack("<Q", tam) + struct.pack("<I", crc)
    directorio += struct.pack("<I", 0)
    with open(destino, "wb") as f:
        f.write(cabecera)
        f.write(directorio)
        for _, _, completo in archivos:
            f.write(open(completo, "rb").read())
        f.flush()
        f.seek(0)
        todo = f.read() if False else None
    # crc final sobre todo lo escrito hasta ahora
    datos = open(destino, "rb").read()
    with open(destino, "ab") as f:
        f.write(struct.pack("<I", zlib.crc32(datos) & 0xFFFFFFFF))
    return archivos


def main():
    print("=== 0) copiar las fuentes nuevas al gamedir ===")
    # OJO: studiomdl compila desde gamedir/modelsrc, no desde build/. Si no se copian, sigue
    # usando las fuentes de una compilacion anterior y TODAS las correcciones del SMD y del .qc se
    # pierden en silencio: el compilador dice "Completed" y el .mdl sale como antes. Me paso: el
    # SMD quedo congelado en la version de las 18:14 y los arreglos del esqueleto no llegaban.
    for f in ("Kotone_Shiomi.smd", "idle.smd", "kotone_l4d2.qc", "kotone_gmod.qc"):
        origen = os.path.join(BUILD, f)
        if os.path.exists(origen):
            shutil.copy2(origen, os.path.join(GAMEDIR, "modelsrc", f))
            print("   copiado: %s (%d bytes)" % (f, os.path.getsize(origen)))

    print("=== 1) malla de fisica ===")
    n = fisica_smd(os.path.join(GAMEDIR, "modelsrc", "fisica.smd"))

    print("=== 2) compilar L4D2 (con ragdoll) ===")
    # con SIN_ANIM=1 se compila sin $includemodel: sirve para separar un problema de animaciones
    # de cualquier otro. Las animaciones solo funcionan si el esqueleto es identico al del juego.
    incluir_anim = not os.environ.get("SIN_ANIM")
    # con SIN_FISICA=1 se compila sin $collisionjoints: para separar la fisica del resto
    incluir_fisica = not os.environ.get("SIN_FISICA")
    qc = open(os.path.join(BUILD, "kotone_l4d2.qc"), encoding="utf-8").read()
    abierto = open(os.path.join(GAMEDIR, "modelsrc", "kotone_l4d2_fisica.qc"), "w", encoding="utf-8", newline="\n")
    abierto.write(qc + "\n" + (qc_fisica() + "\n" if incluir_fisica else ""))
    # Las animaciones del superviviente no van dentro del modelo: el juego las reparte en
    # anim_<personaje>.mdl y anim_gestures.mdl, y el modelo las incluye. Comprobado leyendo el
    # survivor_producer.mdl del propio juego, que cita exactamente esos dos ficheros. Sin esto el
    # modelo sale congelado en partida.
    if incluir_anim:
        abierto.write('\n$includemodel "survivors/anim_producer.mdl"\n'
                      '$includemodel "survivors/anim_gestures.mdl"\n')
    abierto.close()
    rc, texto = correr([STUDIOMDL, "-nop4", "-game", GAMEDIR,
                        os.path.join(GAMEDIR, "modelsrc", "kotone_l4d2_fisica.qc")],
                       os.path.join(RAIZ, "..", "_dl", "source", "studiomdl_fisica.log"))
    print("   exit:", rc, "| linea final:", texto.strip().splitlines()[-1][:100] if texto.strip() else "?")
    if rc != 0 or "Completed" not in texto:
        print("   el ragdoll fallo, se sigue con el modelo sin fisica")
        abierto = open(os.path.join(GAMEDIR, "modelsrc", "kotone_l4d2_fisica.qc"), "w", encoding="utf-8", newline="\n")
        abierto.write(qc)
        # OJO: antes esto iba sin condicion y colaba las animaciones aunque se pidiera SIN_ANIM,
        # con lo que la prueba de aislamiento medía otra cosa. Va condicionado.
        if incluir_anim:
            abierto.write('\n$includemodel "survivors/anim_producer.mdl"\n'
                          '$includemodel "survivors/anim_gestures.mdl"\n')
        abierto.close()
        correr([STUDIOMDL, "-nop4", "-game", GAMEDIR,
                os.path.join(GAMEDIR, "modelsrc", "kotone_l4d2_fisica.qc")],
               os.path.join(RAIZ, "..", "_dl", "source", "studiomdl_sin_fisica.log"))
    for err in ("physics", "error", "ERROR"):
        for l in texto.splitlines():
            if err in l.lower() and ("error" in l.lower() or "too" in l.lower()):
                print("   aviso:", l[:120])
                break

    print("=== 3) compilar Garry's Mod ===")
    gqc = os.path.join(GAMEDIR, "modelsrc", "kotone_gmod.qc")
    texto_gqc = open(gqc, encoding="utf-8").read()
    if incluir_fisica and "$collisionjoints" not in texto_gqc:
        # el modelo de GMod tambien lleva fisica: sin .phy no hay ragdoll al morir
        open(gqc, "w", encoding="utf-8", newline="\n").write(texto_gqc + "\n" + qc_fisica() + "\n")
    rc, texto = correr([STUDIOMDL, "-nop4", "-game", GAMEDIR, gqc],
                       os.path.join(RAIZ, "..", "_dl", "source", "studiomdl_gmod.log"))
    print("   exit:", rc, "|", texto.strip().splitlines()[-1][:100] if texto.strip() else "?")
    if not os.path.exists(os.path.join(GAMEDIR, "models", "player", "kotone", "kotone.phy")):
        print("   AVISO: el modelo de GMod se compilo sin .phy (no tendra ragdoll)")

    print("=== 4) addon de L4D2 ===")
    # Si se compilo sin $collisionjoints, el .phy que haya en gamedir es el de una compilacion
    # ANTERIOR: studiomdl no lo regenera. Colarlo en el paquete deja un .phy cuyo checksum no
    # coincide con el del .mdl, y el motor exige que coincidan. Se borra para no empaquetar basura.
    if not incluir_fisica:
        sobrante = os.path.join(GAMEDIR, "models", "survivors", "survivor_producer.phy")
        if os.path.exists(sobrante):
            os.remove(sobrante)
            print("   (sin fisica: quitado el .phy sobrante de la compilacion anterior)")
    addon = os.path.join(RAIZ, "l4d2_addon")
    if os.path.isdir(addon):
        shutil.rmtree(addon)
    os.makedirs(os.path.join(addon, "models", "survivors"))
    os.makedirs(os.path.join(addon, "materials", "models", "kotone"))
    for f in os.listdir(os.path.join(GAMEDIR, "models", "survivors")):
        shutil.copy2(os.path.join(GAMEDIR, "models", "survivors", f),
                     os.path.join(addon, "models", "survivors", f))
    for base, _, ficheros in os.walk(os.path.join(GAMEDIR, "materials", "models", "kotone")):
        for f in ficheros:
            shutil.copy2(os.path.join(base, f), os.path.join(addon, "materials", "models", "kotone", f))
    open(os.path.join(addon, "addoninfo.txt"), "w", encoding="utf-8", newline="\r\n").write(
        '"AddonInfo"\n{\n'
        '\t"addonSteamAppID"\t"550"\n'
        '\t"addontitle"\t"%s"\n'
        '\t"addonversion"\t"%s"\n'
        '\t"addonauthor"\t"%s"\n'
        '\t"addondescription"\t"%s"\n'
        '\t"addontagline"\t"Kotone Shiomi en Left 4 Dead 2"\n'
        '\t"addonTags"\t"Survivor;Replacement"\n'
        '}\n' % (TITULO, VERSION, AUTOR, DESCRIPCION))
    print("   contenido:")
    for base, _, ficheros in os.walk(addon):
        for f in sorted(ficheros):
            p = os.path.join(base, f)
            print("      %-52s %8.2f MB" % (os.path.relpath(p, addon), os.path.getsize(p) / 1e6))
    rc, salida = vpk(addon)
    print("   vpk exit:", rc, "|", salida.strip().replace("\n", " ")[:200])

    print("=== 5) addon de Garry's Mod ===")
    gmod = os.path.join(RAIZ, "gmod_addon")
    if os.path.isdir(gmod):
        shutil.rmtree(gmod)
    os.makedirs(os.path.join(gmod, "models", "player", "kotone"))
    os.makedirs(os.path.join(gmod, "materials", "models", "kotone"))
    os.makedirs(os.path.join(gmod, "lua", "autorun"))
    for f in os.listdir(os.path.join(GAMEDIR, "models", "player", "kotone")):
        shutil.copy2(os.path.join(GAMEDIR, "models", "player", "kotone", f),
                     os.path.join(gmod, "models", "player", "kotone", f))
    for base, _, ficheros in os.walk(os.path.join(GAMEDIR, "materials", "models", "kotone")):
        for f in ficheros:
            shutil.copy2(os.path.join(base, f), os.path.join(gmod, "materials", "models", "kotone", f))
    shutil.copy2(os.path.join(RAIZ, "lua", "autorun", "kotone_shiori.lua"),
                 os.path.join(gmod, "lua", "autorun", "kotone_shiori.lua"))
    archivos = gma(gmod, os.path.join(RAIZ, "kotone_shiori_gmod.gma"), TITULO, DESCRIPCION, AUTOR)
    print("   .gma con %d ficheros" % len(archivos))


if __name__ == "__main__":
    main()
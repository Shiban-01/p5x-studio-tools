import sys, subprocess, hashlib
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
tmp = Path(r"C:/Users/Lukas/p5x-datamining/_dl/_tmp_hash"); tmp.mkdir(parents=True, exist_ok=True)
def dec(acb,sub,tag):
    w=tmp/(tag+".wav")
    if w.exists(): w.unlink()
    r=subprocess.run(vgm+["-s",str(sub),"-o",str(w),str(acb)],capture_output=True,text=True,timeout=600)
    ex=w.is_file()
    h=hashlib.md5(w.read_bytes()).hexdigest() if ex else None
    sz=w.stat().st_size if ex else 0
    return h, sz, r.returncode, (r.stdout+r.stderr)[-120:].replace("\n"," ")
mdir=Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
for stem in ("CG_zx_Event_04_31_01_1","CG_yugao_1_3","gacha_first_00_new"):
    infos=H.buscar_audios_video(str(mdir/(stem+".usm")))
    print("###", stem)
    for k,i in enumerate(infos):
        h,sz,rc,msg=dec(Path(i["acb"]),i["subsong"],stem+"_%d"%k)
        print("  %-5s %-18s s%-2d %8.3fs  %s sz=%d rc=%d  %s" % (i["idioma"] or "base", i["banco"], i["subsong"], i["segundos"], h, sz, rc, msg if h is None else ""))

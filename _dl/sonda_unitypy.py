
import sys
from collections import Counter
import UnityPy

CASOS = [
    r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\106\shaders.bundle",
    r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\130\uitex_a-chouka23f26de7.bundle",
]
for ruta in CASOS:
    print("=" * 78)
    print(ruta.split("\\")[-1])
    env = UnityPy.load(ruta)
    print("objetos:", len(env.objects), dict(Counter(o.type.name for o in env.objects)))
    for obj in env.objects:
        if obj.type.name in ("Shader", "Material"):
            d = obj.read()
            print("  --- %s: %s" % (obj.type.name, getattr(d, "m_Name", "?")))
            if obj.type.name == "Material":
                try:
                    print("      shader:", getattr(d.m_Shader, "name", None) or d.m_Shader.path_id)
                    for grupo in ("m_SavedProperties",):
                        sp = getattr(d, grupo, None)
                        if sp:
                            for campo in ("m_TexEnvs", "m_Floats", "m_Colors", "m_Ints"):
                                v = getattr(sp, campo, None)
                                if v:
                                    print("      %s: %s" % (campo, str(v)[:300]))
                    print("      keywords:", getattr(d, "m_ShaderKeywords", None))
                except Exception as e:
                    print("      (no pude leer propiedades: %s)" % e)
            else:
                try:
                    pf = getattr(d, "m_ParsedForm", None)
                    print("      parsedForm:", "SI" if pf else "no")
                    if pf:
                        print("      props:", str(getattr(pf, "m_PropInfo", ""))[:200])
                    subs = getattr(d, "m_SubPrograms", None)
                    print("      subprogramas:", len(subs) if subs is not None else "?")
                except Exception as e:
                    print("      (error: %s)" % e)
        elif obj.type.name == "Texture2D":
            d = obj.read()
            if getattr(d, "m_Name", "").lower().startswith(("lihui", "renzhimoni", "moni")):
                ts = getattr(d, "m_TextureSettings", None)
                print("  TXT %-42s %sx%s  filtro=%s  srgb/colorspace=%s  mips=%s  formato=%s"
                      % (d.m_Name[:42], getattr(d, "m_Width", "?"), getattr(d, "m_Height", "?"),
                         getattr(ts, "m_FilterMode", "?"), getattr(d, "m_ColorSpace", "?"),
                         getattr(ts, "m_MipMap", "?"), getattr(d, "m_TextureFormat", "?")))

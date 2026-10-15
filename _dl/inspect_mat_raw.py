import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, rig_unitypy

carpeta = ajustes.carpeta_bundles()
rutas = ["032/role_pc077_01132c9d31.bundle", "089/shared_merged_3400dc06.bundle",
         "103/part_pc077_011eadf551.bundle"]
for r in rutas:
    env = rig_unitypy._abrir(carpeta / r)
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        m = obj.read()
        nom = getattr(m, "m_Name", "") or ""
        if nom in ("PC077_01_body", "PC077_01_body_01", "PC077_01_body_lodlow", "PC077_01_hair"):
            print("=== %s (bundle %s) shader=%r ===" % (nom, r, getattr(getattr(m, "m_Shader", None), "name", None)))
            try:
                for slot, te in m.m_SavedProperties.m_TexEnvs:
                    tn = None
                    err = None
                    try:
                        tn = te.m_Texture.read().m_Name
                    except Exception as e:
                        err = repr(e)
                    print("   slot=%-24s tex=%r err=%s" % (slot, tn, err))
            except Exception as e:
                print("   m_TexEnvs fallo:", repr(e))
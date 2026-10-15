import ast, os

PKG = r'C:\Users\Lukas\p5x-datamining\p5x_studio\p5x_studio'
mods = ["gui.py", "herramientas.py", "extractor.py", "catalogo.py", "bases.py", "trajes.py",
        "dependencias.py", "sesion_unity.py", "indice.py", "unity.py", "glb_rig.py", "clave.py",
        "fbx_blender.py", "ajustes.py", "idiomas.py"]


def nombres_llamados(nodo):
    """Nombres usados como funcion dentro de un ambito (incluyendo subambitos)."""
    usados = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            usados.add(n.func.id)
    return usados


for mod in mods:
    ruta = os.path.join(PKG, mod)
    src = open(ruta, encoding='utf-8').read()
    arbol = ast.parse(src)
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            continue
        llamados = nombres_llamados(nodo)
        # nombres que se reasignan con un valor (no funcion) en este ambito
        reasignados = {}
        cuerpo = nodo.body
        for i, sub in enumerate(cuerpo):
            obj = None
            if isinstance(sub, ast.Assign) and len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Name):
                obj = sub.targets[0]
            elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                obj = sub.target
            if obj is not None and obj.id in llamados:
                reasignados[obj.id] = getattr(sub, 'lineno', '?')
        # parametros que colisionan con un nombre llamado en el cuerpo
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ps = {a.arg for a in nodo.args.args + nodo.args.kwonlyargs + nodo.args.posonlyargs}
            for p in ps & llamados:
                reasignados.setdefault(p, 'param')
            # variables de bucle
            for sub in ast.walk(nodo):
                if isinstance(sub, (ast.For, ast.AsyncFor)) and isinstance(sub.target, ast.Name):
                    if sub.target.id in llamados:
                        reasignados.setdefault(sub.target.id, "for@%s" % sub.lineno)
                if isinstance(sub, ast.comprehension) and isinstance(sub.target, ast.Name):
                    if sub.target.id in llamados:
                        reasignados.setdefault(sub.target.id, "comp@%s" % sub.lineno)
        if reasignados:
            print(f"{mod}::{getattr(nodo,'name','<mod>')} -> {reasignados}")
print("=== fin barrido ===")

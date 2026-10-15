import ast, os

PKG = r'C:\Users\Lukas\p5x-datamining\p5x_studio\p5x_studio'
mods = ["gui.py", "herramientas.py", "extractor.py", "catalogo.py", "bases.py", "trajes.py",
        "dependencias.py", "sesion_unity.py", "indice.py", "unity.py", "glb_rig.py", "clave.py",
        "fbx_blender.py", "ajustes.py", "idiomas.py"]

# nombres importados o definidos a nivel de modulo (funciones)
for mod in mods:
    src = open(os.path.join(PKG, mod), encoding='utf-8').read()
    arbol = ast.parse(src)
    globales = set()
    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            globales.add(n.name)
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                globales.add(a.asname or a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                globales.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name):
                    globales.add(tg.id)

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        llamados = {c.func.id for c in ast.walk(nodo)
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        colisiones = {}
        # parametros
        ps = {a.arg for a in nodo.args.args + nodo.args.kwonlyargs + nodo.args.posonlyargs}
        for p in ps & llamados:
            colisiones[p] = "param"
        # bucles y asignaciones locales
        for sub in ast.walk(nodo):
            if isinstance(sub, (ast.For, ast.AsyncFor)) and isinstance(sub.target, ast.Name):
                if sub.target.id in llamados:
                    colisiones.setdefault(sub.target.id, "for@%d" % sub.lineno)
            if isinstance(sub, ast.Assign):
                for tg in sub.targets:
                    if isinstance(tg, ast.Name) and tg.id in llamados:
                        colisiones.setdefault(tg.id, "assign@%d" % sub.lineno)
            if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                if sub.target.id in llamados:
                    colisiones.setdefault(sub.target.id, "annassign@%d" % sub.lineno)
        if not colisiones:
            continue
        # separar: colisiones con nombres GLOBALES (funcion importada o de modulo) = sospechosas
        graves = {k: v for k, v in colisiones.items() if k in globales}
        if graves:
            print(f"*** {mod}::{nodo.name} PISA GLOBAL {graves}")
print("=== fin ===")

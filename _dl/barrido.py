import ast, os, sys

PKG = r'C:\Users\Lukas\p5x-datamining\p5x_studio\p5x_studio'
mods = ["gui.py", "herramientas.py", "extractor.py", "catalogo.py", "bases.py", "trajes.py",
        "dependencias.py", "sesion_unity.py", "indice.py", "unity.py", "glb_rig.py", "clave.py",
        "fbx_blender.py", "ajustes.py", "idiomas.py"]

# names that are callables/functions at module level
for mod in mods:
    ruta = os.path.join(PKG, mod)
    if not os.path.exists(ruta):
        print("FALTA", mod); continue
    src = open(ruta, encoding='utf-8').read()
    try:
        arbol = ast.parse(src)
    except SyntaxError as e:
        print("SYNTAX", mod, e); continue

    def funcs_en(nodo):
        return {n.name for n in ast.walk(nodo) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # module-level function names
    top_funcs = {n.name for n in arbol.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    # walk every scope: function defs and assignments in the same scope
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            fns = funcs_en(nodo)
            asignados = set()
            for sub in nodo.body:
                if isinstance(sub, ast.Assign):
                    for tg in sub.targets:
                        if isinstance(tg, ast.Name):
                            asignados.add(tg.id)
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    asignados.add(sub.target.id)
                elif isinstance(sub, (ast.For, ast.AsyncFor)):
                    tg = sub.target
                    if isinstance(tg, ast.Name):
                        asignados.add(tg.id)
                    # parameters can also shadow
            pisa = sorted(fns & asignados)
            if pisa:
                nombre = getattr(nodo, 'name', '<modulo>')
                print(f"{mod}::{nombre} pisa funciones: {pisa}")
    # also check function parameters shadowing other module functions
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = {a.arg for a in nodo.args.args + nodo.args.kwonlyargs + nodo.args.posonlyargs}
            if nodo.args.vararg: params.add(nodo.args.vararg.arg)
            if nodo.args.kwarg: params.add(nodo.args.kwarg.arg)
            choque = sorted(params & (top_funcs - {nodo.name}))
            if choque:
                print(f"{mod}::{nodo.name} parametro pisa funcion modulo: {choque}")
print("=== fin ===")

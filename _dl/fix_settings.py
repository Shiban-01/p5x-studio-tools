import re

p = "p5x_studio/ui_web/index.html"
c = open(p, encoding="utf-8").read()

# 1. Eliminar seccion de idioma de Settings
c = re.sub(r'<!-- Idioma -->.*?Interface language.*?</div>\s*</div>\s*</div>', '', c, flags=re.DOTALL)

# 2. Quitar Settings del nav
c = c.replace('\n      <button data-p="settings"><span class="ico">\u2699</span><span data-t="web_nav_settings">Settings</span></button>', '')

# 3. Poner Settings como boton pequeno antes del foot
old_foot = '<div class="foot" id="foot-index"'
new_foot = '<button class="settings-btn" data-p="settings" style="display:flex;align-items:center;gap:6px;margin:4px 8px;padding:6px 10px;background:var(--accent-pale);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-family:Nunito,sans-serif;font-size:10px;font-weight:700;color:var(--text2);transition:all .2s"><span class="ico">\u2699</span><span data-t="web_nav_settings">Settings</span></button>\n    <div class="foot" id="foot-index"'
c = c.replace(old_foot, new_foot, 1)

open(p, "w", encoding="utf-8").write(c)
print(f"OK: {len(c)} bytes")

# Verificar
checks = {
    "settings-btn presente": "settings-btn" in c,
    "web_nav_settings presente": "web_nav_settings" in c,
    "lang-btn eliminado": "lang-btn" not in c,
    "settings-btn en nav": '<button data-p="settings"><span class="ico">' in c,
}
for k, v in checks.items():
    print(f"  {k}: {'SI' if v else 'NO'}")

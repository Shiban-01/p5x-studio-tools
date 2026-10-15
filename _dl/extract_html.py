
import PyInstaller.archive.readers as r
from pathlib import Path
a = r.CArchiveReader('dist/P5X Studio Tools.exe')
for name in ['p5x_studio\\ui_web\\index.html', 'p5x_studio\\ui_web\\estilo.css', 'p5x_studio\\ui_web\\app.js']:
    try:
        data = a.extract(name)
        out = Path('p5x_studio') / name.split('p5x_studio\\', 1)[1]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f'{out}: {len(data)} bytes')
    except Exception as e:
        print(f'{name}: ERROR {e}')

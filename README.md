# P5X Studio Tools

**A toolkit for exploring and extracting assets from Persona 5: The Phantom X (P5X) — Global (Steam) version.**

![Version](https://img.shields.io/badge/version-0.0.3--beta-blue) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## Features

- **Bundle Explorer** — Browse and search 15,000+ game bundles with type filters and size info
- **Bundle Inspector** — Open any bundle to see its resources (meshes, textures, animations, shaders)
- **Resource Search** — Find any mesh or texture across the entire game
- **Video & Audio** — Extract USM videos and ACB/AWB audio banks with vgmstream
- **Bulk Textures** — Mass-extract texture assets organized by category
- **Bust-up Viewer** — View 266 character bust-ups with the game's real UI shader (`UIMultipleGradient`)
- **Shader Rendering** — Accurate shader port with per-character/per-outfit parameters
- **Game Update Detection** — Automatically detect new bundles after game patches
- **Auto-Update Checker** — Checks GitHub for new tool versions on startup

## Screenshots

| | |
|:---:|:---:|
| ![Bundle Explorer](screenshots/mockup_bundles_pink.png) | ![Bust-up Viewer](screenshots/mockup_bustups_black.png) |
| **Bundle Explorer** (Pink theme) | **Bust-up Viewer** (Black theme) |
| ![Inspector](screenshots/mockup_inspector_blue.png) | ![Settings](screenshots/mockup_settings_mint.png) |
| **Bundle Inspector** (Blue theme) | **Settings** (Mint theme) |

*10 color themes available: Pink, Black, Mint, Coffee, Orange, Red, Purple, Blue, Yellow, White*

## Installation

1. Download the latest `P5X Studio Tools.exe` from [Releases](https://github.com/Shiban-01/p5x-studio-tools/releases)
2. Place it in a folder (e.g., `C:\P5X Studio Tools\`)
3. Run it — the tool auto-detects your P5X installation

## Requirements

- Windows 10/11
- Persona 5: The Phantom X (Steam, Global version)

## Usage

1. **Bundles** — Browse game assets, click any bundle to see details
2. **Inspector** — Paste a bundle path or use "Choose file" to inspect contents
3. **Resources** — Search for specific assets by name across the game
4. **Video & Audio** — Extract videos (USM) and audio (ACB/AWB) files
5. **Bust-ups** — View character portraits with shader rendering, export as PNG
6. **Settings** — Configure game path, theme (10 color themes), and output folders

## Building from Source

```bash
git clone https://github.com/Shiban-01/p5x-studio-tools.git
cd p5x-studio-tools/p5x_studio
pip install -r requirements.txt
python -m PyInstaller "P5X Studio Tools.spec"
```

## Tech Stack

- **Python 3.11+** — Core logic and asset processing
- **PyInstaller** — Desktop app packaging
- **PyWebview** — Native window with web UI
- **UnityPy** — Unity asset bundle parsing
- **vgmstream** — Audio extraction (ACB/AWB)
- **FFmpeg** — Video/audio conversion

## License

MIT License — see [LICENSE](LICENSE)

---

**Note:** This tool is for personal/educational use. Respect the game's terms of service.

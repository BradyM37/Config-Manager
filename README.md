# ⚙️ OptiLock Config Manager

A clean, modern GUI application for managing Deadlock performance configs.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 🎮 **Auto-detect Deadlock** - Automatically finds your Deadlock installation
- 📦 **Preset Configs** - One-click application of optimized configs (Potato, Balanced, Quality, Competitive)
- 🎛️ **ConVar Tweaks** - Fine-tune individual settings with sliders and toggles
- 📂 **Backup System** - Automatic backups before any changes
- ↩️ **Easy Restore** - Restore any previous configuration
- 🔄 **Auto-Update** - Check for and apply updates from GitHub

## 📥 Installation

### Option 1: Download Release (Recommended)
1. Download `OptiLockManager.exe` from [Releases](https://github.com/optilock/config-manager/releases)
2. Run the exe - no installation required!

### Option 2: Run from Source
```bash
# Clone the repo
git clone https://github.com/optilock/config-manager.git
cd config-manager

# Install dependencies
pip install -r requirements.txt

# Run
python src/main.py
```

## 🛠️ Building

To create a standalone .exe:

```bash
pip install pyinstaller
python build.py
```

Output will be in `dist/OptiLockManager.exe`

## 📁 Project Structure

```
config-manager/
├── src/
│   ├── main.py              # Entry point
│   ├── ui/
│   │   ├── app.py           # Main window
│   │   ├── preset_cards.py  # Preset selection UI
│   │   └── convar_panel.py  # ConVar tweaks UI
│   ├── core/
│   │   ├── detector.py      # Deadlock auto-detection
│   │   ├── config.py        # Config read/write
│   │   ├── backup.py        # Backup/restore system
│   │   └── updater.py       # GitHub update checker
│   └── data/
│       ├── presets/         # Preset .gi config files
│       └── convars.json     # ConVar definitions
├── assets/
│   └── icon.ico             # Application icon
├── build.py                 # PyInstaller build script
├── requirements.txt
└── README.md
```

## 🎮 Adding Preset Configs

Place your `.gi` config files in `src/data/presets/`:

- `potato.gi` - Maximum FPS, minimum visuals
- `balanced.gi` - Recommended settings
- `quality.gi` - Better visuals, still optimized
- `competitive.gi` - Optimized for visibility

The manager will automatically detect and display them.

## 🔧 Configuration

Config files and backups are stored in:
```
%LOCALAPPDATA%\OptiLockManager\
├── backups/     # Automatic backups
└── presets/     # User presets (fallback)
```

## 🤝 Contributing

Pull requests welcome! For major changes, please open an issue first.

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Credits

- **OptiLock Team** - Config development
- **Maidehnless** - Original OptimisationLock
- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

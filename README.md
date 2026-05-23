<img width="800" height="400" alt="ppsocial" src="https://github.com/user-attachments/assets/c83ed064-520e-4639-a37a-a360aa36fccf" />


# ParaParser — Editor

> **QTI Parameters Control** — a desktop GUI tool for browsing, extracting, and replacing parameters in Qualcomm (QTI) camera-tuning libraries.

---

## Overview

ParaParser Editor is a PyQt5-based desktop application that lets you open a Qualcomm ISP/camera-tuning shared library, inspect every tunable parameter it contains (ID, name, byte offset, length), extract or replace individual parameters as raw binary blobs, and apply dictionary-driven export/import workflows. It supports project files, Magisk module export, ADB push, a built-in hex viewer/editor, a plugin system, and more.

---

## Features

- **Parameter table & tree view** — browse thousands of parameters in a sortable flat table or a nested tree, with live synchronised selection between the two views.
- **Binary extract / replace** — read out or patch any parameter as a raw binary file.
- **Dictionary parser** — load a `.Qdict` file to get human-readable export/import of parameter values; supports auto-find and custom dictionary parsers (`.pyd` / `.so`).
- **Project management** — open, save, and save-as compressed project files (`.QPAR`) that bundle the library and its parsed state.
- **Library management** — import a new library, overwrite the current one, export it, or revert unsaved changes.
- **Magisk module export** — wrap the modified library as a ready-to-flash Magisk module.
- **ADB export** — push the modified library directly to a connected Android device.
- **Hex viewer & hex editor** — inspect any parameter's raw bytes or edit them in-place (`Ctrl+D` / `Ctrl+Shift+D`).
- **Checksum utility** — CRC-16 / ones-complement checksum helpers, with atomic file writes.
- **Find dialog** — search parameters by name or by hex pattern inside the file.
- **Sorting** — display parameters as-parsed, by ID, or by offset.
- **Plugin system**
  - *Built-in:* Auto Tree Sorter, Batch Binary Export/Import, Rows Export, Rows Import.
  - *User plugins:* drop a `.py` / `.so` / `.pyd` file into the `Plugins/` folder or install via **Plugins → Install plugin…**
- **Legacy Chromatix support** — loads address/length/version metadata for older Chromatix-format libraries.
- **Cross-platform** — runs on Windows, macOS, and Linux (PyQt5).

---

## Requirements

| Dependency | Version |
|---|---|
| Python | ≥ 3.8 |
| PyQt5 | any recent |
| NumPy | any recent |

Install dependencies:

```bash
pip install PyQt5 numpy
```

---

## Installation

```bash
git clone https://github.com/lensonphone/ParaParser-Editor.git
cd ParaParser-Editor
pip install PyQt5 numpy
python ParaParser-Editor.py
```

No build step is needed — the application runs directly from source.

---

## Repository Layout

```
ParaParser-Editor/
├── ParaParser-Editor.py          # Application entry point & main window
├── Code/
│   ├── HelpAboutInfo/            # About, Help, Support dialogs
│   ├── InternalExporterUtils/    # Checksum, Magisk export, ADB export
│   ├── Parsers/
│   │   ├── Importer/             # Library import API
│   │   └── LegacyChromatix/      # Legacy Chromatix format support
│   ├── Plugins_BuiltIn/          # Built-in plugin modules
│   ├── ProjectManagement/        # Project open/compress/decompress
│   └── Tools/                    # Hex viewer, hex editor, dictionary tools
├── Packages/                     # Vendored / bundled packages
├── Plugins/                      # User plugin drop folder
├── Resources/                    # Embedded icons and assets
└── LICENSE.txt
```

---

## Usage

### Opening a library

1. **File → Library — Import** (`Ctrl+L`) — select a Qualcomm shared library (`.so` or proprietary binary).  
   The parameter table and tree populate automatically.

### Extracting / replacing a parameter (binary)

1. Select a row in the table or tree.
2. Click **Extract** (raw binary out) or **Replace** (raw binary in) in the right-side control panel.

### Using a dictionary

1. In the **Dictionary Parser** panel choose **Import \*.Qdict** from the dropdown and load your dictionary file.  
   Enable **Autofind Dictionary** to let the app locate a matching dictionary automatically.
2. Use **Export** / **Import** to read or write human-readable parameter values.

### Project workflow

| Action | Menu / Shortcut |
|---|---|
| Open project | File → Project — Open (`Ctrl+O`) |
| Save project | File → Project — Save (`Ctrl+S`) |
| Save project as | File → Project — Save As… (`Ctrl+Shift+S`) |

### Exporting to device

- **File → Export Library As Magisk** (`Ctrl+Shift+M`) — creates a Magisk flashable zip.
- **File → Export Library via ADB** (`Ctrl+Shift+A`) — pushes the library over ADB.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open project |
| `Ctrl+S` | Save project |
| `Ctrl+Shift+S` | Save project as |
| `Ctrl+L` | Import library |
| `Ctrl+F` | Find parameter |
| `Ctrl+D` | Hex viewer |
| `Ctrl+Shift+D` | Hex editor |
| `Ctrl+Shift+M` | Export as Magisk module |
| `Ctrl+Shift+A` | Export via ADB |
| `Shift+C` | Collapse / expand tree |
| `Shift+D` | Parser Dictionary Creator |

---

## Plugin Development

User plugins are plain Python modules (or compiled `.so` / `.pyd` extensions) placed in the `Plugins/` directory. A plugin must expose a callable that accepts `(file_path: str, rows: list[str]) -> list[str] | None`, where each row string is `"ID,Name,Offset,Length"`. Returning `None` or an empty list means "no changes".

Install a plugin at runtime via **Plugins → Install plugin…** — the app copies it into `Plugins/` and registers it in the menu.

---

## License

BSD 3-Clause — see [LICENSE.txt](LICENSE.txt).

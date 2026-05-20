# CNC Robot Control

> Universal open-source CNC robot workflow engine and editor.

`CNC_robot_control` is a desktop application built with Tkinter for building, editing, and running CNC G-code workflows. Connect to your CNC controller over serial, jog axes in real time, and automate complex routines with a line-by-line flow editor — all from a single, self-contained GUI.

---

## Features

- **Serial terminal** — communicate directly with your CNC controller
- **Jog controls & homing** — move axes and run homing sequences interactively
- **Flow editor** — build and run step-by-step G-code automation routines
- **G/M-code reference browser** — look up codes without leaving the app
- **Template import & flow persistence** — save and reload flows as `.gcode` files
- **Offline mode** — mock serial backend works without `pyserial` or hardware

---

## Download

Prebuilt binaries are published on the [latest GitHub release](https://github.com/salithasadalinda/CNC_robot_control/releases/latest):

| Platform | Download                                                                                                                                        |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Windows  | [CNC_robot_control-windows.zip](https://github.com/salithasadalinda/CNC_robot_control/releases/latest/download/CNC_robot_control-windows.zip)   |
| macOS    | [CNC_robot_control-macos.zip](https://github.com/salithasadalinda/CNC_robot_control/releases/latest/download/CNC_robot_control-macos.zip)       |
| Linux    | [CNC_robot_control-linux.tar.gz](https://github.com/salithasadalinda/CNC_robot_control/releases/latest/download/CNC_robot_control-linux.tar.gz) |

Releases are built automatically by the `Release` GitHub Actions workflow when a version tag (e.g. `v0.1.0`) is pushed, or when triggered manually from the Actions tab.

### Clone the source

```bash
git clone https://github.com/salithasadalinda/CNC_robot_control.git
cd CNC_robot_control
```

---

## Documentation

- [User manual — v0.1.0](docs/v0.1.0/user_manual.md)
- [Release guide](docs/v0.1.0/release.md)

---

## Requirements

- Python 3.14 or later
- `pyserial` for real serial port communication (optional — the app runs in mock mode without it)

---

## Installation

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

uv pip install -r requirements.txt
```

To also install development and testing dependencies:

```bash
uv pip install -r requirements-dev.txt
```

---

## Usage

### Run the GUI

From the project root:

```bash
python src\tk_app\main.py
```

Alternatively, run the package as a module by setting `PYTHONPATH` first:

```bash
set PYTHONPATH=src               # Windows
# export PYTHONPATH=src          # macOS / Linux

python -m tk_app.main
```

### Connect to your CNC controller

Use the **serial port combobox** and **baud rate selector** in the toolbar to connect. If no hardware is available, the app automatically falls back to the built-in mock serial port for offline testing.

### Run tests

```bash
pytest -q
```

---

## Project Structure

```
CNC_robot_control/
├── src/
│   └── tk_app/
│       ├── main.py          # Main GUI application entry point
│       └── __init__.py      # Package marker
├── tests/
│   └── test_smoke.py        # Basic import smoke test
├── docs/
│   └── v0.1.0/
│       ├── user_manual.md
│       └── release.md
├── pyproject.toml           # Project metadata and test configuration
├── requirements.txt
└── requirements-dev.txt
```

---

## License

This project is open source. See [`LICENSE`](LICENSE) for details.

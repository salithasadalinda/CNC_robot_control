# CNC_robot_control

Universal open-source CNC robot workflow engine and editor.

`CNC_robot_control` provides a desktop Tkinter application for building, editing, and running CNC G-code flows. It includes:

- serial terminal for CNC communication
- jog controls and homing commands
- flow editor for line-by-line G-code automation
- built-in G/M-code reference browser
- template import and flow save/load support
- mock serial support when `pyserial` is unavailable

## Download

Prebuilt desktop downloads are published on the latest GitHub release:

- [Windows download](https://github.com/salithasadalinda/CNC_robot_control/releases/latest/download/CNC_robot_control-windows.zip)
- [macOS download](https://github.com/salithasadalinda/CNC_robot_control/releases/latest/download/CNC_robot_control-macos.zip)
- [Linux download](https://github.com/salithasadalinda/CNC_robot_control/releases/latest/download/CNC_robot_control-linux.tar.gz)

You can also download the source code from GitHub:

```bash
git clone https://github.com/salithasadalinda/CNC_robot_control.git
cd CNC_robot_control
```

Release files are built automatically by the `Release` GitHub Actions workflow when a version tag such as `v0.1.0` is pushed, or when the workflow is run manually from the Actions tab.

## Requirements

- Python 3.14 or later
- `pyserial` for real serial port communication

## Install

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

If you want to run tests as well, install the dev dependencies:

```bash
uv pip install -r requirements-dev.txt
```

## Run the application

From the project root, start the Tkinter GUI:

```bash
python src\tk_app\main.py
```

If you prefer to run the package as a module, set `PYTHONPATH` to `src` first:

```bash
set PYTHONPATH=src
python -m tk_app.main
```

## Run tests

From the project root:

```bash
pytest -q
```

## Project structure

- `src/tk_app/main.py` – main GUI application
- `src/tk_app/__init__.py` – package marker
- `tests/test_smoke.py` – basic import test
- `pyproject.toml` – project metadata and test configuration

## Notes

- The app includes a mock serial port implementation for offline testing.
- Use the serial port combobox and baud rate selector to connect to your CNC controller.
- Saved flows are written as `.gcode` files and loaded back into the editor.

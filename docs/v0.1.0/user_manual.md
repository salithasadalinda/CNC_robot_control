# CNC Robot Control User Manual

Version: `v0.1.0`

CNC Robot Control is a desktop Tkinter application for building, editing, and sending G-code workflows to CNC, 3D printer, laser, or compatible motion-control firmware over a serial connection.

![CNC Robot Control overview](../assets/v0.1,0/images/axis%20and%20g%20code%20editor.png)

## Contents

- [Safety First](#safety-first)
- [Install And Start](#install-and-start)
- [Main Window Overview](#main-window-overview)
- [Connect To A Controller](#connect-to-a-controller)
- [Axis Configuration](#axis-configuration)
- [Jog Controls](#jog-controls)
- [Serial Terminal](#serial-terminal)
- [Flow Editor](#flow-editor)
- [Templates](#templates)
- [G-Code Reference](#g-code-reference)
- [Save And Open Flows](#save-and-open-flows)
- [Troubleshooting](#troubleshooting)

## Safety First

This application can send real movement commands to connected hardware. Before running a flow on a real CNC machine, test with motors disabled, a simulator, or the included mock serial mode.

Always verify:

- The correct serial port is selected.
- The baud rate matches your controller firmware.
- Emergency stop access is available.
- Homing, probing, spindle, heater, and laser commands are safe for your machine.
- G-code coordinates, units, and feed rates are appropriate.

## Install And Start

Download a release build from the project README, or run from source.

From source:

```bash
git clone https://github.com/salithasadalinda/CNC_robot_control.git
cd CNC_robot_control
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
uv pip install -r requirements.txt
python src\tk_app\main.py
```

macOS or Linux:

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
python src/tk_app/main.py
```

## Main Window Overview

The application is split into three working areas:

- Top toolbar: serial port, baud rate, connection status, run controls, and file actions.
- Left panel: axis setup, jog controls, and workflow templates.
- Main panel: flow editor, serial terminal, and G-code reference.

The toolbar includes:

- Port selector
- Baud selector
- Refresh ports button
- Connect or Disconnect button
- Run Flow and Stop buttons
- New, Open, Save, and Save As buttons

## Connect To A Controller

1. Connect your CNC controller by USB.
2. Click the refresh button beside the port selector.
3. Select the correct port.
4. Select the correct baud rate. `115200` is common for many controllers.
5. Click `Connect`.

When connected, the status indicator changes from disconnected to connected. If no serial library or real controller is available, the app can still run in mock mode for offline testing.

## Axis Configuration

![Axis configuration and flow editor](../assets/v0.1,0/images/axis%20and%20g%20code%20editor.png)

Use the `Axes` tab to configure movement axes.

Each axis has:

- Axis name
- `cm/step` value
- Enabled checkbox

Default axes are `X`, `Y`, `Z`, `U`, `A`, and `B`. Use `+ Add Axis` to add a custom axis when your machine uses additional motion channels.

## Jog Controls

![Jog controls and terminal](../assets/v0.1,0/images/jog%20and%20terminal.png)

Use the `Jog` tab for manual movement.

Controls include:

- Step distance in millimeters
- Feed rate in mm/min
- X/Y directional movement buttons
- Z up/down buttons
- U, A, and B auxiliary axis buttons
- `Home All (G28)`
- `Get Position (M114)`
- `Endstops (M119)`
- `Firmware Info (M115)`

Jog commands are sent immediately to the connected controller.

## Serial Terminal

The `Terminal` tab is for direct command entry and controller responses.

Use it to:

- Send a single G-code or M-code command.
- View responses from the controller.
- Clear the terminal output.
- Add valid commands to the flow editor.

To send a command:

1. Type a command such as `M114`.
2. Press Enter or click `Send`.
3. Check the terminal output for the response.

## Flow Editor

The `Flow Editor` tab is where you create repeatable workflows.

Use the top action buttons to:

- Add a new line
- Delete a selected line
- Move a line up or down
- Duplicate a line
- Clear the flow

Use the edit panel to change the selected G-code line and optional comment, then click `Update Line`.

Use `Run This Line` to test a selected command. Use `Run Flow` in the top toolbar to run the full workflow.

The raw import box lets you paste multiple lines of G-code and import them into the flow editor.

## Templates

![Templates and G-code reference](../assets/v0.1,0/images/template%20and%20g%20code%20referenace.png)

The `Templates` tab includes ready-made flows for common tasks such as:

- 3D print start and end
- BLTouch deploy, probe, and bed leveling
- CNC milling start and end
- Laser start and end
- PID autotune
- Filament change
- Mesh leveling
- Probe accuracy test

To load a template:

1. Select a template.
2. Click `Load Selected Template`, or double-click the template.
3. Review every command before running it on real hardware.

Loading a template can replace the current flow after confirmation.

## G-Code Reference

The `G-Code Reference` tab contains built-in G-code and M-code documentation.

You can:

- Filter by category.
- Search by code or description.
- View command details, examples, and parameters.
- Send an example to the terminal.
- Add an example to the flow editor.
- Copy an example command.

## Demo

![CNC Robot Control demo](../assets/v0.1,0/videos/demo.gif)

If the animation does not render in your viewer, open the file directly:

[Open demo GIF](../assets/v0.1,0/videos/demo.gif)

## Save And Open Flows

Use the toolbar file buttons:

- `New` starts an empty flow.
- `Open` loads an existing `.gcode` or text file.
- `Save` writes changes to the current file.
- `Save As` saves the current flow to a new file.

Saved flows are plain text G-code files, so they can be reviewed or edited outside the application.

## Troubleshooting

### No Ports Found

- Confirm the controller is plugged in.
- Install the required USB serial driver for your board.
- Close other software that may already be using the port.
- Click the refresh button beside the port selector.

### Connection Fails

- Check the selected baud rate.
- Disconnect and reconnect the USB cable.
- Restart the controller.
- Try another USB cable or port.

### Commands Do Not Move The Machine

- Confirm the machine is connected.
- Check controller alarms, locks, or emergency stop state.
- Home the machine if your firmware requires homing before movement.
- Verify units, coordinates, and feed rate.

### Flow Stops Or Sends Unexpected Commands

- Review every line in the flow editor before running.
- Test one line at a time with `Run This Line`.
- Use comments to document why each command is present.
- Keep a safe stop method ready during testing.

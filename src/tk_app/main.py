
#!/usr/bin/env python3
"""
Universal G-Code Controller
Full G/M-code reference, BLTouch, external sensors, templates, terminal, flow manager.

Dependencies:
    pip install pyserial

Run:
    python cnc_controller.py
"""
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import os
import re

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# ══════════════════════════════════════════════════════════

#  THEME
# ══════════════════════════════════════════════════════════
BG        = "#0a0d14"
BG2       = "#111520"
BG3       = "#181d2e"
BG4       = "#1e2438"
ACCENT    = "#00e5b0"
ACCENT2   = "#3b9eff"
ACCENT3   = "#c084fc"
WARN      = "#ff7043"
SUCCESS   = "#00e5b0"
ERROR     = "#ff3d6b"
TEXT      = "#dde3f0"
TEXT_DIM  = "#586280"
TEXT_MID  = "#8896b3"
BORDER    = "#252d47"
CAT_COLORS = {
    "Motion":       "#3b9eff",
    "Coordinates":  "#00e5b0",
    "Homing":       "#a78bfa",
    "Bed Leveling": "#f59e0b",
    "BLTouch":      "#ec4899",
    "Sensors":      "#10b981",
    "Temperature":  "#f97316",
    "Fans":         "#06b6d4",
    "Spindle":      "#84cc16",
    "Extruder":     "#fb923c",
    "Stepper":      "#818cf8",
    "EEPROM":       "#fbbf24",
    "Display":      "#e879f9",
    "SD Card":      "#4ade80",
    "Control":      "#f43f5e",
    "Filament":     "#fb7185",
    "Power":        "#facc15",
    "Debug":        "#94a3b8",
    "CNC Specific": "#22d3ee",
    "Laser":        "#ff6b6b",
    "Delta":        "#a3e635",
    "Linear Adv":   "#c084fc",
    "Input Shape":  "#67e8f9",
    "Custom":       "#cbd5e1",
}
FONT_MONO  = ("Consolas", 10)
FONT_MONO2 = ("Consolas", 9)
FONT_UI    = ("Segoe UI", 10)
FONT_UI9   = ("Segoe UI", 9)
FONT_HEAD  = ("Segoe UI Semibold", 11)
FONT_CODE  = ("Consolas", 11)

# ══════════════════════════════════════════════════════════
#  COMPLETE G-CODE / M-CODE DATABASE
# ══════════════════════════════════════════════════════════
# Format: (code, short_desc, full_desc, example, params)
GCODE_DB = {

  # ─── MOTION ───────────────────────────────────────────
  "Motion": [
    ("G0",  "Rapid Move",
     "Move to position at maximum speed. No cutting/extrusion.",
     "G0 X10 Y20 Z5 F3000",
     "X Y Z A B C E F — target coords + feed rate"),
    ("G1",  "Linear Move",
     "Controlled linear motion at specified feed rate. Used for cutting/printing.",
     "G1 X50 Y30 Z-1 F800 E5",
     "X Y Z A B C E F — coords, feed, extrusion"),
    ("G2",  "Arc Move CW",
     "Clockwise arc move. I/J are offsets from start to center, R is radius.",
     "G2 X10 Y10 I5 J0 F500",
     "X Y Z I J R F E — endpoint, center offset or radius"),
    ("G3",  "Arc Move CCW",
     "Counter-clockwise arc move.",
     "G3 X10 Y10 I5 J0 F500",
     "X Y Z I J R F E — endpoint, center offset or radius"),
    ("G4",  "Dwell / Pause",
     "Pause motion for a defined time. S=seconds, P=milliseconds.",
     "G4 S2   ; pause 2 seconds\nG4 P500 ; pause 500ms",
     "S(seconds) P(milliseconds)"),
    ("G5",  "Bézier Cubic Spline",
     "Smooth cubic spline motion. Requires I J P Q control point offsets.",
     "G5 I0 J3 P0 Q-3 X10 Y20",
     "X Y I J P Q — endpoint and Bézier handles"),
    ("G6",  "Direct Stepper Move",
     "Low-level direct stepper position move (Marlin 2.x).",
     "G6 X1000 Y1000 F100",
     "X Y Z E I(sync) — raw step counts"),
    ("G12", "Clean Nozzle / Spindle",
     "Execute nozzle or tool cleaning cycle (if wiper hardware present).",
     "G12 P1 S1 T2",
     "P(pattern 0-2) S(strokes) T(triangles)"),
    ("G17", "XY Plane Select",
     "Select XY plane for arcs and canned cycles.",
     "G17","None"),
    ("G18", "XZ Plane Select",
     "Select XZ plane for arcs.",
     "G18","None"),
    ("G19", "YZ Plane Select",
     "Select YZ plane for arcs.",
     "G19","None"),
  ],

  # ─── COORDINATES ──────────────────────────────────────
  "Coordinates": [
    ("G20", "Inch Units",
     "Set all coordinates to inches.",
     "G20","None"),
    ("G21", "Millimeter Units",
     "Set all coordinates to millimeters (default).",
     "G21","None"),
    ("G53", "Move in Machine Coordinates",
     "Temporarily override workspace offsets for one move.",
     "G53 G0 X0 Y0","None"),
    ("G54", "Work Coordinate System 1",
     "Select WCS 1 (default workspace offset).",
     "G54","None"),
    ("G55", "Work Coordinate System 2","Select WCS 2.","G55","None"),
    ("G56", "Work Coordinate System 3","Select WCS 3.","G56","None"),
    ("G57", "Work Coordinate System 4","Select WCS 4.","G57","None"),
    ("G58", "Work Coordinate System 5","Select WCS 5.","G58","None"),
    ("G59", "Work Coordinate System 6","Select WCS 6.","G59","None"),
    ("G90", "Absolute Positioning",
     "All coordinates interpreted as absolute positions.",
     "G90","None"),
    ("G91", "Relative Positioning",
     "All coordinates interpreted relative to current position.",
     "G91","None"),
    ("G92", "Set Position / Offset",
     "Define current position as given coordinates without moving.",
     "G92 X0 Y0 Z0 E0",
     "X Y Z E A B C — new current position values"),
    ("G92.1","Reset Position Offsets",
     "Reset G92 offsets to zero.",
     "G92.1","None"),
    ("G92.2","Suspend Position Offsets",
     "Temporarily suspend G92 offsets.",
     "G92.2","None"),
    ("G92.3","Restore Position Offsets",
     "Restore previously suspended G92 offsets.",
     "G92.3","None"),
    ("G93", "Inverse Time Feed Mode",
     "Feed rate interpreted as fraction of move per minute.",
     "G93","None"),
    ("G94", "Units per Minute Feed Mode",
     "Feed rate in mm/min or in/min (default).",
     "G94","None"),
  ],

  # ─── HOMING ───────────────────────────────────────────
  "Homing": [
    ("G27", "Park Toolhead",
     "Move to park position defined in firmware.",
     "G27 P2",
     "P(raise: 0=no raise,1=raise if lower,2=always)"),
    ("G28", "Auto Home",
     "Home one or all axes. Without params homes all axes.",
     "G28       ; home all\nG28 X Y   ; home X and Y only\nG28 Z     ; home Z only",
     "X Y Z (optional) — axes to home"),
    ("G29", "Bed Leveling (Unified)",
     "Probe the bed for leveling. Behavior depends on firmware (bilinear, UBL, mesh).",
     "G29       ; full auto level\nG29 S1    ; UBL load slot 1\nG29 P1    ; UBL phase 1\nG29 A     ; activate",
     "S(slot) P(phase) A(activate) D(disable) L(load) T(trace) V(verbose)"),
    ("G29.1","Set Z Probe Offset",
     "Directly set the Z probe offset value.",
     "G29.1 Z-1.5",
     "Z — probe offset in mm"),
    ("G29.2","Enable/Disable Bed Leveling",
     "Toggle bed leveling compensation.",
     "G29.2 S1  ; enable\nG29.2 S0  ; disable",
     "S(1=enable, 0=disable)"),
    ("G30", "Single Z-Probe",
     "Probe Z at current XY position (or given XY) and report.",
     "G30\nG30 X50 Y50",
     "X Y (optional position to probe)"),
    ("G31", "Dock Sled / Set Probe Trigger",
     "Dock the Z probe sled or set probe trigger value.",
     "G31 P25 X-29 Y-29 Z0.5",
     "P(trigger) X Y Z(offset)"),
    ("G32", "Undock Sled / Probe Bed",
     "Undock the Z probe sled or probe the entire bed.",
     "G32","None"),
    ("G33", "Delta Auto Calibration",
     "Probe and auto-calibrate a delta printer geometry.",
     "G33 P4 C0.02",
     "P(probe points 3-10) C(precision) V(verbose)"),
    ("G34", "Z Steppers Auto-Align",
     "Use probe to automatically align multiple Z steppers.",
     "G34 I3 T0.02 A",
     "I(iterations) T(accuracy) A(amplification)"),
    ("G35", "Tramming Assistant",
     "Guide manual bed tramming using probe measurements.",
     "G35 S5.0",
     "S(screw pitch mm/rev)"),
    ("G38.2","Probe Toward Workpiece (Error)",
     "Move toward workpiece until probe triggers. Error if not triggered.",
     "G38.2 Z-10 F50","X Y Z F"),
    ("G38.3","Probe Toward Workpiece (No Error)",
     "Move toward workpiece until probe triggers or end of move.",
     "G38.3 Z-10 F50","X Y Z F"),
    ("G38.4","Probe Away from Workpiece (Error)",
     "Move away until probe releases. Error if already not triggered.",
     "G38.4 Z10 F50","X Y Z F"),
    ("G38.5","Probe Away from Workpiece (No Error)",
     "Move away until probe releases.",
     "G38.5 Z10 F50","X Y Z F"),
  ],

  # ─── BED LEVELING ─────────────────────────────────────
  "Bed Leveling": [
    ("M48",  "Probe Repeatability Test",
     "Probe Z repeatedly to test probe accuracy/repeatability.",
     "M48 P10 X100 Y100 V2 E L2",
     "P(probes) X Y V(verbose 0-4) E(engage) L(legs)"),
    ("M104", "Set Hotend Temperature (no wait)",
     "Set target hotend temp and continue without waiting.",
     "M104 S200","S(target °C) T(tool index)"),
    ("M190", "Wait for Bed Temperature",
     "Wait until bed reaches target temperature.",
     "M190 S60","S(target °C) R(below temp)"),
    ("M420", "Bed Leveling State",
     "Enable/disable bed leveling and optionally load/save mesh.",
     "M420 S1       ; enable\nM420 S0       ; disable\nM420 L1       ; load slot\nM420 V        ; report",
     "S(1=on,0=off) L(load slot) T(fade height) V(verbose)"),
    ("M421", "Set Mesh Value",
     "Manually set a single mesh bed leveling point.",
     "M421 I3 J2 Z0.15\nM421 X50 Y50 Z-0.12 N",
     "I J(grid indices) X Y(coords) Z(height) N(normalize)"),
    ("G26",  "Mesh Validation Pattern",
     "Print a pattern to visually validate mesh bed leveling.",
     "G26 C0.2 F200 H200 K1 L1.75 O10 P25 R4 S1.75 U10 X50 Y50",
     "C F H K L O P R S U X Y — many options, see docs"),
  ],

  # ─── BLTOUCH / PROBES ─────────────────────────────────
  "BLTouch": [
    ("M280", "Servo Position",
     "Set BLTouch/servo angle. BLTouch uses pin P0.\n"
     "  10° = push pin down (deploy)\n  90° = push pin down (touch mode)\n"
     "  120° = raise pin (stow)\n  160° = alarm release\n  60° = self-test",
     "M280 P0 S10   ; deploy probe\nM280 P0 S90   ; touch mode\nM280 P0 S120  ; stow probe\nM280 P0 S160  ; reset alarm\nM280 P0 S60   ; self test",
     "P(servo index, BLTouch=0) S(angle 0-180)"),
    ("M401", "Deploy Probe",
     "Deploy the Z probe (BLTouch, servo-based, or magnetic).",
     "M401","H(verbose)"),
    ("M402", "Stow Probe",
     "Retract/stow the Z probe.",
     "M402","None"),
    ("M48",  "Probe Accuracy Test",
     "Test BLTouch probe repeatability. Run after deployment.",
     "M48 P10 V2","P(count) V(verbose) E(engage each)"),
    ("M851", "XYZ Probe Offset",
     "Set the X/Y/Z offset of the probe (BLTouch) from the nozzle tip.",
     "M851 X-44 Y-14 Z-2.45",
     "X Y Z — offset in mm from nozzle"),
    ("G29",  "Auto Bed Leveling",
     "Run full auto bed level using BLTouch. Probes a grid and saves mesh.",
     "G29\nG29 V2  ; verbose output",
     "See Homing section for full G29 params"),
    ("M500", "Save BLTouch Offset to EEPROM",
     "After setting M851, save to EEPROM so it persists after reboot.",
     "M851 X-44 Y-14 Z-2.45\nM500",
     "None — saves all settings"),
    ("M503", "Report Settings (verify probe)",
     "Report all current settings including probe offsets.",
     "M503 S0","S(1=no comment)"),
    ("BLTOUCH_DEPLOY",  "BLTouch Deploy Sequence",
     "Complete sequence: deploy, probe, stow. Use as template.",
     "M280 P0 S10   ; deploy\nG4 P100        ; wait 100ms\nG30            ; probe at current XY\nM280 P0 S120  ; stow",
     "Template — not a single command"),
    ("BLTOUCH_RESET",   "BLTouch Alarm Reset",
     "Reset BLTouch after alarm/error state (flashing red LED).",
     "M280 P0 S160  ; alarm release\nG4 P100\nM280 P0 S120  ; stow",
     "Template — not a single command"),
  ],

  # ─── EXTERNAL SENSORS ─────────────────────────────────
  "Sensors": [
    ("M119", "Endstop States",
     "Report the current state of all endstops and probes.",
     "M119","None"),
    ("M43",  "Pin Debug / Endstop Monitor",
     "Watch pin states in real time, test servo, report endstops.",
     "M43          ; report all pins\nM43 P44 W    ; watch pin 44\nM43 E        ; endstop monitor\nM43 S        ; servo test",
     "P(pin) W(watch) E(endstops) S(servo) I(inverse) R(release)"),
    ("M145", "Set Material Preset",
     "Store temperature presets for material slots.",
     "M145 S0 H195 B45 F0",
     "S(material 0=PLA,1=ABS) H(hotend) B(bed) F(fan)"),
    ("M301", "Set PID Hotend",
     "Set PID tuning values for hotend temperature control.",
     "M301 P22.2 I1.08 D114",
     "P I D — PID constants; E(extruder index)"),
    ("M303", "PID Autotune",
     "Run PID autotune cycle for hotend or bed.",
     "M303 E0 S200 C8  ; hotend autotune at 200°C x8 cycles\nM303 E-1 S60 C8 ; bed autotune",
     "E(0=hotend,-1=bed) S(target °C) C(cycles) U(update)"),
    ("M304", "Set PID Bed",
     "Set PID tuning values for heated bed.",
     "M304 P10.0 I0.023 D305.4",
     "P I D — PID constants"),
    ("M305", "Set Thermistor Parameters",
     "Configure thermistor type and values.",
     "M305 P0 T100000 B4092 R4700",
     "P(sensor) T(resistance) B(beta) R(pullup)"),
    ("M400", "Finish Moves",
     "Wait until all moves in the planner buffer are complete.",
     "M400","None"),
    ("M406", "Filament Sensor Enable",
     "Enable filament presence/runout sensor.",
     "M406","None"),
    ("M407", "Filament Sensor Disable",
     "Disable filament presence/runout sensor.",
     "M407","None"),
    ("M412", "Filament Runout Sensor",
     "Enable/disable filament runout sensor and set distance.",
     "M412 S1 D25  ; enable, 25mm detect distance",
     "S(1=enable) D(distance mm) H(host handling)"),
    ("M600", "Filament Change Pause",
     "Pause print for filament change. Parks head and unloads.",
     "M600 X10 Y10 Z20 E-5 L50 U50",
     "X Y Z(park) E(retract) L(load length) U(resume load)"),
    ("M701", "Load Filament",
     "Run filament load sequence.",
     "M701 T0 L50 Z10",
     "T(tool) L(length mm) Z(raise mm) S(temp)"),
    ("M702", "Unload Filament",
     "Run filament unload sequence.",
     "M702 T0 U80 Z10",
     "T(tool) U(length mm) Z(raise mm)"),
  ],

  # ─── TEMPERATURE ──────────────────────────────────────
  "Temperature": [
    ("M104", "Set Hotend Temp (no wait)",
     "Set hotend target temperature and continue.",
     "M104 S200 T0","S(°C) T(tool 0-3)"),
    ("M105", "Report Temperatures",
     "Query and report all current temperatures.",
     "M105","None"),
    ("M106", "Set Fan Speed",
     "Set cooling fan speed. S0=off, S255=full.",
     "M106 S255 P0","S(0-255) P(fan index)"),
    ("M107", "Fan Off",
     "Turn off print cooling fan.",
     "M107 P0","P(fan index, optional)"),
    ("M109", "Wait for Hotend Temp",
     "Set hotend temp and wait until reached.",
     "M109 S200 T0","S(°C) T(tool) R(exact temp)"),
    ("M110", "Set Line Number",
     "Reset line number counter for checksums.",
     "M110 N0","N(line number)"),
    ("M140", "Set Bed Temp (no wait)",
     "Set heated bed target temperature and continue.",
     "M140 S60","S(°C)"),
    ("M141", "Set Chamber Temp (no wait)",
     "Set heated chamber target temperature.",
     "M141 S40","S(°C)"),
    ("M143", "Set Max Hotend Temp",
     "Set maximum allowed hotend temperature.",
     "M143 S275","S(°C)"),
    ("M155", "Temperature Auto-Report",
     "Automatically report temperatures every N seconds.",
     "M155 S4  ; every 4 seconds\nM155 S0  ; disable",
     "S(interval in seconds, 0=disable)"),
    ("M190", "Wait for Bed Temp",
     "Set bed temp and wait until reached.",
     "M190 S60","S(°C) R(below temp)"),
    ("M191", "Wait for Chamber Temp",
     "Set chamber temp and wait until reached.",
     "M191 S40","S(°C) R(below temp)"),
    ("M302", "Cold Extrude Allow",
     "Allow or prevent extrusion below minimum temperature.",
     "M302 S0   ; allow cold extrude\nM302 S170 ; set min to 170°C",
     "S(min temp, 0=allow always)"),
  ],

  # ─── FANS ─────────────────────────────────────────────
  "Fans": [
    ("M106", "Set Fan Speed",
     "Control fan speed by index. S0=off, S255=100%.",
     "M106 S128 P0  ; fan 0 at 50%\nM106 S255 P1  ; fan 1 at 100%",
     "S(0-255) P(fan index 0-2) T(extruder index)"),
    ("M107", "Fan Off",
     "Turn off fan completely.",
     "M107\nM107 P1","P(fan index)"),
    ("M710", "Controller Fan Settings",
     "Set controller board fan speed and idle timeout.",
     "M710 S255 I128 D60 A1",
     "S(active speed) I(idle speed) D(idle delay) A(auto)"),
  ],

  # ─── SPINDLE / LASER ──────────────────────────────────
  "Spindle": [
    ("M3",  "Spindle CW / Laser On",
     "Start spindle clockwise or enable laser. S=RPM or power.",
     "M3 S8000   ; 8000 RPM\nM3 S100    ; laser 100 power",
     "S(RPM or power 0-255)"),
    ("M4",  "Spindle CCW / Laser Dynamic",
     "Start spindle counter-clockwise. Laser dynamic mode.",
     "M4 S8000","S(RPM or power)"),
    ("M5",  "Spindle/Laser Off",
     "Stop spindle or turn off laser.",
     "M5","None"),
    ("M7",  "Mist Coolant On",
     "Turn on mist coolant (CNC).",
     "M7","None"),
    ("M8",  "Flood Coolant On",
     "Turn on flood coolant (CNC).",
     "M8","None"),
    ("M9",  "Coolant Off",
     "Turn off all coolant.",
     "M9","None"),
    ("M10", "Vacuum/Blower On",
     "Turn on vacuum or blower (CNC dust collection).",
     "M10","None"),
    ("M11", "Vacuum/Blower Off",
     "Turn off vacuum/blower.",
     "M11","None"),
    ("M3.1","Laser Fire",
     "Fire laser at given power for inline engraving.",
     "M3.1 S128","S(0-255 power)"),
    ("M5.1","Laser Stop",
     "Stop laser inline mode.",
     "M5.1","None"),
  ],

  # ─── LASER ────────────────────────────────────────────
  "Laser": [
    ("M3",  "Laser On (constant)",
     "Enable laser in constant power mode.",
     "M3 S200","S(power 0-255)"),
    ("M4",  "Laser On (dynamic)",
     "Enable laser in dynamic power mode (power scales with speed).",
     "M4 S200","S(max power)"),
    ("M5",  "Laser Off",
     "Disable laser.",
     "M5","None"),
    ("M106","Air Assist Fan",
     "Control air assist fan for laser cutting.",
     "M106 S255 P2","S(speed) P(fan index)"),
    ("G0",  "Laser Rapid Move (off)",
     "Rapid move with laser off (travel).",
     "G0 X100 Y100 F6000","X Y F"),
    ("G1",  "Laser Cut Move",
     "Move with laser on at controlled feed rate.",
     "G1 X200 F1500 S200","X Y F S(power)"),
    ("M7",  "Mist (Air) On",
     "Turn on air assist (mapped to mist coolant).",
     "M7","None"),
    ("M9",  "Air Assist Off",
     "Turn off air assist.",
     "M9","None"),
    ("M3.9","Laser Inline Enable",
     "Enable inline laser power control per-segment.",
     "M3.9","None"),
  ],

  # ─── EXTRUDER ─────────────────────────────────────────
  "Extruder": [
    ("T0",  "Select Tool 0",
     "Switch to extruder/tool 0.",
     "T0","None"),
    ("T1",  "Select Tool 1",
     "Switch to extruder/tool 1 (dual extrusion).",
     "T1","None"),
    ("M82", "Absolute Extrusion",
     "Set extruder to absolute mode.",
     "M82","None"),
    ("M83", "Relative Extrusion",
     "Set extruder to relative mode.",
     "M83","None"),
    ("M207","Set Retraction",
     "Configure firmware retraction settings.",
     "M207 S3 F45 Z0.2 W3",
     "S(length mm) F(speed mm/min) Z(lift mm) W(extra restart)"),
    ("M208","Set Retraction Recover",
     "Configure extra length/speed on retraction recovery.",
     "M208 S0 F10","S(extra mm) F(speed mm/min)"),
    ("M209","Auto Retract Enable",
     "Enable or disable firmware automatic retraction.",
     "M209 S1  ; enable\nM209 S0  ; disable",
     "S(1=enable, 0=disable)"),
    ("G10", "Retract",
     "Firmware retract using M207 settings.",
     "G10","None"),
    ("G11", "Recover (Unretract)",
     "Firmware retraction recover using M208 settings.",
     "G11","None"),
    ("M900","Linear Advance K Factor",
     "Set Linear Advance K factor for pressure equalization.",
     "M900 K0.2  ; typical PLA\nM900 K0    ; disable",
     "K(factor 0=disable)"),
  ],

  # ─── STEPPER MOTORS ───────────────────────────────────
  "Stepper": [
    ("M17",  "Enable All Steppers",
     "Energize all stepper motors.",
     "M17","None"),
    ("M18",  "Disable All Steppers",
     "De-energize all stepper motors (same as M84).",
     "M18","None"),
    ("M84",  "Disable Steppers",
     "Disable one or all stepper motors after inactivity timeout.",
     "M84       ; disable all\nM84 X Y   ; disable X and Y only\nM84 S30   ; set timeout 30s",
     "X Y Z E (axes) S(timeout seconds)"),
    ("M85",  "Inactivity Timeout",
     "Set stepper motor inactivity timeout.",
     "M85 S120","S(seconds, 0=disable)"),
    ("M92",  "Set Steps/mm",
     "Set stepper steps per mm for each axis.",
     "M92 X80 Y80 Z400 E97",
     "X Y Z E A B — steps/mm per axis"),
    ("M201", "Set Max Acceleration",
     "Set maximum acceleration for each axis (mm/s²).",
     "M201 X500 Y500 Z100 E5000",
     "X Y Z E A B — mm/s² per axis"),
    ("M202", "Set Max Travel Acceleration",
     "Set max acceleration for non-printing travel moves.",
     "M202 X500 Y500","X Y Z E — mm/s²"),
    ("M203", "Set Max Feedrate",
     "Set maximum feed rate (mm/s) per axis.",
     "M203 X200 Y200 Z10 E50",
     "X Y Z E A B — mm/s per axis"),
    ("M204", "Set Starting Acceleration",
     "Set default print (P) and travel (T) acceleration.",
     "M204 P800 T2000","P(print mm/s²) T(travel mm/s²) R(retract)"),
    ("M205", "Set Advanced Settings",
     "Set jerk, junction deviation, and minimum speeds.",
     "M205 X8 Y8 Z0.4 E2 S0.1 T0.1",
     "X Y Z E(jerk) S(min seg speed) T(min travel speed) J(junction dev)"),
    ("M211", "Software Endstops",
     "Enable/disable software endstop limits.",
     "M211 S1  ; enable\nM211 S0  ; disable",
     "S(1=enable, 0=disable)"),
    ("M350", "Set Microstepping",
     "Set microstepping divisor for each axis driver.",
     "M350 X16 Y16 Z16 E16 B1",
     "X Y Z E B(for each driver) — divisor"),
    ("M351", "Set Microstep Pins",
     "Directly set MS1/MS2 pins for microstepping.",
     "M351 X1 Y1 E1 B0 S1",
     "X Y Z E B(pin values) S(pin number 1 or 2)"),
    ("M569", "Driver Direction",
     "Reverse motor direction for a given axis driver.",
     "M569 S1 X  ; reverse X\nM569 S0 Y  ; normal Y",
     "S(0=normal,1=reverse) X Y Z E"),
    ("M906", "Set Motor Current (mA)",
     "Set stepper motor current via TMC drivers.",
     "M906 X800 Y800 Z800 E500",
     "X Y Z E A B — milliamps"),
    ("M911", "TMC Stealth Chop Thresh",
     "Report/set TMC stepper StealthChop velocity threshold.",
     "M911","None"),
    ("M912", "Clear TMC OT Flag",
     "Clear TMC driver overtemperature pre-warning flag.",
     "M912 X Y","X Y Z E (axes)"),
    ("M913", "Set Hybrid Threshold",
     "Set TMC hybrid SpreadCycle/StealthChop velocity threshold.",
     "M913 X100 Y100 Z3","X Y Z E — mm/s threshold"),
    ("M914", "TMC Bump Sensitivity",
     "Set sensorless homing stall sensitivity (TMC2209/2130).",
     "M914 X63 Y63","X Y Z — sensitivity -64 to 63"),
    ("M919", "TMC Chopper Timing",
     "Set custom chopper timing for TMC drivers.",
     "M919 O5 P3 S1 X","O P S axis"),
  ],

  # ─── EEPROM ───────────────────────────────────────────
  "EEPROM": [
    ("M500", "Save Settings",
     "Save all current settings to EEPROM.",
     "M500","None"),
    ("M501", "Load Settings",
     "Load settings from EEPROM (restore saved).",
     "M501","None"),
    ("M502", "Reset to Factory",
     "Reset all settings to compiled firmware defaults. Use M500 to save.",
     "M502\nM500  ; then save",
     "None"),
    ("M503", "Report Settings",
     "Print all current settings as G-code (can copy to restore).",
     "M503\nM503 S0  ; brief",
     "S(1=with comments, 0=no comments)"),
    ("M504", "Validate EEPROM",
     "Validate EEPROM data integrity.",
     "M504","None"),
  ],

  # ─── DISPLAY / LCD ────────────────────────────────────
  "Display": [
    ("M0",   "Unconditional Stop",
     "Pause and wait for user button press on LCD.",
     "M0\nM0 Click to continue\nM0 P5000 ; timeout 5s",
     "P(ms timeout) S(message)"),
    ("M1",   "Conditional Stop",
     "Stop if LCD or host allows, else continue.",
     "M1 Check filament","Message string (optional)"),
    ("M117", "Set LCD Message",
     "Display a message on the LCD screen.",
     'M117 Printing...\nM117 Done!',
     "Message text (max ~20 chars)"),
    ("M118", "Serial Print",
     "Print a message to the serial port / host.",
     'M118 Hello from printer\nM118 E1 ; to host',
     "A(action) E(echo) Pn(port) — message text"),
    ("M150", "Set LED Color",
     "Set RGB(W) LED color. Used for NeoPixel and RGB strips.",
     "M150 R255 G0 B0    ; red\nM150 R0 G255 B0  ; green\nM150 W128        ; warm white",
     "R G B W(white) P(neo index) I(index) K(keep)"),
    ("M300", "Play Tone / Beep",
     "Play a tone through the buzzer.",
     "M300 S440 P500  ; A4 for 500ms\nM300 S0 P100    ; silent pause",
     "S(freq Hz) P(duration ms)"),
    ("M73",  "Set Print Progress",
     "Set the print progress percentage and time remaining on LCD.",
     "M73 P50 R30  ; 50% done, 30 min remain",
     "P(percent 0-100) R(minutes remaining)"),
  ],

  # ─── SD CARD ──────────────────────────────────────────
  "SD Card": [
    ("M20",  "List SD Files",
     "List all files on the SD card.",
     "M20","None"),
    ("M21",  "Init SD Card",
     "Initialize / re-mount the SD card.",
     "M21","None"),
    ("M22",  "Release SD Card",
     "Release / unmount the SD card.",
     "M22","None"),
    ("M23",  "Select SD File",
     "Select a file for printing.",
     "M23 test.gcode","Filename (8.3 format)"),
    ("M24",  "Start/Resume SD Print",
     "Start or resume printing the selected SD file.",
     "M24\nM24 S100 T30","S(position) T(time)"),
    ("M25",  "Pause SD Print",
     "Pause the current SD print.",
     "M25","None"),
    ("M26",  "Set SD Position",
     "Set SD read position in bytes.",
     "M26 S10000","S(byte position)"),
    ("M27",  "SD Print Status",
     "Report SD print status and progress.",
     "M27\nM27 S4  ; auto-report every 4s",
     "S(interval seconds)"),
    ("M28",  "Start SD Write",
     "Open a file on SD for writing.",
     "M28 test.gcode","Filename"),
    ("M29",  "Stop SD Write",
     "Close the file being written to SD.",
     "M29","None"),
    ("M30",  "Delete SD File",
     "Delete a file from the SD card.",
     "M30 test.gcode","Filename"),
    ("M32",  "Select and Start Print",
     "Select file and start printing in one command.",
     "M32 test.gcode","Filename (supports subdirs)"),
    ("M33",  "Long Path to 8.3 Name",
     "Convert long filename to 8.3 DOS format.",
     "M33 /folder/mylong.gcode","Path"),
    ("M34",  "SD Card Sort Order",
     "Set SD card file sorting options.",
     "M34 S1 F1","S(1=alpha) F(1=folders first)"),
  ],

  # ─── CONTROL ──────────────────────────────────────────
  "Control": [
    ("M0",   "Unconditional Stop",
     "Halt machine and wait for user resume.",
     "M0","None"),
    ("M1",   "Conditional Stop",
     "Stop if SD printing.",
     "M1","None"),
    ("M2",   "Program End",
     "Indicate end of program (same as M30 in some firmware).",
     "M2","None"),
    ("M30",  "Program End / Delete File",
     "End program. In Marlin: delete SD file.",
     "M30","Filename (for delete)"),
    ("M112", "Emergency Stop",
     "Immediately stop all motion and shut down. Requires power cycle or firmware reset.",
     "M112","None"),
    ("M113", "Host Keepalive",
     "Set host keepalive interval.",
     "M113 S2","S(seconds, 0=disable)"),
    ("M115", "Firmware Info",
     "Report firmware version and capabilities.",
     "M115","None"),
    ("M116", "Wait for Temperatures",
     "Wait until all set temperatures are reached.",
     "M116","None"),
    ("M120", "Enable Endstops",
     "Enable endstop checking.",
     "M120","None"),
    ("M121", "Disable Endstops",
     "Disable endstop checking.",
     "M121","None"),
    ("M122", "TMC Debug Report",
     "Report TMC stepper driver debug information.",
     "M122","X Y Z E (optional)"),
    ("M226", "Wait for Pin State",
     "Wait until a pin is in the expected state.",
     "M226 P10 S1  ; wait for pin 10 HIGH",
     "P(pin) S(state 0=low,1=high)"),
    ("M355", "Case Light",
     "Toggle or set brightness of enclosure/case light.",
     "M355 S1 P128  ; on at 50%",
     "S(0=off,1=on) P(brightness 0-255)"),
    ("M380", "Activate Solenoid",
     "Activate the solenoid on the active extruder.",
     "M380","None"),
    ("M381", "Deactivate Solenoids",
     "Deactivate all solenoids.",
     "M381","None"),
    ("M410", "Quick Stop",
     "Stop all motion immediately (less severe than M112).",
     "M410","None"),
    ("M605", "Multi-Nozzle Mode",
     "Set dual-nozzle print mode (IDEX printers).",
     "M605 S2 R0 X20  ; mirror mode\nM605 S1         ; normal",
     "S(mode 0-3) X(offset) R(temp diff)"),
    ("M993", "SD to SPI Flash",
     "Copy SD card file to SPI flash.",
     "M993","None"),
    ("M994", "SPI Flash to SD",
     "Copy SPI flash to SD card.",
     "M994","None"),
  ],

  # ─── FILAMENT SENSOR ──────────────────────────────────
  "Filament": [
    ("M406", "Filament Sensor Enable",
     "Enable the filament presence sensor.",
     "M406","None"),
    ("M407", "Filament Sensor Disable",
     "Disable the filament presence sensor.",
     "M407","None"),
    ("M412", "Filament Runout",
     "Configure filament runout sensor.",
     "M412 S1 D25\nM412 R  ; report",
     "S(1=enable) D(detect distance mm) H(host response)"),
    ("M600", "Filament Change",
     "Pause for filament change. Parks, unloads, waits, reloads.",
     "M600\nM600 X10 Y10 Z5 E-3 L100",
     "X Y Z(park pos) E(retract) L(load) U(extra)"),
    ("M701", "Load Filament",
     "Load filament to nozzle.",
     "M701 T0 L120 Z5 S210",
     "T(tool) L(mm) Z(lift mm) S(temp)"),
    ("M702", "Unload Filament",
     "Unload filament from nozzle.",
     "M702 T0 U150 Z5",
     "T(tool) U(mm) Z(lift mm)"),
    ("M603", "Configure Filament Change",
     "Set filament change load/unload distances.",
     "M603 L100 U120",
     "L(load mm) U(unload mm) T(tool)"),
  ],

  # ─── POWER ────────────────────────────────────────────
  "Power": [
    ("M80",  "ATX Power On",
     "Turn on the ATX power supply (if controlled by firmware).",
     "M80","None"),
    ("M81",  "ATX Power Off",
     "Turn off the ATX power supply.",
     "M81","None"),
    ("M850", "Hotend Offset",
     "Set hotend XYZ offsets (multi-extruder).",
     "M850 X0.0 Y0.0 Z0.0","X Y Z — offset in mm"),
    ("M911", "TMC Stealth Chop Report",
     "Report TMC driver StealthChop status.",
     "M911","None"),
    ("M916", "TMC Z Raise on Stall",
     "Raise Z when stall detected (sensorless).",
     "M916","None"),
    ("M917", "TMC Min Current Find",
     "Find minimum motor current (TMC).",
     "M917 X Y","axes"),
    ("M918", "TMC Max Speed Find",
     "Find maximum speed before stall (TMC).",
     "M918","None"),
  ],

  # ─── DEBUG ────────────────────────────────────────────
  "Debug": [
    ("M111", "Debug Level",
     "Set debug flags. Sum of: 1=echo,2=info,4=errors,8=dryrun,16=comms,32=leveling.",
     "M111 S6   ; info + errors\nM111 S0   ; off",
     "S(flags bitmask)"),
    ("M114", "Get Position",
     "Report current position of all axes.",
     "M114\nM114 D  ; detailed\nM114 E  ; extended",
     "D(detailed) E(extended) R(realtime)"),
    ("M115", "Firmware Info",
     "Report firmware name, version, and capabilities (CAPS).",
     "M115","None"),
    ("M119", "Endstop States",
     "Report triggered/open state of all endstops.",
     "M119","None"),
    ("M122", "TMC Debug",
     "Detailed TMC stepper driver diagnostics.",
     "M122","X Y Z E axes (optional)"),
    ("M154", "Position Auto-Report",
     "Automatically report position every N seconds.",
     "M154 S4  ; every 4s\nM154 S0  ; disable",
     "S(interval seconds)"),
    ("M163", "Mix Factor",
     "Set proportional mix factor for mixing extruder.",
     "M163 S0 P0.5","S(component) P(mix 0-1)"),
    ("M164", "Save Mix",
     "Save current mix as a virtual tool.",
     "M164 S0","S(virtual tool index)"),
    ("M200", "Set Filament Diameter",
     "Set actual filament diameter for volumetric extrusion.",
     "M200 D1.75 T0\nM200 D0    ; disable volumetric",
     "D(mm) T(tool)"),
    ("M222", "Set Speed for Purpose",
     "Set extrusion factor percentage.",
     "M222 S95","S(percent)"),
    ("M404", "Filament Width Nominal",
     "Set nominal filament width and enable sensor reporting.",
     "M404 N1.75 W1","N(nominal mm) W(enable sensor)"),
    ("M408", "JSON Status Report",
     "Report machine status in JSON format (RepRapFirmware).",
     "M408 S0","S(type 0-5)"),
    ("M530", "Print Job Start",
     "Notify host of print job start with filename.",
     "M530 S1 L:filename.gcode","S(1=start) L(filename)"),
    ("M531", "Print Job Filename",
     "Set print job filename.",
     "M531 filename.gcode","Filename"),
    ("M532", "Print Job Progress",
     "Set print job progress percentage.",
     "M532 X50.0 L100000","X(percent) L(byte)"),
  ],

  # ─── CNC SPECIFIC ─────────────────────────────────────
  "CNC Specific": [
    ("G40", "Cutter Compensation Off",
     "Cancel cutter radius/diameter compensation.",
     "G40","None"),
    ("G41", "Cutter Comp Left",
     "Tool radius compensation to the left of programmed path.",
     "G41 D0.5","D(radius offset)"),
    ("G42", "Cutter Comp Right",
     "Tool radius compensation to the right of programmed path.",
     "G42 D0.5","D(radius offset)"),
    ("G43", "Tool Length Offset +",
     "Apply tool length offset (add).",
     "G43 H1","H(tool offset register 1-99)"),
    ("G44", "Tool Length Offset -",
     "Apply tool length offset (subtract).",
     "G44 H1","H(tool offset register)"),
    ("G49", "Cancel Tool Length Offset",
     "Cancel active tool length offset.",
     "G49","None"),
    ("G61", "Exact Path Mode",
     "Exact stop at each programmed point.",
     "G61","None"),
    ("G64", "Continuous Path Mode",
     "Continuous path blending (default for most).",
     "G64 P0.01","P(tolerance mm)"),
    ("G73", "Peck Drilling Cycle",
     "Canned peck drilling cycle with chip break.",
     "G73 X10 Y10 Z-20 R2 Q5 F100",
     "X Y(pos) Z(depth) R(retract) Q(peck) F(feed)"),
    ("G74", "Left-Hand Tapping Cycle",
     "CCW tapping canned cycle.",
     "G74 X10 Y10 Z-15 R2 F200","X Y Z R F"),
    ("G76", "Fine Boring Cycle",
     "Fine boring canned cycle.",
     "G76 X10 Y10 Z-10 R2 F50","X Y Z R F P Q"),
    ("G80", "Cancel Canned Cycle",
     "Cancel any active canned machining cycle.",
     "G80","None"),
    ("G81", "Drilling Cycle",
     "Simple drilling canned cycle.",
     "G81 X10 Y10 Z-20 R2 F100","X Y Z R F"),
    ("G82", "Drilling Cycle with Dwell",
     "Drill and dwell at bottom.",
     "G82 X10 Y10 Z-20 R2 P500 F100","X Y Z R P(ms dwell) F"),
    ("G83", "Peck Drilling",
     "Full retract peck drilling cycle.",
     "G83 X10 Y10 Z-30 R2 Q5 F80","X Y Z R Q(peck depth) F"),
    ("G84", "Tapping Cycle",
     "Right-hand tapping canned cycle.",
     "G84 X10 Y10 Z-15 R2 F200","X Y Z R F"),
    ("G85", "Boring Cycle",
     "Boring cycle — no dwell, feed out.",
     "G85 X10 Y10 Z-10 R2 F50","X Y Z R F"),
    ("G86", "Boring Cycle Spindle Stop",
     "Boring cycle — stop spindle, rapid out.",
     "G86 X10 Y10 Z-10 R2 F50","X Y Z R F P"),
    ("G87", "Back Boring Cycle",
     "Back boring canned cycle.",
     "G87 X10 Y10 Z-10 R2 I2 J2 F50","X Y Z R I J F"),
    ("G89", "Boring Cycle with Dwell",
     "Boring cycle with dwell at bottom.",
     "G89 X10 Y10 Z-10 R2 P500 F50","X Y Z R P F"),
    ("G98", "Canned Cycle Return Initial",
     "After canned cycle, return to initial Z level.",
     "G98","None"),
    ("G99", "Canned Cycle Return R Level",
     "After canned cycle, return to R plane.",
     "G99","None"),
    ("M0",  "Program Stop",
     "Optional program stop — wait for operator.",
     "M0","None"),
    ("M1",  "Optional Stop",
     "Optional stop if switch enabled.",
     "M1","None"),
    ("M2",  "Program End",
     "End of program.",
     "M2","None"),
    ("M6",  "Tool Change",
     "Execute a tool change.",
     "M6 T2","T(tool number)"),
    ("M19", "Spindle Orient",
     "Orient spindle to angle (for ATC).",
     "M19 S0","S(angle)"),
    ("M66", "Wait for Input",
     "Wait for digital input pin to reach state.",
     "M66 P3 L3 Q10  ; wait pin 3 high up to 10s",
     "P(pin) E(analog) L(mode) Q(timeout s)"),
  ],

  # ─── DELTA PRINTERS ───────────────────────────────────
  "Delta": [
    ("M665", "Delta Configuration",
     "Set delta geometry: diagonal rod length, radius, height, segments.",
     "M665 L250 R111 H250 B100 X0 Y0 Z0 S100",
     "L(rod) R(radius) H(height) B(print radius) X Y Z(tower offsets) S(segments/s)"),
    ("M666", "Delta Endstop Adjustments",
     "Fine-tune tower endstop offsets for delta calibration.",
     "M666 X0.5 Y-0.3 Z-0.2","X Y Z — endstop offset mm"),
    ("G33",  "Delta Auto-Calibrate",
     "Automated delta calibration via probe.",
     "G33 P4 C0.02 V2",
     "P(probe points 3-10) C(precision) V(verbose) O(old-style)"),
    ("M208", "Set Axis Max",
     "Set maximum travel for each axis (delta uses for height).",
     "M208 X235 Y235 Z300","X Y Z (max mm)"),
  ],

  # ─── LINEAR ADVANCE ───────────────────────────────────
  "Linear Adv": [
    ("M900", "Linear Advance K-Factor",
     "Set Linear Advance pressure control K factor.\n"
     "K=0 disables. Typical: PLA 0.05–0.2, PETG 0.1–0.3, Flex 0.5–2.0",
     "M900 K0.1   ; PLA\nM900 K0     ; disable\nM900 T0 K0.15 ; tool 0",
     "K(factor) T(tool) L(legacy mode)"),
  ],

  # ─── INPUT SHAPING ────────────────────────────────────
  "Input Shape": [
    ("M593", "Input Shaping",
     "Set input shaping (resonance compensation) frequency and damping.\n"
     "Reduces ghosting/ringing artifacts. Requires accelerometer calibration.",
     "M593 F45.6 D0.15 X\nM593 F0     ; disable",
     "F(frequency Hz) D(damping) X Y (axis)"),
    ("M494", "Resonance Test",
     "Run automatic resonance frequency test (requires ADXL345).",
     "M494","None"),
  ],

}

# ══════════════════════════════════════════════════════════
#  FLOW TEMPLATES
# ══════════════════════════════════════════════════════════
TEMPLATES = {
  "3D Print — Start": [
    "G28                    ; home all axes",
    "G29                    ; auto bed level",
    "M420 S1                ; enable bed leveling",
    "G1 Z5 F3000            ; raise Z",
    "G1 X0 Y0 F3000         ; move to origin",
    "M109 S200              ; wait for hotend 200°C",
    "M190 S60               ; wait for bed 60°C",
    "G92 E0                 ; reset extruder",
    "G1 X0 Y20 Z0.3 F3000   ; approach start",
    "G1 X0 Y200 E25 F500    ; prime line",
    "G92 E0                 ; reset extruder again",
    "M117 Printing...       ; display message",
  ],
  "3D Print — End": [
    "M104 S0                ; hotend off",
    "M140 S0                ; bed off",
    "G91                    ; relative",
    "G1 Z10 F3000           ; raise Z",
    "G90                    ; absolute",
    "G28 X Y                ; home X/Y",
    "M84                    ; disable steppers",
    "M117 Print complete!",
  ],
  "BLTouch — Deploy & Probe": [
    "M280 P0 S160           ; BLTouch alarm release",
    "G4 P100",
    "M280 P0 S10            ; deploy pin",
    "G4 P100",
    "G30                    ; single probe at current XY",
    "M280 P0 S120           ; stow pin",
  ],
  "BLTouch — Full Bed Level": [
    "G28                    ; home all",
    "M280 P0 S160           ; alarm release",
    "G4 P500",
    "G29                    ; full mesh probe",
    "M420 S1                ; enable mesh",
    "M500                   ; save to EEPROM",
    "M117 Bed leveled!",
  ],
  "BLTouch — Set Z Offset": [
    "G28                    ; home all",
    "M851 X-44 Y-14 Z0      ; reset probe offset",
    "G1 X117 Y117 Z10 F3000 ; center of bed",
    "G30                    ; probe and get Z",
    "; M851 Z<value>         ; set measured offset",
    "M500                   ; save",
    "M503                   ; verify",
  ],
  "CNC — Milling Start": [
    "G21                    ; mm units",
    "G90                    ; absolute",
    "G17                    ; XY plane",
    "M5                     ; spindle off",
    "G28                    ; home",
    "G92 X0 Y0 Z0           ; zero at home",
    "M3 S12000              ; spindle CW 12000 RPM",
    "G4 S3                  ; wait 3s for spindle",
    "G0 Z5                  ; safe Z",
  ],
  "CNC — Milling End": [
    "M5                     ; spindle off",
    "M9                     ; coolant off",
    "G0 Z50                 ; raise Z",
    "G28 X Y                ; home X/Y",
    "M84                    ; disable steppers",
    "M117 Job complete",
  ],
  "Laser — Start (GRBL)": [
    "G21                    ; mm",
    "G90                    ; absolute",
    "M5                     ; laser off",
    "G28                    ; home",
    "G92 X0 Y0              ; zero here",
    "M3 S0                  ; laser ready",
    "G0 X0 Y0 F6000         ; go to start",
  ],
  "Laser — End (GRBL)": [
    "M5                     ; laser off",
    "G0 X0 Y0               ; home position",
    "M9                     ; air off",
    "M84                    ; disable steppers",
  ],
  "PID Autotune — Hotend": [
    "M303 E0 S200 C8 U1     ; tune hotend at 200°C x8",
    "; result prints as M301 P.. I.. D..",
    "M500                   ; save when done",
  ],
  "PID Autotune — Bed": [
    "M303 E-1 S60 C8 U1     ; tune bed at 60°C x8",
    "; result prints as M304 P.. I.. D..",
    "M500",
  ],
  "Delta — Calibrate": [
    "G28                    ; home all towers",
    "G33 P4 C0.02 V2        ; auto calibrate",
    "M500                   ; save",
    "G28                    ; re-home",
    "M114                   ; verify position",
  ],
  "TMC — Sensorless Homing Setup": [
    "M914 X63 Y63           ; set stall sensitivity",
    "M569 S1 X Y            ; enable stealthchop if needed",
    "M500",
    "G28                    ; test homing",
    "M122                   ; check TMC report",
  ],
  "Filament Change Mid-Print": [
    "M600                   ; pause for filament change",
    "; (machine parks, unloads, waits)",
    "; load new filament on LCD prompt",
    "; machine purges and resumes",
  ],
  "Linear Advance Calibration": [
    "M900 K0                ; disable first",
    "M900 K0.1              ; test value",
    "; print calibration tower",
    "M900 K0.05             ; adjust",
    "M500                   ; save best value",
  ],
  "Mesh Leveling — Manual": [
    "G28",
    "M420 S0                ; disable leveling",
    "G29 S0                 ; start manual mesh",
    "; use LCD to adjust each point",
    "M420 S1                ; enable result",
    "M500",
  ],
  "Probe Accuracy Test": [
    "G28",
    "M48 P10 X100 Y100 V2 E L2  ; 10 probes, verbose",
    "; check Std Dev in output",
  ],
}

# ══════════════════════════════════════════════════════════
#  SERIAL MOCK
# ══════════════════════════════════════════════════════════
class MockSerial:
    def __init__(self): self.is_open = True
    def write(self, data): pass
    def readline(self): time.sleep(0.04); return b"ok\n"
    def close(self): self.is_open = False

class MockPorts:
    @staticmethod
    def comports():
        class P:
            def __init__(self, d, desc): self.device=d; self.description=desc
        return [P("COM1","Mock CNC (Marlin)"), P("COM2","Mock GRBL 1.1")]

# ══════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════
class CNCController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal G-Code Controller")
        self.geometry("1400x880")
        self.minsize(1200, 750)
        self.configure(bg=BG)
        self.serial_conn  = None
        self.connected    = False
        self.flow_lines   = []
        self.current_file = None
        self.axes         = {
            "X": {"cm_per_step": 1.0, "enabled": True},
            "Y": {"cm_per_step": 1.0, "enabled": True},
            "Z": {"cm_per_step": 1.0, "enabled": True},
            "U": {"cm_per_step": 1.0, "enabled": True},
            "A": {"cm_per_step": 1.0, "enabled": True},
            "B": {"cm_per_step": 1.0, "enabled": True},
        }
        self.running_flow = False
        self.cmd_history  = []
        self.hist_idx     = -1
        self.last_valid   = None
        self._port_list   = []
        self._build_ui()
        self._scan_ports()
        self._log("Universal G-Code Controller ready.\n", "info")
        self._log(f"Loaded {sum(len(v) for v in GCODE_DB.values())} G/M codes in {len(GCODE_DB)} categories.\n", "info")

    # ════════════════════════════
    #  STYLE
    # ════════════════════════════
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=FONT_UI,
                    fieldbackground=BG2, bordercolor=BORDER, relief="flat")
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("TNotebook", background=BG, bordercolor=BORDER, tabmargins=0)
        s.configure("TNotebook.Tab", background=BG3, foreground=TEXT_DIM,
                    padding=[14,6], font=FONT_HEAD)
        s.map("TNotebook.Tab",
              background=[("selected",BG2)], foreground=[("selected",ACCENT)])
        s.configure("TPanedwindow", background=BG)
        for name, bg_, fg_ in [
            ("Accent", ACCENT,  BG),
            ("Blue",   ACCENT2, BG),
            ("Warn",   WARN,    "#fff"),
            ("Red",    ERROR,   "#fff"),
        ]:
            s.configure(f"{name}.TButton", background=bg_, foreground=fg_,
                        font=("Segoe UI Semibold",10), relief="flat",
                        borderwidth=0, padding=[12,6])
            s.map(f"{name}.TButton",
                  background=[("active", bg_), ("disabled", BORDER)],
                  foreground=[("disabled", TEXT_DIM)])
        s.configure("Ghost.TButton", background=BG3, foreground=TEXT,
                    font=FONT_UI, relief="flat", borderwidth=0, padding=[10,5])
        s.map("Ghost.TButton", background=[("active", BG4)])
        s.configure("TScrollbar", background=BG3, troughcolor=BG2,
                    arrowcolor=TEXT_DIM, bordercolor=BG, relief="flat")
        s.configure("Treeview", background=BG2, foreground=TEXT,
                    fieldbackground=BG2, bordercolor=BORDER, rowheight=26)
        s.map("Treeview", background=[("selected",BG4)], foreground=[("selected",ACCENT)])
        s.configure("Treeview.Heading", background=BG3, foreground=TEXT_DIM,
                    font=FONT_HEAD, relief="flat")
        s.configure("TCombobox", fieldbackground=BG3, background=BG3,
                    foreground=TEXT, arrowcolor=ACCENT, bordercolor=BORDER)
        s.map("TCombobox", fieldbackground=[("readonly",BG3)])
        s.configure("TEntry", fieldbackground=BG3, foreground=TEXT,
                    insertcolor=ACCENT, bordercolor=BORDER)
        s.configure("TCheckbutton", background=BG2, foreground=TEXT, indicatorcolor=BG3)
        s.map("TCheckbutton", indicatorcolor=[("selected",ACCENT)])

    # ════════════════════════════
    #  UI BUILD
    # ════════════════════════════
    def _build_ui(self):
        self._style()
        self._build_toolbar()
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))
        left  = tk.Frame(paned, bg=BG, width=340)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  weight=0)
        paned.add(right, weight=1)
        left.pack_propagate(False)
        self._build_left(left)
        self._build_right(right)

    # ── TOOLBAR ──────────────────
    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG2, height=54)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⚙  UNIVERSAL G-CODE CONTROLLER", bg=BG2,
                 fg=ACCENT, font=("Consolas",12,"bold")).pack(side=tk.LEFT, padx=14)
        tk.Frame(bar, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=8)
        cf = tk.Frame(bar, bg=BG2); cf.pack(side=tk.LEFT, padx=10)
        def lbl(t): tk.Label(cf, text=t, bg=BG2, fg=TEXT_DIM, font=FONT_UI9).pack(side=tk.LEFT, padx=3)
        lbl("Port")
        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(cf, textvariable=self.port_var, width=16, state="readonly")
        self.port_cb.pack(side=tk.LEFT, padx=3)
        lbl("Baud")
        self.baud_var = tk.StringVar(value="115200")
        ttk.Combobox(cf, textvariable=self.baud_var,
                     values=["9600","19200","38400","57600","115200","250000"],
                     width=8, state="readonly").pack(side=tk.LEFT, padx=3)
        ttk.Button(cf, text="↺", style="Ghost.TButton",
                   command=self._scan_ports).pack(side=tk.LEFT, padx=2)
        self.conn_btn = ttk.Button(cf, text="Connect", style="Accent.TButton",
                                    command=self._toggle_connect)
        self.conn_btn.pack(side=tk.LEFT, padx=4)
        self.dot = tk.Label(bar, text="●", bg=BG2, fg=ERROR, font=("Consolas",18))
        self.dot.pack(side=tk.LEFT, padx=6)
        self.status_lbl = tk.Label(bar, text="Disconnected", bg=BG2,
                                    fg=TEXT_DIM, font=FONT_UI)
        self.status_lbl.pack(side=tk.LEFT)
        rf = tk.Frame(bar, bg=BG2); rf.pack(side=tk.RIGHT, padx=10)
        for txt, sty, cmd in [
            ("▶ Run Flow", "Accent.TButton", self._run_flow),
            ("■ Stop",     "Warn.TButton",   self._stop_flow),
            ("New",        "Ghost.TButton",  self._new_flow),
            ("Open",       "Ghost.TButton",  self._open_flow),
            ("Save",       "Ghost.TButton",  self._save_flow),
            ("Save As",    "Ghost.TButton",  self._saveas_flow),
        ]:
            ttk.Button(rf, text=txt, style=sty, command=cmd).pack(side=tk.LEFT, padx=2)

    # ── LEFT PANEL ───────────────
    def _build_left(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        t1 = tk.Frame(nb, bg=BG2); nb.add(t1, text=" Axes ")
        t2 = tk.Frame(nb, bg=BG2); nb.add(t2, text=" Jog ")
        t3 = tk.Frame(nb, bg=BG2); nb.add(t3, text=" Templates ")
        self._build_axes_tab(t1)
        self._build_jog_tab(t2)
        self._build_templates_tab(t3)

    def _build_axes_tab(self, p):
        hdr = tk.Frame(p, bg=BG2); hdr.pack(fill=tk.X, padx=8, pady=(8,4))
        tk.Label(hdr, text="AXIS CONFIGURATION", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        ttk.Button(hdr, text="+ Add Axis", style="Ghost.TButton",
                   command=self._add_axis).pack(side=tk.RIGHT)
        self.axes_frame = tk.Frame(p, bg=BG2)
        self.axes_frame.pack(fill=tk.BOTH, expand=True, padx=8)
        self._render_axes()

    def _render_axes(self):
        for w in self.axes_frame.winfo_children(): w.destroy()
        hdr = tk.Frame(self.axes_frame, bg=BG3); hdr.pack(fill=tk.X, pady=(0,2))
        for t, w in [("Axis",5),("cm/step",10),("Enabled",7),("",4)]:
            tk.Label(hdr, text=t, bg=BG3, fg=TEXT_DIM,
                     font=FONT_UI9, width=w).pack(side=tk.LEFT, padx=4, pady=4)
        for name, cfg in self.axes.items():
            row = tk.Frame(self.axes_frame, bg=BG2); row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=name, bg=BG2, fg=ACCENT,
                     font=("Consolas",11,"bold"), width=5).pack(side=tk.LEFT, padx=4)
            sv = tk.StringVar(value=str(cfg["cm_per_step"]))
            tk.Entry(row, textvariable=sv, width=11, bg=BG3, fg=TEXT,
                     insertbackground=ACCENT, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1,
                     font=FONT_MONO).pack(side=tk.LEFT, padx=4, pady=4)
            sv.trace_add("write", lambda *a, n=name, s=sv: self._set_axis(n,s))
            bv = tk.BooleanVar(value=cfg["enabled"])
            tk.Checkbutton(row, variable=bv, bg=BG2, activebackground=BG2,
                           selectcolor=BG3, fg=ACCENT,
                           command=lambda n=name,v=bv: self._tog_axis(n,v)).pack(side=tk.LEFT, padx=6)
            if name not in ("X","Y","Z","U","A","B"):
                tk.Button(row, text="✕", bg=BG2, fg=ERROR, relief="flat", bd=0,
                          font=("Consolas",10), cursor="hand2",
                          command=lambda n=name: self._del_axis(n)).pack(side=tk.RIGHT, padx=4)

    def _set_axis(self, n, sv):
        try: self.axes[n]["cm_per_step"] = float(sv.get())
        except: pass
    def _tog_axis(self, n, bv): self.axes[n]["enabled"] = bv.get()
    def _del_axis(self, n):
        del self.axes[n]; self._render_axes()
    def _add_axis(self):
        d = tk.Toplevel(self); d.title("Add Axis"); d.geometry("260x130")
        d.configure(bg=BG2); d.resizable(False,False); d.grab_set()
        tk.Label(d, text="Axis name:", bg=BG2, fg=TEXT, font=FONT_UI).pack(padx=14, pady=(14,4), anchor="w")
        nv = tk.StringVar()
        e = tk.Entry(d, textvariable=nv, bg=BG3, fg=TEXT, relief="flat",
                     insertbackground=ACCENT, font=FONT_MONO,
                     highlightbackground=BORDER, highlightthickness=1)
        e.pack(padx=14, fill=tk.X); e.focus()
        def ok():
            nm = nv.get().strip().upper()
            if not nm or len(nm)>3: return messagebox.showerror("Error","1–3 chars", parent=d)
            if nm in self.axes:    return messagebox.showerror("Error","Already exists", parent=d)
            self.axes[nm] = {"cm_per_step":1.0,"enabled":True}
            self._render_axes(); d.destroy()
        tk.Button(d, text="Add", bg=ACCENT, fg=BG, relief="flat",
                  font=("Segoe UI Semibold",10), command=ok, cursor="hand2").pack(pady=10)
        e.bind("<Return>", lambda e: ok())

    def _build_jog_tab(self, p):
        tk.Label(p, text="JOG CONTROLS", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(padx=8, pady=(8,4), anchor="w")
        df = tk.Frame(p, bg=BG2); df.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(df, text="Step mm:", bg=BG2, fg=TEXT, font=FONT_UI).pack(side=tk.LEFT)
        self.jog_dist = tk.DoubleVar(value=1.0)
        tk.Spinbox(df, textvariable=self.jog_dist, from_=0.01, to=100, increment=0.5,
                   width=8, bg=BG3, fg=TEXT, relief="flat",
                   buttonbackground=BG3, insertbackground=ACCENT,
                   font=FONT_MONO).pack(side=tk.LEFT, padx=6)
        ff = tk.Frame(p, bg=BG2); ff.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(ff, text="Feed mm/m:", bg=BG2, fg=TEXT, font=FONT_UI).pack(side=tk.LEFT)
        self.jog_feed = tk.IntVar(value=1000)
        tk.Spinbox(ff, textvariable=self.jog_feed, from_=10, to=20000, increment=100,
                   width=8, bg=BG3, fg=TEXT, relief="flat",
                   buttonbackground=BG3, insertbackground=ACCENT,
                   font=FONT_MONO).pack(side=tk.LEFT, padx=6)
        pad = tk.Frame(p, bg=BG2); pad.pack(pady=8)
        jb = lambda t,r,c,cmd: tk.Button(pad, text=t, width=5, height=2,
            bg=BG3, fg=TEXT, relief="flat", activebackground=ACCENT,
            activeforeground=BG, font=("Segoe UI",11), cursor="hand2",
            command=cmd).grid(row=r, column=c, padx=3, pady=3)
        jb("Y+",0,1,lambda:self._jog("Y",+1))
        jb("X-",1,0,lambda:self._jog("X",-1))
        jb("⌂",1,1,self._home_all)
        jb("X+",1,2,lambda:self._jog("X",+1))
        jb("Y-",2,1,lambda:self._jog("Y",-1))
        zf = tk.Frame(p, bg=BG2); zf.pack(pady=4)
        for t, d in [("▲ Z+",+1),("▼ Z-",-1)]:
            tk.Button(zf, text=t, width=10, bg=BG3, fg=TEXT, relief="flat",
                      activebackground=ACCENT, activeforeground=BG,
                      font=FONT_UI, cursor="hand2",
                      command=lambda d=d:self._jog("Z",d)).pack(pady=2)
        of = tk.Frame(p, bg=BG2); of.pack(fill=tk.X, padx=8, pady=4)
        for ax in ["U","A","B"]:
            r = tk.Frame(of, bg=BG2); r.pack(fill=tk.X, pady=2)
            tk.Label(r, text=f"{ax}:", bg=BG2, fg=TEXT_DIM,
                     font=FONT_UI, width=3).pack(side=tk.LEFT)
            for t, d in [(f"◄{ax}-",-1),(f"{ax}+►",+1)]:
                tk.Button(r, text=t, width=7, bg=BG3, fg=TEXT, relief="flat",
                          activebackground=ACCENT, activeforeground=BG,
                          font=FONT_UI, cursor="hand2",
                          command=lambda a=ax, d=d:self._jog(a,d)).pack(side=tk.LEFT, padx=3)
        ttk.Button(p, text="Home All (G28)", style="Ghost.TButton",
                   command=self._home_all).pack(pady=6, fill=tk.X, padx=8)
        ttk.Button(p, text="Get Position (M114)", style="Ghost.TButton",
                   command=lambda:self._send_now("M114")).pack(pady=2, fill=tk.X, padx=8)
        ttk.Button(p, text="Endstops (M119)", style="Ghost.TButton",
                   command=lambda:self._send_now("M119")).pack(pady=2, fill=tk.X, padx=8)
        ttk.Button(p, text="Firmware Info (M115)", style="Ghost.TButton",
                   command=lambda:self._send_now("M115")).pack(pady=2, fill=tk.X, padx=8)

    def _jog(self, axis, direction):
        dist = self.jog_dist.get() * direction
        feed = self.jog_feed.get()
        for cmd in ["G91", f"G1 {axis}{dist:.4f} F{feed}", "G90"]:
            self._send_command(cmd)
        self._log(f"  Jog {axis}{'+'if direction>0 else ''}{dist:.3f} mm\n","cmd")
    def _home_all(self):
        self._send_command("G28"); self._log("  G28 Home All\n","cmd")
    def _send_now(self, cmd):
        self._send_command(cmd); self._log(f"  → {cmd}\n","cmd")

    def _build_templates_tab(self, p):
        tk.Label(p, text="FLOW TEMPLATES", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(padx=8, pady=(8,4), anchor="w")
        tk.Label(p, text="Click to load into Flow Editor", bg=BG2,
                 fg=TEXT_DIM, font=FONT_UI9).pack(padx=8, anchor="w")
        frm = tk.Frame(p, bg=BG2); frm.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        sb = ttk.Scrollbar(frm)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(frm, bg=BG3, fg=TEXT, relief="flat",
                        selectbackground=ACCENT, selectforeground=BG,
                        font=FONT_UI, yscrollcommand=sb.set,
                        highlightbackground=BORDER, highlightthickness=1,
                        activestyle="none", cursor="hand2")
        lb.pack(fill=tk.BOTH, expand=True)
        sb.configure(command=lb.yview)
        for name in TEMPLATES:
            lb.insert(tk.END, f"  {name}")
        def load(e):
            sel = lb.curselection()
            if not sel: return
            name = list(TEMPLATES.keys())[sel[0]]
            lines = TEMPLATES[name]
            if self.flow_lines:
                if not messagebox.askyesno("Load Template",
                    f"Replace current flow with\n'{name}'?\n({len(lines)} lines)"):
                    return
            self.flow_lines = list(lines)
            self.flow_title_lbl.configure(text=name)
            self._refresh_tree()
            self.current_file = None
            self._log(f"Loaded template: {name} ({len(lines)} lines)\n","info")
        lb.bind("<Double-1>", load)
        lb.bind("<Return>", load)
        ttk.Button(p, text="Load Selected Template", style="Accent.TButton",
                   command=lambda: load(None)).pack(fill=tk.X, padx=8, pady=6)

    # ── RIGHT PANEL ──────────────
    def _build_right(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        t1 = tk.Frame(nb, bg=BG);  nb.add(t1, text=" Flow Editor ")
        t2 = tk.Frame(nb, bg=BG);  nb.add(t2, text=" Terminal ")
        t3 = tk.Frame(nb, bg=BG);  nb.add(t3, text=" G-Code Reference ")
        self._build_flow_tab(t1)
        self._build_terminal_tab(t2)
        self._build_ref_tab(t3)

    # ── FLOW EDITOR ──────────────
    def _build_flow_tab(self, p):
        hdr = tk.Frame(p, bg=BG); hdr.pack(fill=tk.X, padx=6, pady=(4,0))
        self.flow_title_lbl = tk.Label(hdr, text="Untitled Flow", bg=BG,
                                        fg=TEXT, font=FONT_HEAD)
        self.flow_title_lbl.pack(side=tk.LEFT)
        self.flow_cnt = tk.Label(hdr, text="", bg=BG, fg=TEXT_DIM, font=FONT_UI)
        self.flow_cnt.pack(side=tk.LEFT, padx=10)
        br = tk.Frame(hdr, bg=BG); br.pack(side=tk.RIGHT)
        for t, s, c in [
            ("Add",    "Ghost.TButton", self._flow_add),
            ("Delete", "Ghost.TButton", self._flow_del),
            ("↑",      "Ghost.TButton", self._flow_up),
            ("↓",      "Ghost.TButton", self._flow_dn),
            ("Dup",    "Ghost.TButton", self._flow_dup),
            ("Clear",  "Warn.TButton",  self._flow_clear),
        ]:
            ttk.Button(br, text=t, style=s, command=c).pack(side=tk.LEFT, padx=1)
        pan = ttk.PanedWindow(p, orient=tk.HORIZONTAL)
        pan.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        lf = tk.Frame(pan, bg=BG2); pan.add(lf, weight=2)
        ef = tk.Frame(pan, bg=BG2); pan.add(ef, weight=1)
        # List
        cols = ("no","command","comment")
        self.tree = ttk.Treeview(lf, columns=cols, show="headings", selectmode="browse")
        for col, txt, w in [("no","#",40),("command","G-Code",200),("comment","Comment",140)]:
            self.tree.heading(col, text=txt, anchor="w")
            self.tree.column(col, width=w, stretch=(col!="no"))
        sb = ttk.Scrollbar(lf, command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self._tree_sel)
        self.tree.bind("<Double-1>", lambda e: self.edit_entry.focus())
        # Edit panel
        tk.Label(ef, text="EDIT LINE", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(8,4))
        tk.Label(ef, text="G-Code:", bg=BG2, fg=TEXT, font=FONT_UI).pack(anchor="w", padx=8)
        self.edit_var = tk.StringVar()
        self.edit_entry = tk.Entry(ef, textvariable=self.edit_var,
                                    bg=BG3, fg=TEXT, relief="flat",
                                    insertbackground=ACCENT, font=FONT_MONO,
                                    highlightbackground=BORDER, highlightthickness=1)
        self.edit_entry.pack(fill=tk.X, padx=8, pady=(0,8))
        self.edit_entry.bind("<Return>", lambda e: self._flow_update())
        tk.Label(ef, text="Comment:", bg=BG2, fg=TEXT, font=FONT_UI).pack(anchor="w", padx=8)
        self.cmt_var = tk.StringVar()
        tk.Entry(ef, textvariable=self.cmt_var, bg=BG3, fg=TEXT_DIM, relief="flat",
                 insertbackground=ACCENT, font=FONT_MONO,
                 highlightbackground=BORDER,
                 highlightthickness=1).pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(ef, text="Update Line", style="Accent.TButton",
                   command=self._flow_update).pack(fill=tk.X, padx=8, pady=2)
        ttk.Button(ef, text="▶ Run This Line", style="Blue.TButton",
                   command=self._flow_run_sel).pack(fill=tk.X, padx=8, pady=2)
        tk.Frame(ef, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        tk.Label(ef, text="RAW G-CODE IMPORT", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(0,4))
        self.raw_text = scrolledtext.ScrolledText(ef, bg=BG3, fg=TEXT, relief="flat",
            insertbackground=ACCENT, font=FONT_MONO2,
            highlightbackground=BORDER, highlightthickness=1,
            wrap=tk.WORD, width=30, height=14)
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,4))
        ttk.Button(ef, text="Import from Raw", style="Ghost.TButton",
                   command=self._import_raw).pack(fill=tk.X, padx=8, pady=4)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, line in enumerate(self.flow_lines, 1):
            cmd, *rest = line.split(";",1)
            cmt = rest[0].strip() if rest else ""
            cmd = cmd.strip()
            self.tree.insert("","end", iid=str(i), values=(i, cmd or f";{cmt}", cmt))
        self.flow_cnt.configure(text=f"{len(self.flow_lines)} lines")

    def _tree_sel(self, e):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        line = self.flow_lines[idx]
        cmd, *rest = line.split(";",1)
        self.edit_var.set(cmd.strip())
        self.cmt_var.set(rest[0].strip() if rest else "")

    def _flow_add(self):
        self.flow_lines.append("G0 X0 Y0")
        self._refresh_tree()
        iid = str(len(self.flow_lines))
        self.tree.selection_set(iid); self.tree.see(iid)
        self._tree_sel(None); self.edit_entry.focus()
    def _flow_del(self):
        sel = self.tree.selection()
        if not sel: return
        del self.flow_lines[int(sel[0])-1]; self._refresh_tree()
    def _flow_dup(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        self.flow_lines.insert(idx+1, self.flow_lines[idx])
        self._refresh_tree()
    def _flow_up(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        if idx>0:
            self.flow_lines[idx-1],self.flow_lines[idx] = self.flow_lines[idx],self.flow_lines[idx-1]
            self._refresh_tree(); iid=str(idx); self.tree.selection_set(iid)
    def _flow_dn(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        if idx<len(self.flow_lines)-1:
            self.flow_lines[idx],self.flow_lines[idx+1] = self.flow_lines[idx+1],self.flow_lines[idx]
            self._refresh_tree(); iid=str(idx+2); self.tree.selection_set(iid)
    def _flow_clear(self):
        if messagebox.askyesno("Clear","Remove all lines?"):
            self.flow_lines.clear(); self._refresh_tree()
    def _flow_update(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showinfo("Update","Select a line first.")
        idx = int(sel[0])-1
        cmd = self.edit_var.get().strip()
        cmt = self.cmt_var.get().strip()
        self.flow_lines[idx] = cmd + (f" ; {cmt}" if cmt else "")
        self._refresh_tree(); self.tree.selection_set(sel[0])
    def _flow_run_sel(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        cmd = self.flow_lines[idx].split(";")[0].strip()
        if cmd: self._send_command(cmd); self._log(f"  → {cmd}  [line {idx+1}]\n","flow")
    def _import_raw(self):
        raw = self.raw_text.get(1.0, tk.END).strip()
        if not raw: return
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if messagebox.askyesno("Import",f"Replace flow with {len(lines)} lines?"):
            self.flow_lines = lines; self._refresh_tree()
            self.raw_text.delete(1.0, tk.END)

    # ── TERMINAL ─────────────────
    def _build_terminal_tab(self, p):
        hdr = tk.Frame(p, bg=BG); hdr.pack(fill=tk.X, padx=6, pady=(4,0))
        tk.Label(hdr, text="SERIAL TERMINAL", bg=BG, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        ttk.Button(hdr, text="Clear", style="Ghost.TButton",
                   command=self._clear_term).pack(side=tk.RIGHT)
        self.terminal = scrolledtext.ScrolledText(p, bg="#060a10", fg="#b0ffb0",
            relief="flat", insertbackground=ACCENT, font=("Consolas",10),
            highlightbackground=BORDER, highlightthickness=1,
            state="disabled", wrap=tk.WORD)
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        for tag, color in [
            ("info","#5b9bd5"),("cmd","#00e5b0"),("resp","#7fff7f"),
            ("error","#ff3d6b"),("warn","#ffaa44"),("comment","#4a5270"),
            ("flow","#a78bfa"),("sys","#e879f9"),
        ]:
            self.terminal.tag_configure(tag, foreground=color)
        inp = tk.Frame(p, bg=BG2); inp.pack(fill=tk.X, padx=6, pady=6)
        self.cmd_var = tk.StringVar()
        self.cmd_entry = tk.Entry(inp, textvariable=self.cmd_var, bg=BG3, fg=TEXT,
                                   relief="flat", insertbackground=ACCENT,
                                   font=("Consolas",11),
                                   highlightbackground=ACCENT, highlightthickness=1)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6), ipady=7)
        self.cmd_entry.bind("<Return>", self._term_send)
        self.cmd_entry.bind("<Up>",     self._hist_up)
        self.cmd_entry.bind("<Down>",   self._hist_dn)
        ttk.Button(inp, text="Send", style="Accent.TButton",
                   command=self._term_send).pack(side=tk.LEFT, padx=(0,4))
        self.addflow_btn = ttk.Button(inp, text="+ Add to Flow",
                                       style="Ghost.TButton",
                                       command=self._add_to_flow,
                                       state="disabled")
        self.addflow_btn.pack(side=tk.LEFT)

    def _term_send(self, e=None):
        cmd = self.cmd_var.get().strip()
        if not cmd: return
        self.cmd_history.append(cmd); self.hist_idx = len(self.cmd_history)
        self.cmd_var.set("")
        tag = "comment" if cmd.startswith((";", "(")) else "cmd"
        self._log(f"  → {cmd}\n", tag)
        if self._valid_gcode(cmd):
            self.last_valid = cmd
            self.addflow_btn.configure(state="normal")
        else:
            self.addflow_btn.configure(state="disabled")
        self._send_command(cmd)

    def _valid_gcode(self, cmd):
        return bool(re.match(r"^[TGMFgm]\d", cmd.strip()))

    def _add_to_flow(self):
        if self.last_valid:
            self.flow_lines.append(self.last_valid)
            self._refresh_tree()
            self._log(f"  Added to flow: {self.last_valid}\n","flow")
            self.last_valid = None
            self.addflow_btn.configure(state="disabled")

    def _log(self, msg, tag="resp"):
        self.terminal.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        if tag in ("cmd","flow","sys"):
            self.terminal.insert(tk.END, f"[{ts}] ","comment")
        self.terminal.insert(tk.END, msg, tag)
        self.terminal.see(tk.END)
        self.terminal.configure(state="disabled")

    def _clear_term(self):
        self.terminal.configure(state="normal")
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state="disabled")

    def _hist_up(self, e):
        if self.hist_idx>0:
            self.hist_idx -= 1; self.cmd_var.set(self.cmd_history[self.hist_idx])
    def _hist_dn(self, e):
        if self.hist_idx<len(self.cmd_history)-1:
            self.hist_idx += 1; self.cmd_var.set(self.cmd_history[self.hist_idx])
        else:
            self.hist_idx = len(self.cmd_history); self.cmd_var.set("")

    # ── G-CODE REFERENCE ─────────
    def _build_ref_tab(self, p):
        # Top: category filter + search
        top = tk.Frame(p, bg=BG); top.pack(fill=tk.X, padx=6, pady=(6,4))
        tk.Label(top, text="Category:", bg=BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.LEFT)
        self.cat_var = tk.StringVar(value="All")
        cats = ["All"] + list(GCODE_DB.keys())
        self.cat_cb  = ttk.Combobox(top, textvariable=self.cat_var, values=cats,
                                     width=18, state="readonly")
        self.cat_cb.pack(side=tk.LEFT, padx=6)
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_ref())
        tk.Label(top, text="Search:", bg=BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.LEFT, padx=(10,0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_ref())
        tk.Entry(top, textvariable=self.search_var, bg=BG3, fg=TEXT, relief="flat",
                 insertbackground=ACCENT, font=FONT_MONO,
                 highlightbackground=BORDER, highlightthickness=1,
                 width=20).pack(side=tk.LEFT, padx=6)
        self.ref_count_lbl = tk.Label(top, text="", bg=BG, fg=TEXT_DIM, font=FONT_UI9)
        self.ref_count_lbl.pack(side=tk.RIGHT, padx=10)
        # Paned: list | detail
        pan = ttk.PanedWindow(p, orient=tk.HORIZONTAL)
        pan.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        lf = tk.Frame(pan, bg=BG2); pan.add(lf, weight=1)
        df = tk.Frame(pan, bg=BG2); pan.add(df, weight=1)
        # List treeview
        cols = ("cat","code","desc")
        self.ref_tree = ttk.Treeview(lf, columns=cols, show="headings",
                                      selectmode="browse")
        for col, txt, w in [("cat","Category",100),("code","Code",70),("desc","Description",200)]:
            self.ref_tree.heading(col, text=txt, anchor="w")
            self.ref_tree.column(col, width=w, stretch=(col=="desc"))
        sb = ttk.Scrollbar(lf, command=self.ref_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.ref_tree.configure(yscrollcommand=sb.set)
        self.ref_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.ref_tree.bind("<<TreeviewSelect>>", self._ref_select)
        # Detail panel
        tk.Label(df, text="CODE DETAIL", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(8,4))
        self.det_code = tk.Label(df, text="", bg=BG2, fg=ACCENT,
                                  font=("Consolas",18,"bold"))
        self.det_code.pack(anchor="w", padx=10, pady=(0,2))
        self.det_short = tk.Label(df, text="", bg=BG2, fg=TEXT,
                                   font=("Segoe UI Semibold",11))
        self.det_short.pack(anchor="w", padx=10)
        self.det_cat = tk.Label(df, text="", bg=BG2, fg=TEXT_DIM, font=FONT_UI9)
        self.det_cat.pack(anchor="w", padx=10, pady=(0,6))
        tk.Frame(df, bg=BORDER, height=1).pack(fill=tk.X, padx=8)
        tk.Label(df, text="Description:", bg=BG2, fg=TEXT_DIM,
                 font=FONT_UI9).pack(anchor="w", padx=10, pady=(8,2))
        self.det_desc = tk.Text(df, bg=BG3, fg=TEXT, relief="flat",
                                 font=FONT_UI, wrap=tk.WORD, height=5,
                                 highlightbackground=BORDER, highlightthickness=1,
                                 state="disabled")
        self.det_desc.pack(fill=tk.X, padx=8, pady=(0,6))
        tk.Label(df, text="Example:", bg=BG2, fg=TEXT_DIM,
                 font=FONT_UI9).pack(anchor="w", padx=10, pady=(4,2))
        self.det_ex = tk.Text(df, bg="#0a1020", fg=ACCENT, relief="flat",
                               font=FONT_MONO, wrap=tk.WORD, height=4,
                               highlightbackground=BORDER, highlightthickness=1,
                               state="disabled")
        self.det_ex.pack(fill=tk.X, padx=8, pady=(0,6))
        tk.Label(df, text="Parameters:", bg=BG2, fg=TEXT_DIM,
                 font=FONT_UI9).pack(anchor="w", padx=10, pady=(4,2))
        self.det_params = tk.Text(df, bg=BG3, fg=TEXT_MID, relief="flat",
                                   font=FONT_MONO2, wrap=tk.WORD, height=3,
                                   highlightbackground=BORDER, highlightthickness=1,
                                   state="disabled")
        self.det_params.pack(fill=tk.X, padx=8, pady=(0,8))
        # Buttons
        bf = tk.Frame(df, bg=BG2); bf.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(bf, text="Send to Terminal", style="Accent.TButton",
                   command=self._ref_send_terminal).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Add to Flow", style="Blue.TButton",
                   command=self._ref_add_flow).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Copy Example", style="Ghost.TButton",
                   command=self._ref_copy).pack(side=tk.LEFT, padx=4)
        self._ref_items = []  # cache for filter
        self._populate_ref()

    def _populate_ref(self):
        self.ref_tree.delete(*self.ref_tree.get_children())
        self._ref_items.clear()
        query  = self.search_var.get().lower().strip() if hasattr(self,'search_var') else ""
        filter_cat = self.cat_var.get() if hasattr(self,'cat_var') else "All"
        count  = 0
        for cat, codes in GCODE_DB.items():
            if filter_cat != "All" and cat != filter_cat:
                continue
            color = CAT_COLORS.get(cat, TEXT_DIM)
            for code, short, full, example, params in codes:
                if query and query not in code.lower() \
                         and query not in short.lower() \
                         and query not in full.lower():
                    continue
                iid = f"{cat}|{code}|{count}"
                self.ref_tree.insert("","end", iid=iid,
                                      values=(cat, code, short),
                                      tags=(cat,))
                self._ref_items.append((iid, cat, code, short, full, example, params))
                count += 1
            self.ref_tree.tag_configure(cat, foreground=color)
        self.ref_count_lbl.configure(text=f"{count} codes")

    def _filter_ref(self):
        self._populate_ref()

    def _ref_select(self, e):
        sel = self.ref_tree.selection()
        if not sel: return
        iid = sel[0]
        for item in self._ref_items:
            if item[0] == iid:
                _, cat, code, short, full, example, params = item
                self.det_code.configure(text=code,
                    fg=CAT_COLORS.get(cat, ACCENT))
                self.det_short.configure(text=short)
                self.det_cat.configure(text=f"Category: {cat}")
                for widget, txt in [
                    (self.det_desc, full),
                    (self.det_ex,   example),
                    (self.det_params, params),
                ]:
                    widget.configure(state="normal")
                    widget.delete(1.0, tk.END)
                    widget.insert(1.0, txt)
                    widget.configure(state="disabled")
                self._current_example = example.split("\n")[0].split(";")[0].strip()
                self._current_code    = code
                break

    def _ref_send_terminal(self):
        if hasattr(self,'_current_example') and self._current_example:
            self.cmd_var.set(self._current_example)
            self.cmd_entry.focus()
    def _ref_add_flow(self):
        if hasattr(self,'_current_example') and self._current_example:
            self.flow_lines.append(self._current_example)
            self._refresh_tree()
            self._log(f"  Added to flow: {self._current_example}\n","flow")
    def _ref_copy(self):
        if hasattr(self,'_current_example'):
            self.clipboard_clear()
            self.clipboard_append(self._current_example)
            self._log(f"  Copied: {self._current_example}\n","sys")

    # ════════════════════════════
    
    #  SERIAL
    # ════════════════════════════
    def _scan_ports(self):
        ports = serial.tools.list_ports.comports() if SERIAL_AVAILABLE else MockPorts.comports() # type: ignore
        self._port_list = [p.device for p in ports]
        names = [f"{p.device} — {p.description}" for p in ports]
        self.port_cb["values"] = names
        if names: self.port_cb.current(0)
        self._log(f"Found {len(names)} port(s).\n","sys")

    def _toggle_connect(self):
        if self.connected: self._disconnect()
        else: self._connect()

    def _connect(self):
        idx = self.port_cb.current()
        if idx<0 or not self._port_list:
            return messagebox.showerror("Error","Select a port.")
        port = self._port_list[idx]
        baud = int(self.baud_var.get())
        try:
            self.serial_conn = serial.Serial(port, baud, timeout=2) if SERIAL_AVAILABLE else MockSerial()  # type: ignore
            self.connected = True
            self.conn_btn.configure(text="Disconnect")
            self.dot.configure(fg=SUCCESS)
            self.status_lbl.configure(fg=SUCCESS, text=f"Connected  {port} @ {baud}")
            self._log(f"Connected to {port} at {baud} baud.\n","sys")
            threading.Thread(target=self._read_loop, daemon=True).start()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            self._log(f"Connection failed: {ex}\n","error")

    def _disconnect(self):
        try: self.serial_conn and self.serial_conn.close() # type: ignore
        except KeyError as e:
            logging.exception('error while accessing the dict')
            raise e
        self.serial_conn = None; self.connected = False
        self.conn_btn.configure(text="Connect")
        self.dot.configure(fg=ERROR)
        self.status_lbl.configure(fg=TEXT_DIM, text="Disconnected")
        self._log("Disconnected.\n","warn")

    def _read_loop(self):
        while self.connected and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline()
                if line:
                    txt = line.decode("utf-8", errors="replace").strip()
                    if txt: self.after(0, self._log, f"  ← {txt}\n", "resp")
            except Exception:
                break

    def _send_command(self, cmd):
        cmd = cmd.strip()
        if not cmd: return
        if not self.connected:
            self._log("Not connected.\n","error"); return
        try: self.serial_conn.write((cmd+"\n").encode()) # type: ignore
        except Exception as ex: self._log(f"Send error: {ex}\n","error")

    # ════════════════════════════
    #  FLOW RUN
    # ════════════════════════════
    def _run_flow(self):
        if not self.flow_lines: return messagebox.showinfo("Run","Flow is empty.")
        if not self.connected:  return messagebox.showwarning("Run","Not connected.")
        if self.running_flow:   return
        self.running_flow = True
        threading.Thread(target=self._runner, daemon=True).start()

    def _runner(self):
        self.after(0, self._log,"▶ Flow started...\n","flow")
        for i, line in enumerate(self.flow_lines):
            if not self.running_flow:
                self.after(0, self._log,"■ Flow stopped.\n","warn"); return
            cmd = line.split(";")[0].strip()
            if not cmd: continue
            iid = str(i+1)
            self.after(0, self.tree.selection_set, iid)
            self.after(0, self.tree.see, iid)
            self.after(0, self._log, f"  [{i+1}/{len(self.flow_lines)}] → {cmd}\n","flow")
            self._send_command(cmd)
            time.sleep(0.06)
        self.running_flow = False
        self.after(0, self._log,"✓ Flow complete.\n","info")

    def _stop_flow(self): self.running_flow = False

    # ════════════════════════════
    #  FILE OPS
    # ════════════════════════════
    def _new_flow(self):
        if self.flow_lines:
            if not messagebox.askyesno("New","Discard current flow?"): return
        self.flow_lines.clear(); self.current_file = None
        self.flow_title_lbl.configure(text="Untitled Flow")
        self._refresh_tree()

    def _open_flow(self):
        path = filedialog.askopenfilename(title="Open G-Code",
            filetypes=[("G-Code","*.gcode"),("All","*.*")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                self.flow_lines = [l.rstrip("\n") for l in f if l.strip()]
            self.current_file = path
            self.flow_title_lbl.configure(text=os.path.basename(path))
            self._refresh_tree()
            self.raw_text.delete(1.0, tk.END)
            self.raw_text.insert(1.0,"\n".join(self.flow_lines))
            self._log(f"Loaded: {path} ({len(self.flow_lines)} lines)\n","sys")
        except Exception as ex: messagebox.showerror("Error",str(ex))

    def _save_flow(self):
        if self.current_file: self._write(self.current_file)
        else: self._saveas_flow()

    def _saveas_flow(self):
        path = filedialog.asksaveasfilename(title="Save As",
            defaultextension=".gcode",
            filetypes=[("G-Code","*.gcode"),("All","*.*")])
        if path: self._write(path)

    def _write(self, path):
        try:
            with open(path,"w",encoding="utf-8") as f:
                f.write("\n".join(self.flow_lines)+"\n")
            self.current_file = path
            self.flow_title_lbl.configure(text=os.path.basename(path))
            self._log(f"Saved: {path}\n","sys")
        except Exception as ex: messagebox.showerror("Error",str(ex))

    def on_close(self):
        self._disconnect(); self.destroy()


if __name__ == "__main__":
    app = CNCController()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

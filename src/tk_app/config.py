"""Application configuration and shared UI constants."""

APP_NAME = "CNC_robot_control"
APP_TITLE = "Universal G-Code Controller"
APP_VERSION = "0.1.0"
DEFAULT_BAUD_RATE = "115200"
DEFAULT_WINDOW_SIZE = "1400x880"
MIN_WINDOW_SIZE = (1200, 750)

BG = "#0a0d14"
BG2 = "#111520"
BG3 = "#181d2e"
BG4 = "#1e2438"
ACCENT = "#00e5b0"
ACCENT2 = "#3b9eff"
ACCENT3 = "#c084fc"
WARN = "#ff7043"
SUCCESS = "#00e5b0"
ERROR = "#ff3d6b"
TEXT = "#dde3f0"
TEXT_DIM = "#586280"
TEXT_MID = "#8896b3"
BORDER = "#252d47"

CAT_COLORS = {
    "Motion": "#3b9eff",
    "Coordinates": "#00e5b0",
    "Homing": "#a78bfa",
    "Bed Leveling": "#f59e0b",
    "BLTouch": "#ec4899",
    "Sensors": "#10b981",
    "Temperature": "#f97316",
    "Fans": "#06b6d4",
    "Spindle": "#84cc16",
    "Extruder": "#fb923c",
    "Stepper": "#818cf8",
    "EEPROM": "#fbbf24",
    "Display": "#e879f9",
    "SD Card": "#4ade80",
    "Control": "#f43f5e",
    "Filament": "#fb7185",
    "Power": "#facc15",
    "Debug": "#94a3b8",
    "CNC Specific": "#22d3ee",
    "Laser": "#ff6b6b",
    "Delta": "#a3e635",
    "Linear Adv": "#c084fc",
    "Input Shape": "#67e8f9",
    "Custom": "#cbd5e1",
}

FONT_MONO = ("Consolas", 10)
FONT_MONO2 = ("Consolas", 9)
FONT_UI = ("Segoe UI", 10)
FONT_UI9 = ("Segoe UI", 9)
FONT_HEAD = ("Segoe UI Semibold", 11)
FONT_CODE = ("Consolas", 11)

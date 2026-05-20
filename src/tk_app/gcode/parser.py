"""Small G-code parsing and validation helpers."""

import re

GCODE_COMMAND_PATTERN = re.compile(r"^[TGMFgm]\d")


def is_valid_gcode(command: str) -> bool:
    """Return True when a command starts with a known G-code style prefix."""

    return bool(GCODE_COMMAND_PATTERN.match(command.strip()))

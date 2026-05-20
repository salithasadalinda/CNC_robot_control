"""Serial communication helpers and offline mock objects."""

import time

try:
    import serial
    import serial.tools.list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    SERIAL_AVAILABLE = False


class MockSerial:
    """Minimal serial-compatible object for offline UI testing."""

    def __init__(self):
        self.is_open = True

    def write(self, data):
        pass

    def readline(self):
        time.sleep(0.04)
        return b"ok\n"

    def close(self):
        self.is_open = False


class MockPorts:
    """Mock serial port provider used when pyserial is unavailable."""

    @staticmethod
    def comports():
        class Port:
            def __init__(self, device, description):
                self.device = device
                self.description = description

        return [
            Port("COM1", "Mock CNC (Marlin)"),
            Port("COM2", "Mock GRBL 1.1"),
        ]

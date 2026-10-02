"""Win32 Input Injector for remote mouse, keyboard, and touch events."""

import ctypes
import logging
import time
from typing import Dict

logger = logging.getLogger("airscreen.input")
user32 = ctypes.windll.user32

# Mouse flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0009
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

# Keyboard flags
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]

VKEY_MAP: Dict[str, int] = {
    # System & Editing
    "Backspace": 0x08,
    "Tab": 0x09,
    "Enter": 0x0D,
    "Return": 0x0D,
    "Escape": 0x1B,
    "Esc": 0x1B,
    "Space": 0x20,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "End": 0x23,
    "Home": 0x24,
    "ArrowLeft": 0x25,
    "ArrowUp": 0x26,
    "ArrowRight": 0x27,
    "ArrowDown": 0x28,
    "PrintScreen": 0x2C,
    "Snapshot": 0x2C,
    "Insert": 0x2D,
    "Delete": 0x2E,
    "Del": 0x2E,

    # Modifiers
    "Shift": 0x10,
    "Control": 0x11,
    "Ctrl": 0x11,
    "Alt": 0x12,
    "Menu": 0x12,
    "Win": 0x5B,
    "Windows": 0x5B,
    "Meta": 0x5B,
    "Super": 0x5B,

    # Volume & Media
    "VolumeMute": 0xAD,
    "VolumeDown": 0xAE,
    "VolumeUp": 0xAF,
    "MediaNext": 0xB0,
    "MediaPrev": 0xB1,
    "MediaPlayPause": 0xB3,
    "PlayPause": 0xB3,
}

# Add alphanumeric keys dynamically
for code in range(ord('0'), ord('9') + 1):
    VKEY_MAP[chr(code)] = code

for code in range(ord('A'), ord('Z') + 1):
    VKEY_MAP[chr(code)] = code
    VKEY_MAP[chr(code).lower()] = code

# Add Function keys F1-F12
for i in range(1, 13):
    VKEY_MAP[f"F{i}"] = 0x6F + i
    VKEY_MAP[f"f{i}"] = 0x6F + i


class InputInjector:
    """High-performance Windows input simulator using native SendInput APIs."""

    @staticmethod
    def set_cursor_pos(target_x: int, target_y: int):
        user32.SetCursorPos(target_x, target_y)

    @staticmethod
    def mouse_down(button: str = "left"):
        flag = MOUSEEVENTF_LEFTDOWN
        if button == "right":
            flag = MOUSEEVENTF_RIGHTDOWN
        elif button == "middle":
            flag = MOUSEEVENTF_MIDDLEDOWN
        user32.mouse_event(flag, 0, 0, 0, 0)

    @staticmethod
    def mouse_up(button: str = "left"):
        flag = MOUSEEVENTF_LEFTUP
        if button == "right":
            flag = MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            flag = MOUSEEVENTF_MIDDLEUP
        user32.mouse_event(flag, 0, 0, 0, 0)

    @staticmethod
    def mouse_click(button: str = "left"):
        InputInjector.mouse_down(button)
        time.sleep(0.015)
        InputInjector.mouse_up(button)

    @staticmethod
    def mouse_wheel(delta_y: float):
        # 1 standard wheel tick in Windows is 120 units
        val = int(-delta_y * 120)
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, val, 0)

    @staticmethod
    def type_unicode_text(text: str):
        for char in text:
            code = ord(char)
            inp_down = INPUT(type=1)
            inp_down.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=None)
            inp_up = INPUT(type=1)
            inp_up.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
            events = (INPUT * 2)(inp_down, inp_up)
            user32.SendInput(2, events, ctypes.sizeof(INPUT))
            time.sleep(0.003)

    @staticmethod
    def send_key(key_name: str):
        vk = VKEY_MAP.get(key_name)
        if not vk:
            return
        inp_down = INPUT(type=1)
        inp_down.union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
        inp_up = INPUT(type=1)
        inp_up.union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
        events = (INPUT * 2)(inp_down, inp_up)
        user32.SendInput(2, events, ctypes.sizeof(INPUT))

    @staticmethod
    def send_hotkey(keys: list):
        """Presses multiple keys down in sequence, then releases in reverse order."""
        if not keys:
            return
        vks = []
        for k in keys:
            vk = VKEY_MAP.get(k) or VKEY_MAP.get(str(k).capitalize())
            if vk:
                vks.append(vk)

        if not vks:
            return

        # Press down in order
        for vk in vks:
            inp = INPUT(type=1)
            inp.union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.01)

        time.sleep(0.02)

        # Release in reverse order
        for vk in reversed(vks):
            inp = INPUT(type=1)
            inp.union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.005)


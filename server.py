import asyncio
import ctypes
from ctypes import wintypes
import io
import json
import logging
import os
import socket
import sys
import threading
import time
from typing import Dict, List, Optional

import cv2
import mss
import numpy as np
import psutil
import qrcode
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Set console output encoding to utf-8 for proper QR display
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure Windows DPI awareness for 1:1 pixel accuracy
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32

# Win32 Constants & Mouse/Keyboard Input Structures
SM_CXSCREEN = 0
SM_CYSCREEN = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0009
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

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

VK_MAP = {
    "Backspace": 0x08,
    "Tab": 0x09,
    "Enter": 0x0D,
    "Escape": 0x1B,
    "Space": 0x20,
    "ArrowLeft": 0x25,
    "ArrowUp": 0x26,
    "ArrowRight": 0x27,
    "ArrowDown": 0x28,
    "Delete": 0x2E,
}

class InputController:
    """Handles mouse and keyboard inputs sent wirelessly, mapped to the active monitor."""

    active_monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @classmethod
    def set_active_monitor(cls, mon: Dict):
        cls.active_monitor = mon

    @classmethod
    def set_cursor_pos(cls, x_pct: float, y_pct: float):
        mon = cls.active_monitor
        target_x = mon["left"] + max(0, min(mon["width"] - 1, int(x_pct * mon["width"])))
        target_y = mon["top"] + max(0, min(mon["height"] - 1, int(y_pct * mon["height"])))
        user32.SetCursorPos(target_x, target_y)

    @classmethod
    def mouse_down(cls, button: str = "left"):
        flag = MOUSEEVENTF_LEFTDOWN
        if button == "right":
            flag = MOUSEEVENTF_RIGHTDOWN
        elif button == "middle":
            flag = MOUSEEVENTF_MIDDLEDOWN
        user32.mouse_event(flag, 0, 0, 0, 0)

    @classmethod
    def mouse_up(cls, button: str = "left"):
        flag = MOUSEEVENTF_LEFTUP
        if button == "right":
            flag = MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            flag = MOUSEEVENTF_MIDDLEUP
        user32.mouse_event(flag, 0, 0, 0, 0)

    @classmethod
    def mouse_click(cls, button: str = "left"):
        cls.mouse_down(button)
        time.sleep(0.015)
        cls.mouse_up(button)

    @classmethod
    def mouse_wheel(cls, delta_y: float):
        val = int(-delta_y * 120)
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, val, 0)

    @classmethod
    def type_text(cls, text: str):
        for char in text:
            code = ord(char)
            inp_down = INPUT(type=1)
            inp_down.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=None)
            inp_up = INPUT(type=1)
            inp_up.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
            events = (INPUT * 2)(inp_down, inp_up)
            user32.SendInput(2, events, ctypes.sizeof(INPUT))
            time.sleep(0.005)

    @classmethod
    def send_special_key(cls, key_name: str):
        vk = VK_MAP.get(key_name)
        if not vk:
            return
        inp_down = INPUT(type=1)
        inp_down.union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
        inp_up = INPUT(type=1)
        inp_up.union.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
        events = (INPUT * 2)(inp_down, inp_up)
        user32.SendInput(2, events, ctypes.sizeof(INPUT))


class ScreenStreamEngine:
    """Captures any monitor (Main or Extended Display) and streams at low latency."""

    def __init__(self):
        self.running = False
        self.lock = threading.Lock()
        self.latest_jpeg: Optional[bytes] = None
        self.frame_id: int = 0
        self.scale: float = 0.75
        self.jpeg_quality = 65
        self.fps_cap = 45
        self.capture_thread: Optional[threading.Thread] = None
        self.selected_monitor_idx = 1
        self._refresh_monitors()

        # If a second monitor exists, default to Monitor 2 (Extended Display)!
        if len(self.monitors_list) > 1:
            self.selected_monitor_idx = 2
            print(f"[Multi-Monitor] Extended Display 2 detected! Defaulting to Display 2.")

        self._update_input_controller()

    def _refresh_monitors(self):
        self.monitors_list = []
        with mss.MSS() as sct:
            for i, m in enumerate(sct.monitors):
                if i > 0:  # Skip monitor 0 (which is all monitors combined)
                    label = f"Display {i}" + (" (Extended)" if i > 1 else " (Main)")
                    self.monitors_list.append({
                        "id": i,
                        "name": label,
                        "left": m["left"],
                        "top": m["top"],
                        "width": m["width"],
                        "height": m["height"]
                    })

    def get_monitors(self) -> List[Dict]:
        self._refresh_monitors()
        return self.monitors_list

    def get_current_monitor_info(self) -> Dict:
        for m in self.monitors_list:
            if m["id"] == self.selected_monitor_idx:
                return m
        return self.monitors_list[0] if self.monitors_list else {"left": 0, "top": 0, "width": 1920, "height": 1080}

    def _update_input_controller(self):
        mon = self.get_current_monitor_info()
        InputController.set_active_monitor(mon)

    def set_monitor(self, idx: int):
        self._refresh_monitors()
        valid_ids = [m["id"] for m in self.monitors_list]
        if idx in valid_ids:
            with self.lock:
                self.selected_monitor_idx = idx
                self._update_input_controller()
            print(f"[Display Switched] Now streaming Display {idx}")

    def set_settings(self, quality: int, scale: float):
        self.scale = max(0.4, min(1.0, scale))
        self.jpeg_quality = max(30, min(95, quality))
        print(f"[Settings Update] Scale: {self.scale*100:.0f}%, Quality: {self.jpeg_quality}%")

    def start(self):
        if self.running:
            return
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def _capture_loop(self):
        # Attach thread to interactive desktop session
        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)

        sct = mss.MSS()
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        last_quality = self.jpeg_quality

        while self.running:
            loop_start = time.perf_counter()
            frame = None

            try:
                mon_idx = self.selected_monitor_idx
                if mon_idx >= len(sct.monitors):
                    mon_idx = 1
                mon = sct.monitors[mon_idx]
                sct_img = sct.grab(mon)
                raw = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape((sct_img.height, sct_img.width, 4))
                frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
            except Exception:
                time.sleep(0.02)
                continue

            if frame is not None:
                h, w = frame.shape[:2]
                target_w = int(w * self.scale)
                target_h = int(h * self.scale)
                if self.scale < 0.98:
                    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

                if last_quality != self.jpeg_quality:
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                    last_quality = self.jpeg_quality

                success, buffer = cv2.imencode(".jpg", frame, encode_param)
                if success:
                    jpeg_bytes = buffer.tobytes()
                    with self.lock:
                        self.latest_jpeg = jpeg_bytes
                        self.frame_id += 1

            # Sleep to maintain target FPS
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0.001, (1.0 / self.fps_cap) - elapsed)
            time.sleep(sleep_time)


app = FastAPI(title="AirScreen Wireless Display")
stream_engine = ScreenStreamEngine()

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def on_startup():
    stream_engine.start()

@app.get("/")
def get_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    curr_mon = stream_engine.get_current_monitor_info()
    await websocket.send_text(json.dumps({
        "type": "init",
        "monitors": stream_engine.get_monitors(),
        "selectedMonitor": stream_engine.selected_monitor_idx,
        "screenWidth": curr_mon["width"],
        "screenHeight": curr_mon["height"],
        "quality": stream_engine.jpeg_quality
    }))

    # Frame streaming task with ACK / backpressure control
    client_ready = asyncio.Event()
    client_ready.set()
    last_sent_frame_id = -1
    is_active = True

    async def sender_task():
        nonlocal last_sent_frame_id, is_active
        while is_active:
            try:
                # Wait until client acknowledged previous frame (prevents Wi-Fi buffer pile-up)
                await client_ready.wait()
                client_ready.clear()

                # Get latest frame
                curr_frame_id = stream_engine.frame_id
                if curr_frame_id == last_sent_frame_id or stream_engine.latest_jpeg is None:
                    await asyncio.sleep(0.005)
                    client_ready.set()
                    continue

                with stream_engine.lock:
                    data = stream_engine.latest_jpeg
                    last_sent_frame_id = curr_frame_id

                if data:
                    await websocket.send_bytes(data)
            except Exception:
                break

    sender = asyncio.create_task(sender_task())

    try:
        while True:
            raw_msg = await websocket.receive_text()
            msg = json.loads(raw_msg)
            m_type = msg.get("type")

            if m_type == "ack":
                client_ready.set()

            elif m_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "t": msg.get("t")}))

            elif m_type == "select_monitor":
                idx = int(msg.get("idx", 1))
                stream_engine.set_monitor(idx)
                curr_mon = stream_engine.get_current_monitor_info()
                await websocket.send_text(json.dumps({
                    "type": "monitor_changed",
                    "selectedMonitor": stream_engine.selected_monitor_idx,
                    "screenWidth": curr_mon["width"],
                    "screenHeight": curr_mon["height"]
                }))

            elif m_type == "mouse_move":
                InputController.set_cursor_pos(msg["x"], msg["y"])

            elif m_type == "mouse_down":
                InputController.set_cursor_pos(msg["x"], msg["y"])
                InputController.mouse_down(msg.get("button", "left"))

            elif m_type == "mouse_up":
                InputController.set_cursor_pos(msg["x"], msg["y"])
                InputController.mouse_up(msg.get("button", "left"))

            elif m_type == "click":
                InputController.set_cursor_pos(msg["x"], msg["y"])
                InputController.mouse_click(msg.get("button", "left"))

            elif m_type == "wheel":
                InputController.mouse_wheel(msg.get("deltaY", 0))

            elif m_type == "type_text":
                InputController.type_text(msg.get("text", ""))

            elif m_type == "key":
                InputController.send_special_key(msg.get("key", ""))

            elif m_type == "settings":
                quality = int(msg.get("quality", 65))
                scale = float(msg.get("scale", 0.75))
                stream_engine.set_settings(quality, scale)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket Error]: {e}")
    finally:
        is_active = False
        sender.cancel()
        print("[Client Disconnected]")


def get_local_wifi_ip() -> str:
    wifi_ip = None
    fallback_ip = None
    for iface, addrs in psutil.net_if_addrs().items():
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith("127."):
                if a.address.startswith("169.254."):
                    continue
                name_low = iface.lower()
                if "wi-fi" in name_low or "wlan" in name_low or "wireless" in name_low:
                    wifi_ip = a.address
                elif not fallback_ip and "virtual" not in name_low and "vethernet" not in name_low:
                    fallback_ip = a.address
    return wifi_ip or fallback_ip or "127.0.0.1"


def find_available_port(preferred_port: int = 8000) -> int:
    for p in range(preferred_port, preferred_port + 20):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", p))
            s.close()
            return p
        except OSError:
            continue
    return preferred_port


def print_banner(ip: str, port: int):
    url = f"http://{ip}:{port}"
    try:
        qr_img = qrcode.make(url)
        qr_path = os.path.join(STATIC_DIR, "qr.png")
        qr_img.save(qr_path)
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("      🚀 AIRSCREEN - WIRELESS SECOND DISPLAY SERVER 🚀")
    print("=" * 60)
    print(f"\n📡 Connect your Phone / Tablet to the SAME Wi-Fi network.")
    print(f"📱 Open your mobile browser and go to:")
    print(f"\n   👉 \033[1;32m{url}\033[0m 👈\n")
    print("📷 Or scan this QR Code with your phone camera:")
    print("-" * 60)
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.print_ascii(invert=True)
    except Exception:
        pass
    print("-" * 60)
    print("✨ Features:")
    print("  • Extended Display & Multi-Monitor Support")
    print("  • Ultra-low latency GPU capture (DXGI / Direct3D)")
    print("  • Touch-to-click & Trackpad mode for PC mouse control")
    print("  • Wireless keyboard typing from phone")
    print("  • Fullscreen borderless display mode")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    ip = get_local_wifi_ip()
    port = find_available_port(8000)
    print_banner(ip, port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

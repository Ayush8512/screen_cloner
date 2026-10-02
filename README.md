# AirScreen :: Professional Low-Latency Wireless Display & Control Suite

AirScreen is an end-to-end, commercial-grade software suite designed to clone and extend Windows displays to mobile phones, iPads, Android tablets, and remote browsers over local Wi-Fi with ultra-low latency, zero cables, and zero browser bloat.

---

## Key Architecture & Capabilities

### 1. AirScreen Host (Workstation Control Center)
- **Native Desktop GUI**: Powered by `pywebview` using the Windows Edge WebView2 engine — no black command prompts needed.
- **Windows System Tray Daemon**: Runs silently in the background near the Windows clock (`pystray`). Clean menu for opening control center, copying connection links, and toggling display modes.
- **High-Res QR Code & Wi-Fi Selector**: Automatic IP resolution with dropdown switcher for Wi-Fi, Ethernet, and Mobile Hotspot interfaces.
- **1-Click Virtual Display Driver (VDD)**: Easily install, enable, or remove genuine secondary Windows monitors (Display 2) for real drag-and-drop multitasking.
- **Live Monitor Thumbnail Previews**: Real-time visual thumbnails of Monitor 1 and Monitor 2 with one-click broadcast switching.
- **Connected Devices Monitor**: View connected client devices (iPad, iPhone, Android, Laptop), live ping latency, and disconnect rogue devices with one click.

### 2. AirScreen Client (Standalone PWA Receiver)
- **1-Tap PWA Installation**: Installs directly onto Android, iPadOS/iOS home screens as a standalone native app (100% fullscreen, zero browser address bars).
- **Floating Action Pill**: Draggable, auto-dimming translucent HUD displaying live FPS, latency, and monitor status.
- **Slide-Up Multi-Tool Drawer**:
  - **Display Tab**: Monitor switcher (Display 1 / Display 2), 540p / 720p / 1080p quality presets, screen fit mode (Letterbox / Stretch to fill), fullscreen toggle, and virtual keyboard trigger.
  - **Virtual Trackpad Tab**: Dedicated touchpad surface with Left-Click, Right-Click, and Middle-Click buttons, tactile scroll bar, kinetic inertia momentum, and sensitivity adjustment slider.
  - **Windows Shortcuts Tab**: Instant access to `Win` (Start), `Win + D` (Show Desktop), `Alt + Tab` (App Switcher), `Ctrl + Shift + Esc` (Task Manager), `Win + P` (Project Display), `Ctrl + C / V / Z / A`, Arrow keys, and editing keys.
  - **Media Tab**: Windows volume control (`Vol +`, `Vol -`, `Mute`) and playback controls (`Prev`, `Play/Pause`, `Next`).
  - **Gesture Help Tab**: Quick reference card for touch gestures with minimalist SVG diagrams.
- **Pinch-to-Zoom & Pan**: Multi-touch zoom up to 3.5x to read tiny code or spreadsheet text on mobile screens, with drag panning and a "Reset 1:1" button.
- **Screen Wake Lock & Haptics**: Keeps the mobile screen awake while streaming, with subtle vibration feedback on button presses.

---

## System Architecture

```
wireless_display/
├── airscreen/                        # Modular Core Engine
│   ├── config.py                     # Configuration & streaming profiles
│   ├── app.py                        # FastAPI application & REST APIs
│   ├── core/
│   │   ├── display.py                # DPI awareness & monitor enumeration
│   │   ├── capture.py                # DXGI GPU Duplication / MSS GDI + Thumbnail generator
│   │   ├── encoder.py                # Hardware-accelerated JPEG frame compressor
│   │   └── input.py                  # Win32 SendInput controller (Mouse, Keyboard, Hotkeys)
│   ├── gui/
│   │   ├── window.py                 # PyWebView native desktop window manager
│   │   └── tray.py                   # Pystray background system tray daemon
│   └── network/
│       ├── discovery.py              # Multi-interface discovery & IP resolver
│       ├── protocol.py               # Typed protocol schemas (Handshake, Hotkeys, Telemetry)
│       └── session.py                # Client session manager & flow control
├── static/                           # Client Web Application & Host Dashboard
│   ├── manifest.json                 # PWA Web App Manifest
│   ├── sw.js                         # PWA Service Worker for offline caching
│   ├── icon.svg                      # High-res vector application icon
│   ├── index.html                    # Mobile/Tablet touch receiver client
│   ├── dashboard.html                # Host desktop control center dashboard
│   ├── css/
│   │   ├── main.css                  # Mobile client obsidian stylesheet
│   │   └── dashboard.css             # Host control center dark zinc stylesheet
│   └── js/
│       ├── connection.js             # WebSocket client & telemetry ping
│       ├── renderer.js               # Canvas frame renderer (ImageBitmap)
│       ├── controls.js               # Touch gestures, trackpad, pinch-to-zoom & haptics
│       ├── app.js                    # Mobile UI orchestrator & PWA installer
│       └── dashboard.js              # Host dashboard controller & monitor switcher
├── virtual_display_driver/           # VDD Driver and Control utilities
├── build_app.py                      # PyInstaller standalone executable builder
├── launch_airscreen.bat              # 1-Click desktop launcher
├── start_airscreen.bat               # Interactive menu launcher
└── main.py                           # CLI & Application entry point
```

---

## Quick Start

### Option 1: 1-Click Desktop Launcher
Double-click **`launch_airscreen.bat`** to start AirScreen immediately with the modern Desktop Control Center and System Tray icon.

### Option 2: Interactive Menu Launcher
Double-click **`start_airscreen.bat`** and select:
- `1` to run the Desktop Control Center + System Tray.
- `2` to run in Headless / Console Mode.
- `3` to install/enable Virtual Display Driver (Display 2).
- `4` to manage Virtual Display Settings.
- `5` to compile a Standalone Executable (`AirScreen.exe`).

### Option 3: Command Line
```bash
# Run with Modern Desktop GUI (Default)
python main.py

# Run in Console / Headless Mode
python main.py --headless --port 8000 --fps 60 --quality 75

# Build Standalone Executable
python build_app.py
```

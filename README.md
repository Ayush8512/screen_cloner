# AirScreen :: Professional Low-Latency Wireless Display

AirScreen is a modular, high-performance software system designed to extend and mirror Windows displays to mobile devices, tablets, and remote browsers over local Wi-Fi without physical cables.

## Architecture

```
wireless_display/
├── airscreen/                        # Core Python Engine
│   ├── config.py                     # Central configuration & streaming profiles
│   ├── app.py                        # FastAPI application factory & routes
│   ├── core/
│   │   ├── display.py                # Windows DPI awareness & monitor enumeration
│   │   ├── capture.py                # Desktop capture worker thread (MSS / DXGI)
│   │   ├── encoder.py                # Hardware-accelerated JPEG frame compressor
│   │   └── input.py                  # Win32 SendInput controller (mouse & keyboard)
│   └── network/
│       ├── discovery.py              # Interface discovery & IP resolution
│       ├── protocol.py               # Typed protocol schemas & message parsing
│       └── session.py                # WebSocket client session manager & flow control
├── static/                           # Minimalist Client Frontend
│   ├── index.html                    # Semantic HTML5 markup
│   ├── css/
│   │   └── main.css                  # Industrial Dark Zinc/Slate stylesheet
│   └── js/
│       ├── connection.js             # WebSocket client & ping telemetry
│       ├── renderer.js               # Canvas frame renderer (ImageBitmap)
│       ├── controls.js               # Normalized touch & trackpad gesture engine
│       └── app.js                    # UI orchestrator
├── virtual_display_driver/           # VDD Driver and Control utility
├── main.py                           # CLI entry point
└── start_airscreen.bat               # Windows launcher script
```

## Key Engineering Highlights

- **Zero Buffer Lag:** Implements an acknowledgement-based backpressure streaming protocol. The server only pushes the next frame when the client is ready, preventing socket buffer queueing over Wi-Fi.
- **Extended Display Support:** Compatible with Microsoft IddCx Virtual Display Driver (VDD) to create genuine secondary screens in Windows that support drag-and-drop window workflows.
- **Hardware-Accelerated Mobile Decoding:** Uses `createImageBitmap` on the client to decode video frames directly on the mobile GPU.
- **Precision Input Handling:** Supports both direct touch mapping (1:1 screen mapping) and laptop-style trackpad mode with momentum scrolling and Unicode typing.
- **Industrial Minimalist Aesthetics:** Clean dark zinc palette (`#090d16`, `#0f172a`, `#1e293b`) with steel blue accents and lightweight SVG vector line icons. Completely free of flashy gradients or emojis.

## Usage

### 1. Launch via Script
Double-click `start_airscreen.bat` and select:
- `1` to run the Wireless Display Server.
- `2` to install/manage the Virtual Display Driver (for Extended Display 2).

### 2. Launch via CLI
```bash
python main.py --port 8000 --fps 45 --quality 65 --scale 0.75
```

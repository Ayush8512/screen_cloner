"""AirScreen Command-Line Interface and Server Entry Point."""

import argparse
import ctypes
import logging
import multiprocessing
import os
import sys
import threading
import time
import webbrowser

import uvicorn

from airscreen.config import AppConfig, get_resource_path
from airscreen.network.discovery import NetworkDiscovery
from airscreen.app import create_app
from airscreen.gui.window import HostWindow
from airscreen.gui.tray import SystemTrayManager

# Configure structured monochromatic logging with optional file fallback for frozen exe
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%H:%M:%S")
logger = logging.getLogger("airscreen")

# Safely handle frozen / windowed stdout
if sys.stdout is None:
    class DummyStream:
        def write(self, s): pass
        def flush(self): pass
    sys.stdout = DummyStream()
    sys.stderr = DummyStream()
else:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AirScreen - Ultra-Low Latency Wireless Display Server & Control Center"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding host IP")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Initial target port")
    parser.add_argument("--fps", type=int, default=45, help="Capture frame rate cap (default: 45)")
    parser.add_argument("--quality", "-q", type=int, default=65, help="JPEG quality 25-95 (default: 65)")
    parser.add_argument("--scale", "-s", type=float, default=0.75, help="Resolution scale factor (default: 0.75)")
    parser.add_argument("--headless", "--no-gui", action="store_true", help="Run without native desktop GUI")
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve static assets folder across dev and frozen PyInstaller environments
    static_dir = get_resource_path("static")

    # Discover network configuration
    wifi_ip = NetworkDiscovery.get_local_wifi_ip()
    port = NetworkDiscovery.find_open_port(preferred_port=args.port)

    config = AppConfig(
        host=args.host,
        port=port,
        fps_cap=args.fps,
        default_quality=args.quality,
        default_scale=args.scale,
    )

    # Print clean monochromatic startup banner
    NetworkDiscovery.print_startup_banner(wifi_ip, port, static_dir)

    # Initialize server application
    app = create_app(config=config, static_dir=static_dir)

    if args.headless:
        # Run server in main thread (headless / console mode)
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            ws_ping_interval=None,
            ws_ping_timeout=None,
            log_level="warning",
        )
    else:
        # Run server in background daemon thread
        server_config = uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            ws_ping_interval=None,
            ws_ping_timeout=None,
            log_level="warning",
        )
        server = uvicorn.Server(server_config)
        server_thread = threading.Thread(target=server.run, name="UvicornServerThread", daemon=True)
        server_thread.start()

        # Allow server 500ms to bind port
        time.sleep(0.5)

        # Lifecycle event to coordinate exit from tray or keyboard interrupt
        exit_event = threading.Event()

        def signal_exit():
            logger.info("[AirScreen] Exit signal received. Terminating process...")
            exit_event.set()

        # Initialize System Tray
        tray = SystemTrayManager(port=config.port, on_exit=signal_exit)
        tray.run_in_thread()

        # Launch Native Desktop Window with graceful fallback to browser
        try:
            window = HostWindow(port=config.port)
            window.start()
            logger.info("[AirScreen] Control Center window closed. Service remains active in system tray.")
        except Exception as e:
            logger.warning(f"[GUI] Native window unavailable ({e}). Opening dashboard in system browser...")
            webbrowser.open(f"http://127.0.0.1:{config.port}/dashboard")

        # Keep server and system tray alive until user explicitly exits via tray
        try:
            while not exit_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("[AirScreen] Shutting down...")
            os._exit(0)


if __name__ == "__main__":
    # Crucial on Windows for PyInstaller frozen binary execution
    multiprocessing.freeze_support()
    try:
        main()
    except Exception as exc:
        if sys.platform == "win32" and getattr(sys, "frozen", False):
            ctypes.windll.user32.MessageBoxW(
                0,
                f"AirScreen encountered an error and could not start:\n\n{exc}",
                "AirScreen Fatal Error",
                0x10,
            )
        raise

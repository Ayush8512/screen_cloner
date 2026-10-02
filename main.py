"""AirScreen Command-Line Interface and Server Entry Point."""

import argparse
import logging
import os
import sys

import uvicorn

from airscreen.config import AppConfig
from airscreen.network.discovery import NetworkDiscovery
from airscreen.app import create_app

# Configure structured monochromatic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("airscreen")

# Force UTF-8 on Windows stdout for clean terminal borders
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AirScreen - Ultra-Low Latency Wireless Display Server"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding host IP")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Initial target port")
    parser.add_argument("--fps", type=int, default=45, help="Capture frame rate cap (default: 45)")
    parser.add_argument("--quality", "-q", type=int, default=65, help="JPEG quality 25-95 (default: 65)")
    parser.add_argument("--scale", "-s", type=float, default=0.75, help="Resolution scale factor (default: 0.75)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve static assets folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")

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

    # Initialize and start server
    app = create_app(config=config, static_dir=static_dir)
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        ws_ping_interval=None,
        ws_ping_timeout=None,
        log_level="warning",
    )


if __name__ == "__main__":
    main()

"""Network discovery, local IP resolution, and terminal banner generation."""

import os
import socket
import sys
from typing import Optional

import psutil
import qrcode


class NetworkDiscovery:
    """Detects active network interfaces, IP addresses, and available ports."""

    @staticmethod
    def get_all_network_interfaces() -> list:
        """Returns list of all active IPv4 network interfaces."""
        results = []
        try:
            interfaces = psutil.net_if_addrs()
            for iface_name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        if addr.address.startswith("169.254."):
                            continue
                        name_lower = iface_name.lower()
                        label = iface_name
                        if any(w in name_lower for w in ["wi-fi", "wlan", "wireless"]):
                            label = f"Wi-Fi ({iface_name})"
                        elif any(e in name_lower for e in ["ethernet", "lan", "eth"]):
                            label = f"Ethernet ({iface_name})"
                        elif "hotspot" in name_lower:
                            label = f"Mobile Hotspot ({iface_name})"
                        
                        results.append({
                            "name": iface_name,
                            "label": label,
                            "ip": addr.address,
                            "is_wifi": any(w in name_lower for w in ["wi-fi", "wlan", "wireless"]),
                        })
        except Exception:
            pass

        # Sort so Wi-Fi comes first
        results.sort(key=lambda x: not x["is_wifi"])
        return results

    @staticmethod
    def get_local_wifi_ip() -> str:
        all_ifaces = NetworkDiscovery.get_all_network_interfaces()
        if all_ifaces:
            return all_ifaces[0]["ip"]
        return "127.0.0.1"


    @staticmethod
    def find_open_port(preferred_port: int = 8000, max_attempts: int = 25) -> int:
        for offset in range(max_attempts):
            test_port = preferred_port + offset
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("0.0.0.0", test_port))
                    return test_port
            except OSError:
                continue
        return preferred_port

    @staticmethod
    def print_startup_banner(ip: str, port: int, static_dir: str):
        url = f"http://{ip}:{port}"
        
        # Save a clean QR code PNG for the static web client
        try:
            qr = qrcode.make(url)
            qr_file = os.path.join(static_dir, "qr.png")
            qr.save(qr_file)
        except Exception:
            pass

        separator = "=" * 64
        print("\n" + separator)
        print("  AIRSCREEN :: WIRELESS SECOND DISPLAY SERVER")
        print("  Version: 2.0.0  |  Architecture: Modular Win32 / DXGI")
        print(separator)
        print(f"\n[NETWORK] Server listening on interface: {ip}:{port}")
        print(f"[CLIENT]  Open mobile browser and connect to:")
        print(f"          -> {url}\n")
        print("[-] Quick Scan QR Code:")
        print("-" * 64)
        try:
            qr_terminal = qrcode.QRCode(border=1)
            qr_terminal.add_data(url)
            qr_terminal.print_ascii(invert=True)
        except Exception:
            pass
        print("-" * 64)
        print("[STATUS] Press Ctrl+C in this console to terminate.")
        print(separator + "\n")

"""Windows System Tray Daemon using Pystray."""

import logging
import subprocess
import threading
import webbrowser
from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger("airscreen.tray")


def create_tray_icon() -> Image.Image:
    """Renders a sharp, clean 64x64 AirScreen icon for the system notification area."""
    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)

    # Blue badge background
    dc.ellipse([2, 2, 62, 62], fill=(2, 132, 199, 255), outline=(56, 189, 248, 255), width=2)
    # White monitor wireframe
    dc.rectangle([16, 16, 48, 38], outline=(255, 255, 255, 255), width=3)
    dc.line([32, 38, 32, 48], fill=(255, 255, 255, 255), width=3)
    dc.line([22, 48, 42, 48], fill=(255, 255, 255, 255), width=3)
    return image


class SystemTrayManager:
    """Manages the Windows notification area tray icon and menu."""

    def __init__(self, port: int, on_exit=None):
        self.port = port
        self.on_exit = on_exit
        self.icon = None

    def _open_dashboard(self, icon, item):
        webbrowser.open(f"http://127.0.0.1:{self.port}/dashboard")

    def _copy_link(self, icon, item):
        from airscreen.network.discovery import NetworkDiscovery
        ip = NetworkDiscovery.get_local_wifi_ip()
        url = f"http://{ip}:{self.port}"
        try:
            subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{url}'"], check=False)
        except Exception:
            pass

    def _toggle_display_mode(self, icon, item):
        subprocess.run(["powershell", "-Command", "Start-Process 'ms-settings:display'"], check=False)

    def _quit(self, icon, item):
        icon.stop()
        if self.on_exit:
            self.on_exit()

    def run_in_thread(self):
        """Starts the system tray loop in a background thread."""
        def _run():
            image = create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("🖥️ Open Control Center", self._open_dashboard, default=True),
                pystray.MenuItem("📋 Copy Client Link", self._copy_link),
                pystray.MenuItem("🪟 Windows Display Settings", self._toggle_display_mode),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Exit AirScreen", self._quit),
            )
            self.icon = pystray.Icon("AirScreen", image, "AirScreen Wireless Display", menu)
            logger.info("[Tray] System tray icon registered")
            self.icon.run()

        t = threading.Thread(target=_run, name="SystemTrayThread", daemon=True)
        t.start()

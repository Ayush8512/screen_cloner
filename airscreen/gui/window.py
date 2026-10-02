"""Native Desktop Window Manager using PyWebView."""

import logging
import threading
import webview

logger = logging.getLogger("airscreen.window")


class HostWindow:
    """Manages the native Windows desktop control window for the host."""

    def __init__(self, port: int, title: str = "AirScreen - Host Control Center"):
        self.port = port
        self.title = title
        self.window = None

    def start(self):
        url = f"http://127.0.0.1:{self.port}/dashboard"
        logger.info(f"[GUI] Launching native window for {url}")
        
        # Configure modern window
        self.window = webview.create_window(
            title=self.title,
            url=url,
            width=1120,
            height=750,
            min_size=(850, 580),
            resizable=True,
            background_color="#090d16",
        )
        webview.start(debug=False)

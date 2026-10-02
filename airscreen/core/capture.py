"""High-performance GPU DXGI screen capture engine with GDI MSS fallback."""

import ctypes
import logging
import threading
import time
from typing import Optional

import cv2
import mss
import numpy as np

from airscreen.core.display import DisplayManager, DisplayMonitor
from airscreen.core.encoder import FrameEncoder

logger = logging.getLogger("airscreen.capture")
user32 = ctypes.windll.user32


class ScreenCaptureEngine:
    """Captures desktop video frames using DirectX GPU Duplication (DXGI) with seamless MSS fallback."""

    def __init__(
        self,
        display_manager: DisplayManager,
        encoder: FrameEncoder,
        target_fps: int = 45,
        default_monitor_id: Optional[int] = None,
    ):
        self.display_manager = display_manager
        self.encoder = encoder
        self.target_fps = target_fps
        self.selected_monitor_id = (
            default_monitor_id
            if default_monitor_id is not None
            else self.display_manager.get_default_monitor_id()
        )

        self._running = False
        self._lock = threading.Lock()
        self._latest_frame_bytes: Optional[bytes] = None
        self._frame_id: int = 0
        self._worker_thread: Optional[threading.Thread] = None
        self._monitor_changed = False

    @property
    def frame_id(self) -> int:
        return self._frame_id

    @property
    def latest_frame(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_frame_bytes

    def set_monitor(self, monitor_id: int) -> bool:
        monitors = self.display_manager.get_monitors(force_refresh=True)
        if any(m.id == monitor_id for m in monitors):
            with self._lock:
                self.selected_monitor_id = monitor_id
                self._monitor_changed = True
            logger.info(f"[Capture] Target monitor switched to ID {monitor_id}")
            return True
        return False

    def get_active_monitor(self) -> DisplayMonitor:
        mon = self.display_manager.get_monitor_by_id(self.selected_monitor_id)
        if not mon:
            mon = self.display_manager.get_monitors()[0]
        return mon

    def start(self):
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._capture_worker, name="ScreenCaptureWorker", daemon=True
        )
        self._worker_thread.start()
        logger.info(
            f"[Capture] Engine started targeting Display {self.selected_monitor_id} at {self.target_fps} FPS"
        )

    def stop(self):
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        logger.info("[Capture] Engine stopped")

    def _capture_worker(self):
        # Attach thread to interactive desktop session
        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)

        # Initialize DXCam (DirectX Desktop Duplication)
        dx_camera = None
        current_dx_output = -1

        def init_dxcam(output_idx: int):
            nonlocal dx_camera, current_dx_output
            if dx_camera is not None:
                try:
                    dx_camera.stop()
                    dx_camera.release()
                except Exception:
                    pass
                dx_camera = None

            try:
                import dxcam
                # output_idx in dxcam is 0-based index of monitor outputs
                dx_camera = dxcam.create(output_idx=output_idx, output_color="BGR")
                dx_camera.start(target_fps=self.target_fps, video_mode=True)
                current_dx_output = output_idx
                logger.info(f"[Capture] DirectX GPU Duplication active on Output {output_idx}")
            except Exception as e:
                dx_camera = None
                current_dx_output = -1
                logger.warning(f"[Capture] DirectX Duplication unavailable ({e}), using MSS GDI fallback")

        # Initial DXCam setup
        init_dxcam(max(0, self.selected_monitor_id - 1))

        # Backup MSS instance
        sct = mss.MSS()
        frame_interval = 1.0 / max(10, min(120, self.target_fps))

        while self._running:
            loop_start = time.perf_counter()

            # Handle monitor change
            if self._monitor_changed:
                self._monitor_changed = False
                target_output = max(0, self.selected_monitor_id - 1)
                init_dxcam(target_output)

            bgr_frame = None

            # 1. Primary: DirectX Desktop Duplication (captures hardware video & overlays)
            if dx_camera is not None:
                try:
                    bgr_frame = dx_camera.get_latest_frame()
                except Exception:
                    bgr_frame = None

            # 2. Fallback: MSS GDI
            if bgr_frame is None and dx_camera is None:
                try:
                    active_mon = self.get_active_monitor()
                    target_idx = active_mon.id
                    if target_idx >= len(sct.monitors):
                        target_idx = 1

                    sct_mon = sct.monitors[target_idx]
                    sct_img = sct.grab(sct_mon)
                    raw_bytes = np.frombuffer(
                        sct_img.raw, dtype=np.uint8
                    ).reshape((sct_img.height, sct_img.width, 4))
                    bgr_frame = cv2.cvtColor(raw_bytes, cv2.COLOR_BGRA2BGR)
                except Exception as exc:
                    time.sleep(0.02)
                    continue

            # Encode and publish frame
            if bgr_frame is not None:
                encoded_bytes = self.encoder.encode(bgr_frame)
                if encoded_bytes:
                    with self._lock:
                        self._latest_frame_bytes = encoded_bytes
                        self._frame_id += 1

            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)

        # Cleanup on exit
        if dx_camera is not None:
            try:
                dx_camera.stop()
                dx_camera.release()
            except Exception:
                pass

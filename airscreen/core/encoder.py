"""High-speed image encoding and resolution scaling pipeline."""

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("airscreen.encoder")


class FrameEncoder:
    """Optimized JPEG encoder for real-time low-latency video streaming."""

    def __init__(self, default_quality: int = 65, default_scale: float = 0.75):
        self.quality = max(25, min(95, default_quality))
        self.scale = max(0.35, min(1.0, default_scale))
        self._encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]

    def set_parameters(self, quality: int, scale: float):
        self.quality = max(25, min(95, quality))
        self.scale = max(0.35, min(1.0, scale))
        self._encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]

    def encode(self, frame: np.ndarray) -> Optional[bytes]:
        """Scales and encodes an OpenCV BGR frame into JPEG binary bytes."""
        try:
            h, w = frame.shape[:2]
            if self.scale < 0.98:
                target_w = int(w * self.scale)
                target_h = int(h * self.scale)
                # cv2.INTER_LINEAR provides the ideal balance of speed and clarity
                frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

            success, buffer = cv2.imencode(".jpg", frame, self._encode_params)
            if success:
                return buffer.tobytes()
        except Exception as exc:
            logger.error(f"[Encoder] Encoding failure: {exc}")
        return None

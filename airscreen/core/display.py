"""Windows display enumeration, DPI awareness, and coordinate transformation."""

import ctypes
from dataclasses import asdict, dataclass
import logging
from typing import Dict, List, Optional, Tuple

import mss

logger = logging.getLogger("airscreen.display")

# Initialize Windows DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


@dataclass(frozen=True)
class DisplayMonitor:
    id: int
    name: str
    left: int
    top: int
    width: int
    height: int
    is_primary: bool
    is_extended: bool

    def to_dict(self) -> Dict:
        return asdict(self)


class DisplayManager:
    """Manages active Windows monitors, coordinates, and hotplug changes."""

    def __init__(self):
        self._cached_monitors: List[DisplayMonitor] = []
        self.refresh()

    def refresh(self) -> List[DisplayMonitor]:
        monitors: List[DisplayMonitor] = []
        try:
            with mss.MSS() as sct:
                # sct.monitors[0] is the bounding box of all displays combined
                for i, m in enumerate(sct.monitors):
                    if i == 0:
                        continue
                    is_primary = (m["left"] == 0 and m["top"] == 0)
                    is_extended = not is_primary or i > 1
                    label = f"Display {i}" + (" (Extended)" if i > 1 else " (Main)")
                    monitors.append(
                        DisplayMonitor(
                            id=i,
                            name=label,
                            left=m["left"],
                            top=m["top"],
                            width=m["width"],
                            height=m["height"],
                            is_primary=is_primary,
                            is_extended=is_extended,
                        )
                    )
        except Exception as exc:
            logger.error(f"[Display] Enumeration error: {exc}")

        if not monitors:
            monitors.append(
                DisplayMonitor(
                    id=1,
                    name="Display 1 (Default)",
                    left=0,
                    top=0,
                    width=1920,
                    height=1080,
                    is_primary=True,
                    is_extended=False,
                )
            )

        self._cached_monitors = monitors
        return self._cached_monitors

    def get_monitors(self, force_refresh: bool = False) -> List[DisplayMonitor]:
        if force_refresh or not self._cached_monitors:
            return self.refresh()
        return self._cached_monitors

    def get_monitor_by_id(self, monitor_id: int) -> Optional[DisplayMonitor]:
        for mon in self._cached_monitors:
            if mon.id == monitor_id:
                return mon
        return self._cached_monitors[0] if self._cached_monitors else None

    def get_default_monitor_id(self, prefer_extended: bool = True) -> int:
        mons = self.get_monitors()
        if prefer_extended and len(mons) > 1:
            for m in mons:
                if m.is_extended and m.id > 1:
                    return m.id
        return mons[0].id if mons else 1

    def to_screen_coords(self, x_pct: float, y_pct: float, monitor_id: int) -> Tuple[int, int]:
        """Translates normalized 0.0-1.0 client touch coordinates to absolute Windows virtual desktop coordinates."""
        mon = self.get_monitor_by_id(monitor_id)
        if not mon:
            return 0, 0
        clamped_x = max(0.0, min(1.0, x_pct))
        clamped_y = max(0.0, min(1.0, y_pct))
        target_x = mon.left + int(clamped_x * (mon.width - 1))
        target_y = mon.top + int(clamped_y * (mon.height - 1))
        return target_x, target_y

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Tuple


def get_base_dir() -> str:
    """Returns the base project root or PyInstaller extract/bundle directory."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(*subpaths: str) -> str:
    """Resolve absolute path to a bundled resource file or directory across dev and PyInstaller environments."""
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            p = os.path.join(bundle_dir, *subpaths)
            if os.path.exists(p):
                return p
        exe_dir = os.path.dirname(sys.executable)
        p = os.path.join(exe_dir, *subpaths)
        if os.path.exists(p):
            return p
        return os.path.join(bundle_dir or exe_dir, *subpaths)
    else:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root_dir, *subpaths)


@dataclass(frozen=True)
class StreamPreset:
    name: str
    scale: float
    quality: int
    target_fps: int


QUALITY_PRESETS: Dict[str, StreamPreset] = {
    "performance": StreamPreset(name="540p Performance", scale=0.5, quality=50, target_fps=60),
    "balanced": StreamPreset(name="720p Balanced", scale=0.75, quality=65, target_fps=45),
    "quality": StreamPreset(name="1080p Quality", scale=1.0, quality=80, target_fps=30),
}


@dataclass
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    fps_cap: int = 45
    default_quality: int = 65
    default_scale: float = 0.75
    auto_select_extended: bool = True
    monitor_poll_interval: float = 2.0
    ping_interval_ms: int = 1500
    jpeg_subsampling: int = 0  # 4:4:4 or 4:2:0 via cv2

    @property
    def dimensions_scale_range(self) -> Tuple[float, float]:
        return (0.35, 1.0)

    @property
    def quality_range(self) -> Tuple[int, int]:
        return (25, 95)

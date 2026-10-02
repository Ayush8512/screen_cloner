"""Automated PyInstaller build script for packaging AirScreen into a standalone Windows executable."""

import os
import shutil
import subprocess
import sys


def build():
    print("=" * 64)
    print("  AIRSCREEN :: STANDALONE EXECUTABLE BUILD PIPELINE")
    print("=" * 64)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")

    # Command line arguments for PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "AirScreen",
        "--add-data", f"{os.path.join(base_dir, 'static')};static",
        "--add-data", f"{os.path.join(base_dir, 'virtual_display_driver')};virtual_display_driver",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespans",
        "--hidden-import", "uvicorn.lifespans.on",
        "--hidden-import", "pystray",
        "--hidden-import", "webview",
        "--hidden-import", "dxcam",
        os.path.join(base_dir, "main.py"),
    ]

    print("\n[BUILD] Running PyInstaller compilation...")
    result = subprocess.run(cmd, cwd=base_dir)

    if result.returncode == 0:
        print("\n" + "=" * 64)
        print("  BUILD SUCCESSFUL!")
        print(f"  Standalone application located at: {os.path.join(dist_dir, 'AirScreen')}")
        print("=" * 64 + "\n")
    else:
        print("\n[ERROR] PyInstaller build failed with exit code:", result.returncode)


if __name__ == "__main__":
    build()

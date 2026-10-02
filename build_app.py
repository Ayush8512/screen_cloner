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
        "--add-data", f"{os.path.join(base_dir, 'virtual_display_driver', 'Dependencies')};virtual_display_driver/Dependencies",
        "--add-data", f"{os.path.join(base_dir, 'virtual_display_driver', 'SignedDrivers')};virtual_display_driver/SignedDrivers",
        "--add-data", f"{os.path.join(base_dir, 'install_driver_admin.bat')};.",
        "--add-data", f"{os.path.join(base_dir, 'uninstall_driver_admin.bat')};.",
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
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "clr",
        "--hidden-import", "pythonnet",
        "--hidden-import", "clr_loader",
        "--hidden-import", "dxcam",
        "--hidden-import", "qrcode",
        "--hidden-import", "PIL",
        "--hidden-import", "psutil",
        os.path.join(base_dir, "main.py"),
    ]

    print("\n[BUILD] Running PyInstaller compilation...")
    result = subprocess.run(cmd, cwd=base_dir)

    if result.returncode == 0:
        target_app_dir = os.path.join(dist_dir, "AirScreen")
        for helper_file in ["install_driver_admin.bat", "uninstall_driver_admin.bat", "start_airscreen.bat"]:
            src = os.path.join(base_dir, helper_file)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(target_app_dir, helper_file))

        print("\n" + "=" * 64)
        print("  BUILD SUCCESSFUL!")
        print(f"  Standalone application located at: {target_app_dir}")
        print("=" * 64 + "\n")
    else:
        print("\n[ERROR] PyInstaller build failed with exit code:", result.returncode)


if __name__ == "__main__":
    build()

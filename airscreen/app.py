"""FastAPI application factory, lifespan management, and static file routing."""

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from airscreen.config import AppConfig
from airscreen.core.capture import ScreenCaptureEngine
from airscreen.core.display import DisplayManager
from airscreen.core.encoder import FrameEncoder
from airscreen.network.session import ClientSessionManager

logger = logging.getLogger("airscreen.app")


def create_app(config: AppConfig, static_dir: str) -> FastAPI:
    """Builds and wires the AirScreen FastAPI application instance."""

    display_manager = DisplayManager()
    encoder = FrameEncoder(
        default_quality=config.default_quality,
        default_scale=config.default_scale,
    )
    capture_engine = ScreenCaptureEngine(
        display_manager=display_manager,
        encoder=encoder,
        target_fps=config.fps_cap,
    )
    session_manager = ClientSessionManager(
        capture_engine=capture_engine,
        display_manager=display_manager,
        encoder=encoder,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("[App] Initializing capture engine...")
        capture_engine.start()
        yield
        logger.info("[App] Shutting down capture engine...")
        capture_engine.stop()

    app = FastAPI(title="AirScreen Wireless Display", lifespan=lifespan)

    # Static assets mounting
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        return FileResponse(index_path)

    @app.get("/dashboard")
    async def serve_dashboard():
        dash_path = os.path.join(static_dir, "dashboard.html")
        if os.path.exists(dash_path):
            return FileResponse(dash_path)
        return JSONResponse({"status": "Dashboard loading..."})

    @app.get("/api/system/stats")
    async def get_system_stats():
        from airscreen.network.discovery import NetworkDiscovery
        import subprocess

        # Check driver running status
        driver_active = False
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            devcon_path = os.path.join(base_dir, "virtual_display_driver", "Dependencies", "devcon.exe")
            if os.path.exists(devcon_path):
                res = subprocess.run([devcon_path, "status", "Root\\MttVDD"], capture_output=True, text=True, timeout=2)
                driver_active = "Driver is running" in res.stdout
        except Exception:
            driver_active = False

        monitors = [m.to_dict() for m in display_manager.get_monitors(force_refresh=True)]
        active = capture_engine.get_active_monitor().to_dict()
        clients = session_manager.get_connected_clients()
        interfaces = NetworkDiscovery.get_all_network_interfaces()

        return JSONResponse({
            "status": "online",
            "port": config.port,
            "fps_cap": config.fps_cap,
            "quality": encoder.quality,
            "scale": encoder.scale,
            "monitors": monitors,
            "active_monitor": active,
            "driver_active": driver_active,
            "clients": clients,
            "client_count": len(clients),
            "interfaces": interfaces,
        })

    @app.get("/api/system/thumbnail/{monitor_id}")
    async def get_monitor_thumbnail(monitor_id: int):
        from fastapi import Response
        thumb_bytes = capture_engine.generate_thumbnail(monitor_id=monitor_id, max_width=320)
        if thumb_bytes:
            return Response(content=thumb_bytes, media_type="image/jpeg")
        return Response(status_code=404)

    @app.post("/api/monitors/select/{monitor_id}")
    async def api_select_monitor(monitor_id: int):
        success = capture_engine.set_monitor(monitor_id)
        return JSONResponse({"success": success, "selected": monitor_id})

    @app.post("/api/clients/disconnect/{client_id}")
    async def api_disconnect_client(client_id: str):
        success = await session_manager.disconnect_client(client_id)
        return JSONResponse({"success": success})

    @app.post("/api/driver/action")
    async def api_driver_action(payload: dict):
        action = payload.get("action")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if action == "install":
            bat_path = os.path.join(base_dir, "install_driver_admin.bat")
            os.system(f'start "" powershell -Command "Start-Process \'{bat_path}\' -Verb RunAs"')
            return JSONResponse({"success": True, "message": "Triggered driver installation"})
        elif action == "remove":
            bat_path = os.path.join(base_dir, "uninstall_driver_admin.bat")
            os.system(f'start "" powershell -Command "Start-Process \'{bat_path}\' -Verb RunAs"')
            return JSONResponse({"success": True, "message": "Triggered driver removal"})
        elif action == "settings":
            os.system('start ms-settings:display')
            return JSONResponse({"success": True, "message": "Opened Windows Display Settings"})

        return JSONResponse({"success": False, "message": "Unknown action"}, status_code=400)

    @app.get("/api/monitors")
    async def list_monitors():
        monitors = [m.to_dict() for m in display_manager.get_monitors(force_refresh=True)]
        active = capture_engine.get_active_monitor().to_dict()
        return JSONResponse({"monitors": monitors, "active": active})

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket):
        await session_manager.handle_client(websocket)

    return app


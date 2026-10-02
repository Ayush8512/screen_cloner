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

    @app.get("/api/monitors")
    async def list_monitors():
        monitors = [m.to_dict() for m in display_manager.get_monitors(force_refresh=True)]
        active = capture_engine.get_active_monitor().to_dict()
        return JSONResponse({"monitors": monitors, "active": active})

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket):
        await session_manager.handle_client(websocket)

    return app

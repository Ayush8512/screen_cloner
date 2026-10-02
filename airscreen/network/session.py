"""Thread-safe WebSocket client session management, frame streaming, and event dispatching."""

import asyncio
import json
import logging
import traceback
from typing import Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

from airscreen.core.capture import ScreenCaptureEngine
from airscreen.core.display import DisplayManager
from airscreen.core.encoder import FrameEncoder
from airscreen.core.input import InputInjector
from airscreen.network.protocol import MessageType, parse_client_message

logger = logging.getLogger("airscreen.session")


class ClientSessionManager:
    """Manages connected clients, handles input events, and coordinates low-latency frame streaming."""

    def __init__(
        self,
        capture_engine: ScreenCaptureEngine,
        display_manager: DisplayManager,
        encoder: FrameEncoder,
    ):
        self.capture_engine = capture_engine
        self.display_manager = display_manager
        self.encoder = encoder
        self._active_connections: Set[WebSocket] = set()

    async def handle_client(self, websocket: WebSocket):
        await websocket.accept()
        self._active_connections.add(websocket)

        # Mutex lock to serialize writes to this WebSocket (prevents concurrency crashes)
        ws_lock = asyncio.Lock()

        async def safe_send_text(text: str) -> bool:
            try:
                async with ws_lock:
                    await websocket.send_text(text)
                return True
            except Exception:
                return False

        async def safe_send_bytes(data: bytes) -> bool:
            try:
                async with ws_lock:
                    await websocket.send_bytes(data)
                return True
            except Exception:
                return False

        active_mon = self.capture_engine.get_active_monitor()
        all_monitors = [m.to_dict() for m in self.display_manager.get_monitors()]

        # Send initial handshake packet
        await safe_send_text(
            json.dumps({
                "type": MessageType.INIT.value,
                "monitors": all_monitors,
                "selectedMonitor": active_mon.id,
                "screenWidth": active_mon.width,
                "screenHeight": active_mon.height,
                "quality": self.encoder.quality,
            })
        )

        client_ready = asyncio.Event()
        client_ready.set()
        last_sent_frame_id = -1
        is_streaming = True

        async def stream_worker():
            nonlocal last_sent_frame_id, is_streaming
            while is_streaming:
                try:
                    # Wait for client acknowledgment or 35ms timeout to prevent stream freezing
                    try:
                        await asyncio.wait_for(client_ready.wait(), timeout=0.035)
                    except asyncio.TimeoutError:
                        pass
                    client_ready.clear()

                    current_frame_id = self.capture_engine.frame_id
                    if current_frame_id == last_sent_frame_id:
                        await asyncio.sleep(0.005)
                        client_ready.set()
                        continue

                    frame_bytes = self.capture_engine.latest_frame
                    if frame_bytes:
                        last_sent_frame_id = current_frame_id
                        success = await safe_send_bytes(frame_bytes)
                        if not success:
                            break
                    else:
                        await asyncio.sleep(0.005)
                        client_ready.set()

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug(f"[Stream] Worker terminated: {exc}")
                    break

        sender_task = asyncio.create_task(stream_worker())

        try:
            while True:
                raw_text = await websocket.receive_text()
                msg = parse_client_message(raw_text)
                if not msg:
                    continue

                msg_type = msg.get("type")

                if msg_type == MessageType.ACK.value:
                    client_ready.set()

                elif msg_type == MessageType.PING.value:
                    await safe_send_text(
                        json.dumps({"type": MessageType.PONG.value, "t": msg.get("t")})
                    )

                elif msg_type == MessageType.SELECT_MONITOR.value:
                    requested_id = int(msg.get("idx", 1))
                    if self.capture_engine.set_monitor(requested_id):
                        updated_mon = self.capture_engine.get_active_monitor()
                        await safe_send_text(
                            json.dumps({
                                "type": MessageType.MONITOR_CHANGED.value,
                                "selectedMonitor": updated_mon.id,
                                "screenWidth": updated_mon.width,
                                "screenHeight": updated_mon.height,
                            })
                        )

                elif msg_type == MessageType.MOUSE_MOVE.value:
                    x, y = self.display_manager.to_screen_coords(
                        float(msg["x"]), float(msg["y"]), self.capture_engine.selected_monitor_id
                    )
                    InputInjector.set_cursor_pos(x, y)

                elif msg_type == MessageType.MOUSE_DOWN.value:
                    x, y = self.display_manager.to_screen_coords(
                        float(msg["x"]), float(msg["y"]), self.capture_engine.selected_monitor_id
                    )
                    InputInjector.set_cursor_pos(x, y)
                    InputInjector.mouse_down(msg.get("button", "left"))

                elif msg_type == MessageType.MOUSE_UP.value:
                    x, y = self.display_manager.to_screen_coords(
                        float(msg["x"]), float(msg["y"]), self.capture_engine.selected_monitor_id
                    )
                    InputInjector.set_cursor_pos(x, y)
                    InputInjector.mouse_up(msg.get("button", "left"))

                elif msg_type == MessageType.CLICK.value:
                    x, y = self.display_manager.to_screen_coords(
                        float(msg["x"]), float(msg["y"]), self.capture_engine.selected_monitor_id
                    )
                    InputInjector.set_cursor_pos(x, y)
                    InputInjector.mouse_click(msg.get("button", "left"))

                elif msg_type == MessageType.WHEEL.value:
                    InputInjector.mouse_wheel(float(msg.get("deltaY", 0)))

                elif msg_type == MessageType.TYPE_TEXT.value:
                    InputInjector.type_unicode_text(msg.get("text", ""))

                elif msg_type == MessageType.KEY.value:
                    InputInjector.send_key(msg.get("key", ""))

                elif msg_type == MessageType.SETTINGS.value:
                    quality = int(msg.get("quality", self.encoder.quality))
                    scale = float(msg.get("scale", self.encoder.scale))
                    self.encoder.set_parameters(quality, scale)

        except (WebSocketDisconnect, ConnectionResetError):
            pass
        except Exception as exc:
            # Check for disconnect / closed socket errors
            err_name = type(exc).__name__
            if "ConnectionClosed" in err_name or "Disconnect" in err_name:
                pass
            else:
                logger.error(f"[Session] WebSocket handler error ({err_name}): {exc}")
        finally:
            is_streaming = False
            sender_task.cancel()
            self._active_connections.discard(websocket)
            logger.info("[Session] Client connection closed")

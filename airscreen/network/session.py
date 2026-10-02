"""Thread-safe WebSocket client session management, frame streaming, and event dispatching."""

import asyncio
import json
import logging
import traceback
from typing import Dict, List, Set, Optional
import time
import uuid

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
        self._sessions: Dict[WebSocket, dict] = {}
        self._lock = asyncio.Lock()

    def get_connected_clients(self) -> List[dict]:
        """Returns snapshot list of connected clients and their telemetry."""
        now = time.time()
        clients = []
        for ws, info in list(self._sessions.items()):
            clients.append({
                "id": info.get("id"),
                "ip": info.get("ip"),
                "device": info.get("device"),
                "connected_seconds": int(now - info.get("connected_at", now)),
                "ping_ms": info.get("ping_ms", "--"),
                "frames_sent": info.get("frames_sent", 0),
                "frames_dropped": info.get("frames_dropped", 0),
                "last_frame_kb": info.get("last_frame_kb", 0),
            })

        return clients

    async def disconnect_client(self, client_id: str) -> bool:
        """Forcefully closes connection with a specific client ID."""
        for ws, info in list(self._sessions.items()):
            if info.get("id") == client_id:
                try:
                    await ws.close()
                except Exception:
                    pass
                return True
        return False

    async def handle_client(self, websocket: WebSocket):
        await websocket.accept()
        self._active_connections.add(websocket)

        # Detect device type from User-Agent
        ua = websocket.headers.get("user-agent", "")
        device = "Web Browser"
        if "iPad" in ua:
            device = "iPad (Tablet)"
        elif "iPhone" in ua:
            device = "iPhone"
        elif "Android" in ua:
            device = "Android Tablet" if "Tablet" in ua else "Android Phone"
        elif "Windows" in ua:
            device = "Windows Device"
        elif "Macintosh" in ua:
            device = "Mac"
        elif "Linux" in ua:
            device = "Linux Device"

        client_id = f"dev_{uuid.uuid4().hex[:6]}"
        client_ip = websocket.client.host if websocket.client else "Unknown IP"

        self._sessions[websocket] = {
            "id": client_id,
            "ip": client_ip,
            "device": device,
            "connected_at": time.time(),
            "ping_ms": "--",
        }

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
        total_frames_sent = 0
        total_frames_dropped = 0

        async def stream_worker():
            nonlocal last_sent_frame_id, is_streaming, total_frames_sent, total_frames_dropped
            while is_streaming:
                try:
                    # Wait for client acknowledgment with 200ms timeout for lost packets
                    try:
                        await asyncio.wait_for(client_ready.wait(), timeout=0.200)
                    except asyncio.TimeoutError:
                        # Client ACK lost or delayed; reset ready gate to prevent deadlock
                        client_ready.set()
                        await asyncio.sleep(0.01)
                        continue

                    client_ready.clear()

                    current_frame_id = self.capture_engine.frame_id
                    if current_frame_id == last_sent_frame_id:
                        # No new screen change; pause briefly
                        await asyncio.sleep(0.004)
                        client_ready.set()
                        continue

                    # Calculate dropped frames if capture advanced faster than client consumption
                    if last_sent_frame_id != -1 and current_frame_id > last_sent_frame_id + 1:
                        dropped = current_frame_id - last_sent_frame_id - 1
                        total_frames_dropped += dropped
                        if websocket in self._sessions:
                            self._sessions[websocket]["frames_dropped"] = total_frames_dropped

                    frame_bytes = self.capture_engine.latest_frame
                    if frame_bytes:
                        last_sent_frame_id = current_frame_id
                        total_frames_sent += 1
                        if websocket in self._sessions:
                            self._sessions[websocket]["frames_sent"] = total_frames_sent
                            self._sessions[websocket]["last_frame_kb"] = round(len(frame_bytes) / 1024, 1)

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
                    req_t = msg.get("t")
                    if req_t and websocket in self._sessions:
                        calc_ping = int(time.time() * 1000) - int(req_t)
                        if 0 <= calc_ping < 5000:
                            self._sessions[websocket]["ping_ms"] = calc_ping
                    await safe_send_text(
                        json.dumps({"type": MessageType.PONG.value, "t": req_t})
                    )

                elif msg_type == MessageType.HOTKEY.value:
                    combo = msg.get("combo", [])
                    if isinstance(combo, list):
                        InputInjector.send_hotkey(combo)

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
            self._sessions.pop(websocket, None)
            logger.info(f"[Session] Client {client_id} disconnected")


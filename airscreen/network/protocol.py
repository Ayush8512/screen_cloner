"""Network message protocol definitions and packet validation."""

from enum import Enum
from typing import Any, Dict, Optional


class MessageType(str, Enum):
    # Server -> Client
    INIT = "init"
    PONG = "pong"
    MONITOR_CHANGED = "monitor_changed"
    ERROR = "error"

    # Client -> Server
    ACK = "ack"
    PING = "ping"
    SELECT_MONITOR = "select_monitor"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    CLICK = "click"
    WHEEL = "wheel"
    TYPE_TEXT = "type_text"
    KEY = "key"
    HOTKEY = "hotkey"
    SETTINGS = "settings"


def parse_client_message(raw_json: str) -> Optional[Dict[str, Any]]:
    import json
    try:
        data = json.loads(raw_json)
        if isinstance(data, dict) and "type" in data:
            return data
    except Exception:
        pass
    return None

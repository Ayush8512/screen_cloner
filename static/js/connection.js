/**
 * AirScreen WebSocket Connection & Telemetry Manager
 */

class ConnectionManager {
  constructor(options = {}) {
    this.onFrame = options.onFrame || (() => {});
    this.onInit = options.onInit || (() => {});
    this.onStatusChange = options.onStatusChange || (() => {});
    this.onPingUpdate = options.onPingUpdate || (() => {});

    this.ws = null;
    this.pingTimer = null;
    this.isConnected = false;
    this.ping = 0;
  }

  connect() {
    const loc = window.location;
    const protocol = loc.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${loc.host}/ws`;

    this.ws = new WebSocket(url);
    this.ws.binaryType = "arraybuffer";

    this.ws.onopen = () => {
      this.isConnected = true;
      this.onStatusChange(true);
      this._startPing();
    };

    this.ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        this._handleJsonMessage(event.data);
      } else {
        // Binary JPEG frame
        this.onFrame(event.data);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.onStatusChange(false);
      this._stopPing();
      setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = (err) => {
      console.error("[WS] Connection error:", err);
    };
  }

  sendAck() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "ack" }));
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  _startPing() {
    this._stopPing();
    this.pingTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: "ping", t: performance.now() });
      }
    }, 1500);
  }

  _stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  _handleJsonMessage(rawJson) {
    try {
      const msg = JSON.parse(rawJson);
      if (msg.type === "init" || msg.type === "monitor_changed") {
        this.onInit(msg);
      } else if (msg.type === "pong") {
        this.ping = Math.round(performance.now() - msg.t);
        this.onPingUpdate(this.ping);
      }
    } catch (e) {
      console.error("[WS] Failed to parse message:", e);
    }
  }
}

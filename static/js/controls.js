/**
 * AirScreen Remote Touch, Mouse & Keyboard Input Controller
 */

class InputManager {
  constructor(canvasElement, onSendEvent) {
    this.canvas = canvasElement;
    this.send = onSendEvent;

    this.mode = "touch"; // "touch" or "trackpad"
    this.touchStartTime = 0;
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.lastTrackpadX = 0;
    this.lastTrackpadY = 0;
    this.isDragging = false;
    this.twoFingerStartY = 0;

    this.fitMode = "contain"; // "contain" or "fill"
    this._bindTouchEvents();
    this._bindMouseEvents();
  }

  setMode(newMode) {
    this.mode = newMode;
  }

  setFitMode(newFitMode) {
    this.fitMode = newFitMode;
  }

  _getNormalizedCoords(e) {
    const rect = this.canvas.getBoundingClientRect();
    const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
    const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

    if (this.fitMode === "fill") {
      const x = Math.max(0, Math.min(1, (clientX - rect.left) / (rect.width || 1)));
      const y = Math.max(0, Math.min(1, (clientY - rect.top) / (rect.height || 1)));
      return { x, y };
    }

    const canvasRatio = this.canvas.width / (this.canvas.height || 1);
    const viewRatio = rect.width / (rect.height || 1);

    let renderW = rect.width;
    let renderH = rect.height;
    let offsetX = 0;
    let offsetY = 0;

    if (viewRatio > canvasRatio) {
      renderW = rect.height * canvasRatio;
      offsetX = (rect.width - renderW) / 2;
    } else {
      renderH = rect.width / canvasRatio;
      offsetY = (rect.height - renderH) / 2;
    }

    const touchX = clientX - rect.left - offsetX;
    const touchY = clientY - rect.top - offsetY;

    const x = Math.max(0, Math.min(1, touchX / (renderW || 1)));
    const y = Math.max(0, Math.min(1, touchY / (renderH || 1)));
    return { x, y };
  }

  _bindTouchEvents() {
    this.canvas.addEventListener("touchstart", (e) => {
      e.preventDefault();
      this.touchStartTime = performance.now();

      if (e.touches.length === 1) {
        const { x, y } = this._getNormalizedCoords(e);
        this.touchStartX = x;
        this.touchStartY = y;
        this.lastTrackpadX = e.touches[0].clientX;
        this.lastTrackpadY = e.touches[0].clientY;

        if (this.mode === "touch") {
          this.send({ type: "mouse_down", x, y, button: "left" });
          this.isDragging = true;
        }
      } else if (e.touches.length === 2) {
        this.twoFingerStartY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        if (this.isDragging) {
          this.send({ type: "mouse_up", x: this.touchStartX, y: this.touchStartY, button: "left" });
          this.isDragging = false;
        }
      }
    }, { passive: false });

    this.canvas.addEventListener("touchmove", (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        const { x, y } = this._getNormalizedCoords(e);
        if (this.mode === "touch") {
          this.send({ type: "mouse_move", x, y });
        } else {
          // Trackpad relative delta mode
          const dx = (e.touches[0].clientX - this.lastTrackpadX) / window.innerWidth;
          const dy = (e.touches[0].clientY - this.lastTrackpadY) / window.innerHeight;
          this.lastTrackpadX = e.touches[0].clientX;
          this.lastTrackpadY = e.touches[0].clientY;

          this.touchStartX = Math.max(0, Math.min(1, this.touchStartX + dx * 1.6));
          this.touchStartY = Math.max(0, Math.min(1, this.touchStartY + dy * 1.6));
          this.send({ type: "mouse_move", x: this.touchStartX, y: this.touchStartY });
        }
      } else if (e.touches.length === 2) {
        // Two-finger scroll
        const currentTwoY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const delta = (currentTwoY - this.twoFingerStartY) * 0.05;
        this.twoFingerStartY = currentTwoY;
        if (Math.abs(delta) > 0.08) {
          this.send({ type: "wheel", deltaY: delta });
        }
      }
    }, { passive: false });

    this.canvas.addEventListener("touchend", (e) => {
      e.preventDefault();
      const elapsed = performance.now() - this.touchStartTime;

      if (e.touches.length === 0) {
        if (this.mode === "touch") {
          const { x, y } = this._getNormalizedCoords(e.changedTouches[0]);
          this.send({ type: "mouse_up", x, y, button: "left" });
          this.isDragging = false;
        } else {
          // Trackpad tap = click
          if (elapsed < 240) {
            this.send({ type: "click", x: this.touchStartX, y: this.touchStartY, button: "left" });
          }
        }
      }
    }, { passive: false });
  }

  _bindMouseEvents() {
    this.canvas.addEventListener("mousedown", (e) => {
      const { x, y } = this._getNormalizedCoords(e);
      const btn = e.button === 2 ? "right" : (e.button === 1 ? "middle" : "left");
      this.send({ type: "mouse_down", x, y, button: btn });
    });

    this.canvas.addEventListener("mousemove", (e) => {
      const { x, y } = this._getNormalizedCoords(e);
      this.send({ type: "mouse_move", x, y });
    });

    this.canvas.addEventListener("mouseup", (e) => {
      const { x, y } = this._getNormalizedCoords(e);
      const btn = e.button === 2 ? "right" : (e.button === 1 ? "middle" : "left");
      this.send({ type: "mouse_up", x, y, button: btn });
    });

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.send({ type: "wheel", deltaY: e.deltaY > 0 ? -1 : 1 });
    }, { passive: false });

    this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  }
}

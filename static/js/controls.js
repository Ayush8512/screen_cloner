/**
 * AirScreen Advanced Remote Input & Gesture Engine
 * Supports: Direct Touch, Dedicated Trackpad, Pinch-to-Zoom & Pan, Wheel Scrolling & Haptics
 */

class InputManager {
  constructor(canvasElement, onSendEvent) {
    this.canvas = canvasElement;
    this.send = onSendEvent;

    this.mode = "touch"; // "touch" or "trackpad"
    this.fitMode = "contain"; // "contain" or "fill"
    this.sensitivity = 1.5;

    // Gesture & Touch state
    this.touchStartTime = 0;
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.lastTouchX = 0;
    this.lastTouchY = 0;
    this.isDragging = false;

    // Pinch-to-Zoom & Pan state
    this.zoomScale = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.initialPinchDist = 0;
    this.initialPinchScale = 1.0;
    this.lastTwoMidX = 0;
    this.lastTwoMidY = 0;
    this.twoFingerStartY = 0;

    // Zoom badge elements
    this.zoomBadge = document.getElementById("zoom-badge");
    this.zoomLevelLabel = document.getElementById("zoom-level");
    this.resetZoomBtn = document.getElementById("reset-zoom-btn");

    if (this.resetZoomBtn) {
      this.resetZoomBtn.addEventListener("click", () => this.resetZoom());
    }

    this._bindCanvasTouchEvents();
    this._bindCanvasMouseEvents();
    this._bindVirtualTrackpad();
    this.requestWakeLock();
  }

  setFitMode(fitMode) {
    this.fitMode = fitMode;
    this.resetZoom();
  }

  setSensitivity(val) {
    this.sensitivity = parseFloat(val) || 1.5;
  }

  vibrate(ms = 12) {
    if (navigator.vibrate) {
      try { navigator.vibrate(ms); } catch (e) {}
    }
  }

  requestWakeLock() {
    if ("wakeLock" in navigator) {
      navigator.wakeLock.request("screen").catch(() => {});
    }
  }

  resetZoom() {
    this.zoomScale = 1.0;
    this.panX = 0;
    this.panY = 0;
    this._updateTransform();
    if (this.zoomBadge) this.zoomBadge.classList.add("hidden");
  }

  _updateTransform() {
    this.canvas.style.transform = `scale(${this.zoomScale}) translate(${this.panX}px, ${this.panY}px)`;
    if (this.zoomBadge && this.zoomLevelLabel) {
      if (this.zoomScale > 1.05) {
        this.zoomBadge.classList.remove("hidden");
        this.zoomLevelLabel.textContent = `${Math.round(this.zoomScale * 100)}%`;
      } else {
        this.zoomBadge.classList.add("hidden");
      }
    }
  }

  _getPinchDist(t1, t2) {
    const dx = t1.clientX - t2.clientX;
    const dy = t1.clientY - t2.clientY;
    return Math.hypot(dx, dy);
  }

  _getNormalizedCoords(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();

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

  _bindCanvasTouchEvents() {
    this.canvas.addEventListener("touchstart", (e) => {
      e.preventDefault();
      this.touchStartTime = performance.now();

      if (e.touches.length === 1) {
        const { x, y } = this._getNormalizedCoords(e.touches[0].clientX, e.touches[0].clientY);
        this.touchStartX = x;
        this.touchStartY = y;
        this.lastTouchX = e.touches[0].clientX;
        this.lastTouchY = e.touches[0].clientY;

        if (this.zoomScale <= 1.05) {
          this.send({ type: "mouse_down", x, y, button: "left" });
          this.isDragging = true;
        }
      } else if (e.touches.length === 2) {
        // Prepare for pinch zoom or scroll
        if (this.isDragging) {
          this.send({ type: "mouse_up", x: this.touchStartX, y: this.touchStartY, button: "left" });
          this.isDragging = false;
        }
        this.initialPinchDist = this._getPinchDist(e.touches[0], e.touches[1]);
        this.initialPinchScale = this.zoomScale;
        this.twoFingerStartY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        this.lastTwoMidX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        this.lastTwoMidY = this.twoFingerStartY;
      }
    }, { passive: false });

    this.canvas.addEventListener("touchmove", (e) => {
      e.preventDefault();

      if (e.touches.length === 1) {
        if (this.zoomScale > 1.05) {
          // Pan canvas when zoomed in
          const dx = (e.touches[0].clientX - this.lastTouchX) / this.zoomScale;
          const dy = (e.touches[0].clientY - this.lastTouchY) / this.zoomScale;
          this.panX += dx;
          this.panY += dy;
          this.lastTouchX = e.touches[0].clientX;
          this.lastTouchY = e.touches[0].clientY;
          this._updateTransform();
        } else {
          const { x, y } = this._getNormalizedCoords(e.touches[0].clientX, e.touches[0].clientY);
          this.send({ type: "mouse_move", x, y });
        }
      } else if (e.touches.length === 2) {
        const currentDist = this._getPinchDist(e.touches[0], e.touches[1]);
        const distDiff = Math.abs(currentDist - this.initialPinchDist);

        if (distDiff > 20) {
          // Pinch Zooming
          const scaleChange = currentDist / (this.initialPinchDist || 1);
          this.zoomScale = Math.max(1.0, Math.min(3.5, this.initialPinchScale * scaleChange));
          this._updateTransform();
        } else {
          // Two-finger scroll
          const currentTwoY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
          const delta = (currentTwoY - this.twoFingerStartY) * 0.06;
          this.twoFingerStartY = currentTwoY;
          if (Math.abs(delta) > 0.08) {
            this.send({ type: "wheel", deltaY: delta });
          }
        }
      }
    }, { passive: false });

    this.canvas.addEventListener("touchend", (e) => {
      e.preventDefault();
      const elapsed = performance.now() - this.touchStartTime;

      if (e.touches.length === 0) {
        if (this.isDragging) {
          const changedTouch = e.changedTouches[0];
          const { x, y } = this._getNormalizedCoords(changedTouch.clientX, changedTouch.clientY);
          this.send({ type: "mouse_up", x, y, button: "left" });
          this.isDragging = false;
        }

        // Two finger tap = Right Click
        if (e.changedTouches.length === 2 && elapsed < 300) {
          this.vibrate(18);
          this.send({ type: "click", x: this.touchStartX, y: this.touchStartY, button: "right" });
        }
      }
    }, { passive: false });
  }

  _bindCanvasMouseEvents() {
    this.canvas.addEventListener("mousedown", (e) => {
      const { x, y } = this._getNormalizedCoords(e.clientX, e.clientY);
      const btn = e.button === 2 ? "right" : (e.button === 1 ? "middle" : "left");
      this.send({ type: "mouse_down", x, y, button: btn });
    });

    this.canvas.addEventListener("mousemove", (e) => {
      const { x, y } = this._getNormalizedCoords(e.clientX, e.clientY);
      this.send({ type: "mouse_move", x, y });
    });

    this.canvas.addEventListener("mouseup", (e) => {
      const { x, y } = this._getNormalizedCoords(e.clientX, e.clientY);
      const btn = e.button === 2 ? "right" : (e.button === 1 ? "middle" : "left");
      this.send({ type: "mouse_up", x, y, button: btn });
    });

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.send({ type: "wheel", deltaY: e.deltaY > 0 ? -1 : 1 });
    }, { passive: false });

    this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  _bindVirtualTrackpad() {
    const pad = document.getElementById("virtual-trackpad");
    const btnLeft = document.getElementById("btn-left-click");
    const btnRight = document.getElementById("btn-right-click");
    const btnMid = document.getElementById("btn-mid-click");
    const slider = document.getElementById("sensitivity-slider");
    const sliderVal = document.getElementById("sensitivity-val");

    if (slider) {
      slider.addEventListener("input", (e) => {
        this.setSensitivity(e.target.value);
        if (sliderVal) sliderVal.textContent = `${e.target.value}x`;
      });
    }

    if (btnLeft) {
      btnLeft.addEventListener("click", () => {
        this.vibrate(15);
        this.send({ type: "click", button: "left" });
      });
    }

    if (btnRight) {
      btnRight.addEventListener("click", () => {
        this.vibrate(20);
        this.send({ type: "click", button: "right" });
      });
    }

    if (btnMid) {
      btnMid.addEventListener("click", () => {
        this.vibrate(15);
        this.send({ type: "click", button: "middle" });
      });
    }

    if (!pad) return;

    let padStartX = 0;
    let padStartY = 0;
    let padTouchStart = 0;

    pad.addEventListener("touchstart", (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        padStartX = e.touches[0].clientX;
        padStartY = e.touches[0].clientY;
        padTouchStart = performance.now();
      }
    }, { passive: false });

    pad.addEventListener("touchmove", (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        const dx = (e.touches[0].clientX - padStartX) / window.innerWidth;
        const dy = (e.touches[0].clientY - padStartY) / window.innerHeight;
        padStartX = e.touches[0].clientX;
        padStartY = e.touches[0].clientY;

        this.touchStartX = Math.max(0, Math.min(1, (this.touchStartX || 0.5) + dx * this.sensitivity));
        this.touchStartY = Math.max(0, Math.min(1, (this.touchStartY || 0.5) + dy * this.sensitivity));

        this.send({ type: "mouse_move", x: this.touchStartX, y: this.touchStartY });
      } else if (e.touches.length === 2) {
        // Trackpad 2-finger scroll
        const dy = e.touches[0].clientY - padStartY;
        padStartY = e.touches[0].clientY;
        if (Math.abs(dy) > 2) {
          this.send({ type: "wheel", deltaY: dy * 0.05 });
        }
      }
    }, { passive: false });

    pad.addEventListener("touchend", (e) => {
      e.preventDefault();
      const elapsed = performance.now() - padTouchStart;
      if (e.touches.length === 0 && elapsed < 220) {
        this.vibrate(12);
        this.send({ type: "click", x: this.touchStartX, y: this.touchStartY, button: "left" });
      }
    }, { passive: false });
  }
}

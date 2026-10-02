/**
 * AirScreen Hardware-Accelerated Canvas Frame Renderer
 */

class FrameRenderer {
  constructor(canvasElement, onFpsUpdate) {
    this.canvas = canvasElement;
    this.ctx = this.canvas.getContext("2d", { alpha: false, desynchronized: true });
    this.onFpsUpdate = onFpsUpdate || (() => {});

    this.frameCount = 0;
    this.lastFpsTime = performance.now();
    this.isRendering = false;
  }

  setDimensions(width, height) {
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
  }

  async renderFrame(arrayBuffer) {
    try {
      const blob = new Blob([arrayBuffer], { type: "image/jpeg" });
      const bitmap = await createImageBitmap(blob);

      if (this.canvas.width !== bitmap.width || this.canvas.height !== bitmap.height) {
        this.canvas.width = bitmap.width;
        this.canvas.height = bitmap.height;
      }

      this.ctx.drawImage(bitmap, 0, 0);
      bitmap.close();

      this.frameCount++;
      const now = performance.now();
      if (now - this.lastFpsTime >= 1000) {
        this.onFpsUpdate(this.frameCount);
        this.frameCount = 0;
        this.lastFpsTime = now;
      }
    } catch (err) {
      console.error("[Renderer] Frame decode error:", err);
    }
  }
}

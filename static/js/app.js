/**
 * AirScreen Client Application Orchestrator
 */

document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("screen-canvas");
  const splash = document.getElementById("splash");
  const statusDot = document.getElementById("status-dot");
  const statusLabel = document.getElementById("status-label");
  const fpsBadge = document.getElementById("fps-badge");
  const pingBadge = document.getElementById("ping-badge");
  const monitorBadge = document.getElementById("monitor-badge");
  const monitorBtn = document.getElementById("monitor-btn");
  const monitorLabel = document.getElementById("monitor-label");
  const modeBtn = document.getElementById("mode-btn");
  const modeLabel = document.getElementById("mode-label");
  const qualityBtn = document.getElementById("quality-btn");
  const qualityLabel = document.getElementById("quality-label");
  const kbdBtn = document.getElementById("kbd-btn");
  const hiddenInput = document.getElementById("hidden-input");
  const fullscreenBtn = document.getElementById("fullscreen-btn");
  const fitBtn = document.getElementById("fit-btn");
  const fitLabel = document.getElementById("fit-label");
  const dock = document.getElementById("dock");
  const hud = document.getElementById("hud");
  const hudToggle = document.getElementById("hud-toggle");

  let monitors = [];
  let selectedMonitor = 1;
  let dockVisible = true;
  let fitMode = "contain";

  const qualityProfiles = [
    { name: "540p", scale: 0.5, quality: 50 },
    { name: "720p", scale: 0.75, quality: 65 },
    { name: "1080p", scale: 1.0, quality: 80 },
  ];
  let qualityIndex = 1;

  // Initialize Renderer
  const renderer = new FrameRenderer(canvas, (fps) => {
    fpsBadge.textContent = `${fps} FPS`;
  });

  // Initialize Connection
  const connection = new ConnectionManager({
    onFrame: async (arrayBuffer) => {
      await renderer.renderFrame(arrayBuffer);
      connection.sendAck();
    },
    onInit: (initData) => {
      renderer.setDimensions(initData.screenWidth, initData.screenHeight);

      if (initData.monitors && initData.monitors.length > 1) {
        monitors = initData.monitors;
        monitorBtn.style.display = "flex";
        monitorBadge.style.display = "inline-block";
      } else {
        monitors = initData.monitors || [];
        monitorBtn.style.display = "none";
        monitorBadge.style.display = "none";
      }

      if (initData.selectedMonitor) {
        selectedMonitor = initData.selectedMonitor;
        monitorLabel.textContent = `Display ${selectedMonitor}`;
        monitorBadge.textContent = selectedMonitor === 2 ? "Display 2 (Extended)" : `Display ${selectedMonitor}`;
      }

      setTimeout(() => splash.classList.add("dismissed"), 300);
    },
    onStatusChange: (connected) => {
      if (connected) {
        statusDot.classList.remove("disconnected");
        statusLabel.textContent = "Live";
      } else {
        statusDot.classList.add("disconnected");
        statusLabel.textContent = "Offline";
        splash.classList.remove("dismissed");
      }
    },
    onPingUpdate: (ping) => {
      pingBadge.textContent = `${ping} ms`;
    },
  });

  // Initialize Input Controls
  const input = new InputManager(canvas, (event) => connection.send(event));

  // Mode Toggle (Touch vs Trackpad)
  modeBtn.addEventListener("click", () => {
    if (input.mode === "touch") {
      input.setMode("trackpad");
      modeLabel.textContent = "Trackpad";
      modeBtn.classList.remove("active");
    } else {
      input.setMode("touch");
      modeLabel.textContent = "Direct Touch";
      modeBtn.classList.add("active");
    }
  });

  // Display Monitor Switch
  monitorBtn.addEventListener("click", () => {
    if (monitors.length <= 1) return;
    const currentIdx = monitors.findIndex((m) => m.id === selectedMonitor);
    const nextIdx = (currentIdx + 1) % monitors.length;
    const nextMon = monitors[nextIdx];
    connection.send({ type: "select_monitor", idx: nextMon.id });
  });

  // Quality Toggle
  qualityBtn.addEventListener("click", () => {
    qualityIndex = (qualityIndex + 1) % qualityProfiles.length;
    const profile = qualityProfiles[qualityIndex];
    qualityLabel.textContent = profile.name;
    connection.send({
      type: "settings",
      quality: profile.quality,
      scale: profile.scale,
    });
  });

  // Virtual Keyboard
  kbdBtn.addEventListener("click", () => {
    hiddenInput.focus();
  });

  hiddenInput.addEventListener("input", () => {
    if (hiddenInput.value) {
      connection.send({ type: "type_text", text: hiddenInput.value });
      hiddenInput.value = "";
    }
  });

  hiddenInput.addEventListener("keydown", (e) => {
    if (["Backspace", "Enter", "Tab", "Escape"].includes(e.key)) {
      connection.send({ type: "key", key: e.key });
    }
  });

  // Quick Action Keys
  window.sendKey = function (key) {
    connection.send({ type: "key", key });
  };

  // Fullscreen
  fullscreenBtn.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  });

  // Aspect Ratio & Fit Mode Toggle (Contain vs Fill Screen)
  fitBtn.addEventListener("click", () => {
    if (fitMode === "contain") {
      fitMode = "fill";
      canvas.style.objectFit = "fill";
      fitLabel.textContent = "Ratio";
      fitBtn.classList.add("active");
      input.setFitMode("fill");
    } else {
      fitMode = "contain";
      canvas.style.objectFit = "contain";
      fitLabel.textContent = "Fill";
      fitBtn.classList.remove("active");
      input.setFitMode("contain");
    }
  });

  // HUD & Dock Toggle
  hudToggle.addEventListener("click", () => {
    dockVisible = !dockVisible;
    if (dockVisible) {
      dock.classList.remove("hidden");
      hud.style.opacity = "1";
    } else {
      dock.classList.add("hidden");
      hud.style.opacity = "0";
    }
  });

  // Start connection
  connection.connect();
});

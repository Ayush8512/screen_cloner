/**
 * AirScreen Client Application Orchestrator
 * Coordinates Renderer, Connection, Touch Controls, PWA installation, and Drawer Navigation
 */

document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("screen-canvas");
  const splash = document.getElementById("splash");
  const statusDot = document.getElementById("status-dot");
  const fpsBadge = document.getElementById("fps-badge");
  const pingBadge = document.getElementById("ping-badge");
  const monitorBadge = document.getElementById("monitor-badge");
  const hiddenInput = document.getElementById("hidden-input");

  // Drawer & Pill elements
  const actionPill = document.getElementById("action-pill");
  const openDrawerBtn = document.getElementById("open-drawer-btn");
  const drawer = document.getElementById("drawer");
  const drawerOverlay = document.getElementById("drawer-overlay");
  const drawerCloseBtn = document.getElementById("drawer-close-btn");
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  // Display & Mode buttons
  const fullscreenBtn = document.getElementById("fullscreen-btn");
  const kbdTriggerBtn = document.getElementById("kbd-trigger-btn");
  const fitContainBtn = document.getElementById("fit-contain-btn");
  const fitFillBtn = document.getElementById("fit-fill-btn");
  const btnMon1 = document.getElementById("btn-mon-1");
  const btnMon2 = document.getElementById("btn-mon-2");

  // PWA elements
  const pwaBanner = document.getElementById("pwa-banner");
  const pwaInstallBtn = document.getElementById("pwa-install-btn");
  const pwaDismissBtn = document.getElementById("pwa-dismiss-btn");
  let deferredPrompt = null;

  let monitors = [];
  let selectedMonitor = 1;
  let autoDimTimeout = null;

  // Initialize Renderer
  const renderer = new FrameRenderer(canvas, (fps) => {
    if (fpsBadge) fpsBadge.textContent = `${fps} FPS`;
  });

  // Initialize Connection
  const connection = new ConnectionManager({
    onFrame: async (arrayBuffer) => {
      await renderer.renderFrame(arrayBuffer);
      connection.sendAck();
    },
    onInit: (initData) => {
      renderer.setDimensions(initData.screenWidth, initData.screenHeight);

      if (initData.monitors) {
        monitors = initData.monitors;
      }

      if (initData.selectedMonitor) {
        selectedMonitor = initData.selectedMonitor;
        updateMonitorUI(selectedMonitor);
      }

      setTimeout(() => splash.classList.add("dismissed"), 300);
    },
    onStatusChange: (connected) => {
      if (connected) {
        statusDot.classList.remove("disconnected");
      } else {
        statusDot.classList.add("disconnected");
        splash.classList.remove("dismissed");
      }
    },
    onPingUpdate: (ping) => {
      if (pingBadge) pingBadge.textContent = `${ping} ms`;
    },
  });

  // Initialize Input Controls
  const input = new InputManager(canvas, (event) => connection.send(event));

  // Auto-dim action pill after inactivity
  function resetAutoDim() {
    if (actionPill) {
      actionPill.classList.remove("dimmed");
      clearTimeout(autoDimTimeout);
      autoDimTimeout = setTimeout(() => {
        if (!drawer.classList.contains("open")) {
          actionPill.classList.add("dimmed");
        }
      }, 4000);
    }
  }

  window.addEventListener("touchstart", resetAutoDim, { passive: true });
  window.addEventListener("mousemove", resetAutoDim, { passive: true });
  resetAutoDim();

  // Drawer Management
  function openDrawer() {
    drawer.classList.add("open");
    drawerOverlay.classList.add("active");
    if (actionPill) actionPill.classList.remove("dimmed");
    input.vibrate(10);
  }

  function closeDrawer() {
    drawer.classList.remove("open");
    drawerOverlay.classList.remove("active");
    resetAutoDim();
  }

  if (openDrawerBtn) openDrawerBtn.addEventListener("click", openDrawer);
  if (drawerCloseBtn) drawerCloseBtn.addEventListener("click", closeDrawer);
  if (drawerOverlay) drawerOverlay.addEventListener("click", closeDrawer);

  // Tab Navigation inside Drawer
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      input.vibrate(8);
      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetTab = btn.getAttribute("data-tab");
      const pane = document.getElementById(targetTab);
      if (pane) pane.classList.add("active");
    });
  });

  // Monitor Switcher
  function updateMonitorUI(monId) {
    if (monitorBadge) {
      monitorBadge.textContent = monId === 2 ? "Display 2 (Ext)" : "Display 1";
    }
    if (btnMon1 && btnMon2) {
      if (monId === 1) {
        btnMon1.classList.add("active");
        btnMon2.classList.remove("active");
      } else {
        btnMon1.classList.remove("active");
        btnMon2.classList.add("active");
      }
    }
  }

  window.switchMonitor = function (monitorId) {
    input.vibrate(12);
    selectedMonitor = monitorId;
    updateMonitorUI(monitorId);
    connection.send({ type: "select_monitor", idx: monitorId });
  };

  // Quality Profiles
  const qualityPresets = {
    "540p": { scale: 0.5, quality: 50 },
    "720p": { scale: 0.75, quality: 65 },
    "1080p": { scale: 1.0, quality: 80 },
  };

  window.setQualityPreset = function (presetName) {
    input.vibrate(10);
    const preset = qualityPresets[presetName];
    if (preset) {
      document.querySelectorAll("[data-quality]").forEach((b) => {
        b.classList.toggle("active", b.getAttribute("data-quality") === presetName);
      });
      connection.send({
        type: "settings",
        quality: preset.quality,
        scale: preset.scale,
      });
    }
  };

  // Screen Fit Mode
  window.setFitMode = function (mode) {
    input.vibrate(10);
    if (mode === "fill") {
      canvas.style.objectFit = "fill";
      if (fitFillBtn) fitFillBtn.classList.add("active");
      if (fitContainBtn) fitContainBtn.classList.remove("active");
      input.setFitMode("fill");
    } else {
      canvas.style.objectFit = "contain";
      if (fitContainBtn) fitContainBtn.classList.add("active");
      if (fitFillBtn) fitFillBtn.classList.remove("active");
      input.setFitMode("contain");
    }
  };

  // Fullscreen
  if (fullscreenBtn) {
    fullscreenBtn.addEventListener("click", () => {
      input.vibrate(12);
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  // Virtual Keyboard
  if (kbdTriggerBtn) {
    kbdTriggerBtn.addEventListener("click", () => {
      input.vibrate(10);
      closeDrawer();
      setTimeout(() => {
        hiddenInput.focus();
      }, 300);
    });
  }

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

  // Global Dispatchers for HTML inline onclick
  window.sendKey = function (key) {
    input.vibrate(10);
    connection.send({ type: "key", key });
  };

  window.sendHotkey = function (combo) {
    input.vibrate(15);
    connection.send({ type: "hotkey", combo });
  };

  // PWA Install Handling
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (pwaBanner) pwaBanner.classList.remove("hidden");
  });

  if (pwaInstallBtn) {
    pwaInstallBtn.addEventListener("click", async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === "accepted") {
          if (pwaBanner) pwaBanner.classList.add("hidden");
        }
        deferredPrompt = null;
      }
    });
  }

  if (pwaDismissBtn) {
    pwaDismissBtn.addEventListener("click", () => {
      if (pwaBanner) pwaBanner.classList.add("hidden");
    });
  }

  // Start WebSocket connection
  connection.connect();
});

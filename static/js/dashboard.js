/**
 * AirScreen Host Desktop Control Center Dashboard Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  const ifaceSelect = document.getElementById("iface-select");
  const connectionUrl = document.getElementById("connection-url");
  const qrImg = document.getElementById("qr-img");
  const copyUrlBtn = document.getElementById("copy-url-btn");
  const openClientTabBtn = document.getElementById("open-client-tab-btn");

  const driverStatusBadge = document.getElementById("driver-status-badge");
  const btnDriverInstall = document.getElementById("btn-driver-install");
  const btnDriverRemove = document.getElementById("btn-driver-remove");
  const btnDriverSettings = document.getElementById("btn-driver-settings");

  const monitorCountLabel = document.getElementById("monitor-count-label");
  const monitorsPreviewContainer = document.getElementById("monitors-preview-container");

  const clientCountBadge = document.getElementById("client-count-badge");
  const clientsListContainer = document.getElementById("clients-list-container");

  let currentPort = 8000;
  let selectedIp = "127.0.0.1";
  let interfacesLoaded = false;
  let activeMonitorId = 1;

  // Fetch telemetry & system state
  async function refreshStats() {
    try {
      const res = await fetch("/api/system/stats");
      if (!res.ok) return;
      const data = await res.json();

      currentPort = data.port || 8000;
      activeMonitorId = data.active_monitor ? data.active_monitor.id : 1;

      // Populate Network Interfaces dropdown once or if empty
      if (!interfacesLoaded && data.interfaces && data.interfaces.length > 0) {
        ifaceSelect.innerHTML = "";
        data.interfaces.forEach((iface, idx) => {
          const opt = document.createElement("option");
          opt.value = iface.ip;
          opt.textContent = `${iface.label} - ${iface.ip}`;
          if (idx === 0) {
            opt.selected = true;
            selectedIp = iface.ip;
          }
          ifaceSelect.appendChild(opt);
        });
        interfacesLoaded = true;
        updateConnectionDetails();
      }

      // Update Driver status badge
      if (data.driver_active) {
        driverStatusBadge.textContent = "Driver Active & Running";
        driverStatusBadge.className = "badge badge-success";
      } else {
        driverStatusBadge.textContent = "Driver Inactive / Removed";
        driverStatusBadge.className = "badge badge-warning";
      }

      // Update Monitors List
      renderMonitors(data.monitors || [], activeMonitorId);

      // Update Connected Clients
      renderClients(data.clients || []);

    } catch (e) {
      console.error("Failed to fetch dashboard stats:", e);
    }
  }

  function updateConnectionDetails() {
    selectedIp = ifaceSelect.value || "127.0.0.1";
    const fullUrl = `http://${selectedIp}:${currentPort}`;
    connectionUrl.textContent = fullUrl;

    // Refresh QR code
    qrImg.src = `/static/qr.png?v=${Date.now()}`;
  }

  ifaceSelect.addEventListener("change", () => {
    updateConnectionDetails();
  });

  // Copy Connection URL
  copyUrlBtn.addEventListener("click", () => {
    const url = connectionUrl.textContent;
    navigator.clipboard.writeText(url).then(() => {
      copyUrlBtn.textContent = "✓ Copied!";
      setTimeout(() => (copyUrlBtn.textContent = "📋 Copy"), 2000);
    });
  });

  // Open Client in Browser Tab
  openClientTabBtn.addEventListener("click", () => {
    window.open(connectionUrl.textContent, "_blank");
  });

  // Render Monitor Cards
  function renderMonitors(monitors, activeId) {
    monitorCountLabel.textContent = `${monitors.length} Monitor${monitors.length > 1 ? "s" : ""} Detected`;
    monitorsPreviewContainer.innerHTML = "";

    monitors.forEach((mon) => {
      const isCurrentActive = mon.id === activeId;
      const card = document.createElement("div");
      card.className = `monitor-preview-card ${isCurrentActive ? "active" : ""}`;
      card.title = isCurrentActive ? "Currently Broadcasting" : "Click to Broadcast This Screen";

      card.innerHTML = `
        <div class="monitor-thumb-frame">
          <img src="/api/system/thumbnail/${mon.id}?t=${Date.now()}" alt="${mon.name}" onerror="this.src='/static/icon.svg';">
        </div>
        <div class="monitor-info">
          <div>
            <div class="mon-name">${mon.name}</div>
            <div class="mon-res">${mon.width} x ${mon.height} ${mon.is_primary ? "(Main)" : "(Extended)"}</div>
          </div>
          <span class="badge ${isCurrentActive ? "badge-accent" : "badge-secondary"}">
            ${isCurrentActive ? "● Active Stream" : "Switch"}
          </span>
        </div>
      `;

      card.addEventListener("click", async () => {
        try {
          await fetch(`/api/monitors/select/${mon.id}`, { method: "POST" });
          refreshStats();
        } catch (e) {}
      });

      monitorsPreviewContainer.appendChild(card);
    });
  }

  // Render Connected Devices List
  function renderClients(clients) {
    clientCountBadge.textContent = `${clients.length} Device${clients.length !== 1 ? "s" : ""}`;

    if (clients.length === 0) {
      clientsListContainer.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📱</span>
          <span>No devices currently connected. Scan the QR code to connect.</span>
        </div>
      `;
      return;
    }

    clientsListContainer.innerHTML = "";
    clients.forEach((client) => {
      const row = document.createElement("div");
      row.className = "client-row";

      let icon = "📱";
      if (client.device.includes("Tablet") || client.device.includes("iPad")) icon = "📟";
      else if (client.device.includes("Windows") || client.device.includes("Mac")) icon = "💻";

      row.innerHTML = `
        <div class="client-details">
          <span class="client-icon">${icon}</span>
          <div>
            <div class="client-title">${client.device}</div>
            <div class="client-meta">${client.ip} • Ping: ${client.ping_ms} ms • Connected: ${client.connected_seconds}s ago</div>
          </div>
        </div>
        <button class="btn btn-sm btn-secondary" onclick="disconnectDevice('${client.id}')">Disconnect</button>
      `;

      clientsListContainer.appendChild(row);
    });
  }

  window.disconnectDevice = async function (clientId) {
    try {
      await fetch(`/api/clients/disconnect/${clientId}`, { method: "POST" });
      refreshStats();
    } catch (e) {}
  };

  // Driver Actions
  async function triggerDriverAction(action) {
    try {
      await fetch("/api/driver/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      setTimeout(refreshStats, 2000);
    } catch (e) {}
  }

  btnDriverInstall.addEventListener("click", () => triggerDriverAction("install"));
  btnDriverRemove.addEventListener("click", () => triggerDriverAction("remove"));
  btnDriverSettings.addEventListener("click", () => triggerDriverAction("settings"));

  // Initial fetch and 2.5s polling loop
  refreshStats();
  setInterval(refreshStats, 2500);
});

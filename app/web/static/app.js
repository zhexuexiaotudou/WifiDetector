const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "—").replace(
  /[&<>"']/g,
  (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char],
);

async function json(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function time(value) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "尚无";
}

async function loadDashboard() {
  if (!$("#roomGrid")) return;
  const [health, rooms] = await Promise.all([json("/api/health"), json("/api/rooms")]);
  $("#running").textContent = health.running ? "运行中" : "待命";
  $("#currentRoom").textContent = health.current_room || "—";
  $("#progress").textContent = `${health.rooms_completed} / 8`;
  $("#pending").textContent = health.pending_events;
  $("#faults").textContent = health.system_faults;
  $("#lastUpdated").textContent = `更新于 ${time(health.server_time)}`;
  $("#roomGrid").innerHTML = rooms.map((room) => {
    const unknown = (room.clients || []).filter((client) => !client.is_monitor_pc).length;
    const tv = room.iptv?.state === "active"
      ? "IPTV 明确活跃"
      : room.capabilities?.iptv_state
        ? "IPTV 未活跃"
        : "HDMI/IPTV 证据不可用";
    return `<article class="room-card">
      <div class="room-top"><h3>${esc(room.room_id)}</h3><span class="status ${room.reachable ? "ok" : "pending"}">${room.reachable ? "已采样" : "数据不足"}</span></div>
      <ul><li>匿名客户端 ${room.clients?.length ?? 0}</li><li>待校准设备 ${unknown}</li><li>${esc(tv)}</li><li>最新样本 ${time(room.captured_at)}</li></ul>
      <a href="/rooms/${esc(room.room_id)}">查看证据与事件 →</a>
    </article>`;
  }).join("");
}

async function loadRoom() {
  const root = $("#roomDetail");
  if (!root) return;
  try {
    const detail = await json(`/api/rooms/${root.dataset.room}`);
    root.innerHTML = `<article class="panel"><h2>最新样本</h2><p>${time(detail.captured_at)}</p><p>来源：${esc(detail.raw_source)}</p><p>客户端：${detail.clients.length}</p><p>完整 MAC 与主机名不会持久化。</p></article>
      <article class="panel"><h2>电视业务能力</h2><p>${detail.capabilities.iptv_state ? "存在明确 IPTV 状态证据" : "当前网关不提供已验证的明确状态证据"}</p><p>${detail.iptv?.state === "active" ? "IPTV 业务活跃" : "不能判断 HDMI 电视是否亮屏"}</p></article>
      <article class="panel"><h2>匿名设备</h2>${detail.clients.map((client) => `<p><code>${esc(client.device_id)}</code> ${client.is_monitor_pc ? "监测电脑" : "待校准"} · ${esc(client.rx_rate_bps)} bps</p>`).join("")}</article>
      <article class="panel"><h2>最近事件</h2>${detail.events.slice(0, 8).map((event) => `<p>${esc(event.event_type)} · ${(event.confidence * 100).toFixed(0)}% · ${esc(event.review_status || "待复核")}</p>`).join("") || "<p>无</p>"}</article>`;
  } catch (_error) {
    root.innerHTML = "<article class=\"panel\"><h2>数据不足</h2><p>请先运行一轮扫描。</p></article>";
  }
}

async function loadEvents() {
  const root = $("#eventList");
  if (!root) return;
  const events = await json("/api/events");
  root.innerHTML = events.length
    ? events.map((event) => `<article class="panel event"><strong>${esc(event.room_id)}</strong><span>${esc(event.event_type)}</span><div><p>${esc(event.reasons?.join("；"))}</p><small>${time(event.occurred_at)} · ${esc(event.review_status || "待人工复核")}</small></div><strong class="confidence">${(event.confidence * 100).toFixed(0)}%</strong></article>`).join("")
    : "<article class=\"panel\">暂无事件</article>";
}

document.addEventListener("DOMContentLoaded", () => {
  loadDashboard().catch(console.error);
  loadRoom().catch(console.error);
  loadEvents().catch(console.error);
  let dashboardPoll = null;
  if ($("#roomGrid")) {
    dashboardPoll = window.setInterval(() => loadDashboard().catch(console.error), 1000);
  }
  window.addEventListener("pagehide", () => {
    if (dashboardPoll !== null) window.clearInterval(dashboardPoll);
  });

  $("#scanButton")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "正在顺序扫描 8 个房间…";
    try {
      await json("/api/scan-cycle", { method: "POST" });
    } finally {
      await loadDashboard();
      button.disabled = false;
      button.textContent = "立即运行一轮模拟扫描";
    }
  });

  $("#purgeButton")?.addEventListener("click", async () => {
    const result = await json("/api/purge", { method: "POST" });
    alert(`已清理 ${result.samples} 个样本、${result.events} 个事件`);
  });

  $("#clearButton")?.addEventListener("click", async () => {
    const confirmation = $("#clearPhrase").value;
    const result = await json("/api/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation }),
    });
    alert(`已清空 ${result.samples} 个样本、${result.events} 个事件`);
  });
});

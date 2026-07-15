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

function relativeSpan(seconds) {
  const value = Number(seconds || 0);
  if (value < 60) return value ? `${value} 秒` : "单次出现";
  if (value < 3600) return `${Math.round(value / 60)} 分钟`;
  return `${(value / 3600).toFixed(1)} 小时`;
}

function shortId(deviceId) {
  return String(deviceId || "未知").replace("dev_", "#").slice(0, 9);
}

function confidenceClass(confidence) {
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.5) return "medium";
  return "low";
}

function formatRate(rate) {
  if (rate == null) return "无流量数据";
  if (rate >= 1_000_000) return `${(rate / 1_000_000).toFixed(1)} Mbps`;
  if (rate >= 1_000) return `${(rate / 1_000).toFixed(0)} Kbps`;
  return `${rate} bps`;
}

function scanIssue(status, hasSample = false) {
  if (!status) return hasSample ? "已有设备样本" : "尚未运行扫描";
  const labels = {
    wifi_profile_missing: "电脑未保存该房间 Wi‑Fi",
    ssid_not_visible: "当前位置看不到该房间 Wi‑Fi",
    wifi_connect_failed: "Wi‑Fi 连接失败",
    wrong_ssid: "连接到了错误的 Wi‑Fi",
    wrong_bssid: "BSSID 与授权配置不一致",
    dhcp_timeout: "未获得本机网络地址",
    router_unreachable: "默认网关不符合现场条件",
    TimeoutError: "本轮扫描超时",
  };
  return status.ok ? "本轮采样成功" : (labels[status.error_code] || "本轮采样失败");
}

function deviceRow(device, compact = false) {
  const confidence = Number(device.type_confidence || 0);
  const confidenceText = `${Math.round(confidence * 100)}%`;
  return `<div class="device-row ${compact ? "compact" : ""}">
    <span class="presence ${device.currently_visible ? "online" : "offline"}" aria-label="${device.currently_visible ? "本轮可见" : "本轮未见"}"></span>
    <code>${esc(shortId(device.device_id))}</code>
    <div class="device-type"><strong>${esc(device.probable_type)}</strong><span class="confidence ${confidenceClass(confidence)}">${confidenceText}</span></div>
    <span class="activity ${device.activity_label.includes("活跃") ? "active" : ""}">${esc(device.activity_label)}</span>
  </div>`;
}

function roomCard(room) {
  const devices = (room.devices || []).filter((device) => !device.is_monitor_pc);
  const current = devices.filter((device) => device.currently_visible);
  const active = current.filter((device) => device.activity_label.includes("活跃"));
  const televisions = devices.filter((device) => device.probable_type.includes("电视"));
  const sampled = Boolean(room.captured_at);
  const preview = devices.slice(0, 3).map((device) => deviceRow(device, true)).join("");
  const remainder = devices.length > 3 ? `<p class="more-devices">另有 ${devices.length - 3} 台历史设备</p>` : "";
  const empty = `<div class="room-empty"><b>${esc(scanIssue(room.scan_status, sampled))}</b><span>运行扫描后，这里会按匿名设备逐条展示。</span></div>`;
  return `<article class="room-card ${sampled ? "sampled" : "unsampled"}">
    <header class="room-card-head"><div><span class="room-label">ROOM</span><h3>${esc(room.room_id)}</h3></div><span class="status ${sampled ? "ok" : "pending"}">${sampled ? "已采样" : "未采样"}</span></header>
    <div class="room-stats"><span><strong>${current.length}</strong> 本轮可见</span><span><strong>${active.length}</strong> 联网活跃</span><span><strong>${televisions.length}</strong> 电视候选</span></div>
    <div class="device-preview">${preview || empty}${remainder}</div>
    <footer class="room-card-foot"><span>${sampled ? `更新 ${time(room.captured_at)}` : esc(scanIssue(room.scan_status, sampled))}</span><a href="/rooms/${esc(room.room_id)}">查看完整台账 →</a></footer>
  </article>`;
}

async function loadDashboard() {
  if (!$("#roomGrid")) return;
  const [health, rooms] = await Promise.all([json("/api/health"), json("/api/rooms")]);
  $("#running").textContent = health.running ? "运行中" : "待命";
  $("#currentRoom").textContent = health.current_room || "—";
  $("#progress").textContent = `${health.rooms_completed} / ${health.room_count}`;
  $("#pending").textContent = health.pending_events;
  $("#faults").textContent = health.system_faults;
  $("#lastUpdated").textContent = `界面更新 ${time(health.server_time)}`;
  $("#roomGrid").innerHTML = rooms.map(roomCard).join("");
}

function deviceDetail(device, roomId) {
  const confidence = Number(device.type_confidence || 0);
  const hitRate = `${device.observed_samples} / ${device.total_room_samples} 次样本`;
  const options = ["海信电视", "手机", "平板", "个人电脑", "酒店固定设备", "允许设备", "未知设备"]
    .map((label) => `<option value="${label}" ${device.manual_label === label ? "selected" : ""}>${label}</option>`)
    .join("");
  const placeholder = device.manual_label ? "" : '<option value="" selected disabled>选择人工类型</option>';
  return `<article class="device-card">
    <header><div class="device-title"><span class="presence ${device.currently_visible ? "online" : "offline"}"></span><div><code>${esc(shortId(device.device_id))}</code><small>${device.currently_visible ? "最新样本可见" : "最新样本未见"}</small></div></div><span class="source-tag">${esc(device.type_source)}</span></header>
    <div class="device-verdict"><div><span>大概率类型</span><strong>${esc(device.probable_type)}</strong></div><b class="confidence-ring ${confidenceClass(confidence)}" style="--confidence:${Math.round(confidence * 100)}">${Math.round(confidence * 100)}<small>%</small></b></div>
    <p class="reason">${esc(device.type_reason)}</p>
    <dl class="device-facts"><div><dt>使用情况</dt><dd>${esc(device.activity_label)} · ${Math.round(Number(device.activity_confidence) * 100)}% 证据强度</dd></div><div><dt>网络速率</dt><dd>${formatRate(device.activity_rate_bps)}</dd></div><div><dt>采样命中</dt><dd>${hitRate}</dd></div><div><dt>可见跨度</dt><dd>${relativeSpan(device.visible_span_seconds)}</dd></div><div><dt>首次出现</dt><dd>${time(device.first_seen)}</dd></div><div><dt>最近出现</dt><dd>${time(device.last_seen)}</dd></div></dl>
    <p class="activity-reason">${esc(device.activity_reason)}</p>
    <div class="classify-control"><label>人工修正类型<select data-device-label="${esc(device.device_id)}">${placeholder}${options}</select></label><button class="tertiary save-label" data-room="${esc(roomId)}" data-device="${esc(device.device_id)}">保存</button></div>
  </article>`;
}

async function loadRoom() {
  const root = $("#roomDetail");
  if (!root) return;
  try {
    const detail = await json(`/api/rooms/${root.dataset.room}`);
    const devices = (detail.devices || []).filter((device) => !device.is_monitor_pc);
    const current = devices.filter((device) => device.currently_visible).length;
    const active = devices.filter((device) => device.currently_visible && device.activity_label.includes("活跃")).length;
    const tv = devices.filter((device) => device.probable_type.includes("电视")).length;
    root.innerHTML = `<section class="room-summary">
      <article><span>历史设备</span><strong>${devices.length}</strong></article><article><span>本轮可见</span><strong>${current}</strong></article><article><span>联网活跃</span><strong>${active}</strong></article><article><span>电视候选</span><strong>${tv}</strong></article><article class="summary-wide"><span>最新样本</span><strong>${time(detail.captured_at)}</strong><small>${esc(detail.raw_source)} · ${esc(scanIssue(detail.scan_status, Boolean(detail.captured_at)))}</small></article>
    </section>
    <section class="section-heading inventory-heading"><div><p class="eyebrow">ANONYMOUS DEVICES</p><h2>设备画像</h2></div><span id="labelStatus">类型概率不代表人员身份</span></section>
    <section class="device-grid">${devices.map((device) => deviceDetail(device, detail.room_id)).join("") || "<div class=\"room-empty large\"><b>这一房间尚未发现设备</b><span>本机发现可能受到客户端隔离、设备待机或轮询时机影响。</span></div>"}</section>
    <aside class="evidence-panel"><div><p class="eyebrow">EVIDENCE BOUNDARY</p><h2>这一页能说明什么</h2></div><ul><li>“联网活跃”只根据逐设备速率元数据；本机模式没有该数据时会明确显示使用未知。</li><li>媒体服务广播可提高电视/媒体设备概率，但不能证明亮屏、播放或有人观看。</li><li>手机和平板经常使用随机 MAC；没有可解释标识时，系统不会强行二选一。</li></ul></aside>
    <section class="panel events-compact"><h2>最近事件</h2>${detail.events.slice(0, 8).map((event) => `<p><span>${esc(event.event_type)}</span><b>${Math.round(event.confidence * 100)}%</b><small>${time(event.last_seen || event.occurred_at)} · ${esc(event.review_status || "待复核")}</small></p>`).join("") || "<p>暂无事件</p>"}</section>`;
  } catch (_error) {
    root.innerHTML = `<div class="room-empty large"><b>该房间尚无设备样本</b><span>返回总览运行一轮扫描；如果 Wi‑Fi 配置缺失，总览会显示具体原因。</span><a class="secondary" href="/">返回总览</a></div>`;
  }
}

async function saveDeviceLabel(button) {
  const select = document.querySelector(`[data-device-label="${button.dataset.device}"]`);
  const status = $("#labelStatus");
  if (!select.value) {
    status.textContent = "请先选择一种人工类型";
    return;
  }
  button.disabled = true;
  try {
    await json("/api/allowlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room_id: button.dataset.room, device_id: button.dataset.device, label: select.value, note: "" }),
    });
    status.textContent = "人工类型已保存";
    await loadRoom();
  } catch (_error) {
    status.textContent = "保存失败，请稍后重试";
  } finally {
    button.disabled = false;
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
  if ($("#roomGrid")) dashboardPoll = window.setInterval(() => loadDashboard().catch(console.error), 3000);
  window.addEventListener("pagehide", () => { if (dashboardPoll !== null) window.clearInterval(dashboardPoll); });
  document.addEventListener("click", (event) => {
    const button = event.target.closest(".save-label");
    if (button) saveDeviceLabel(button);
  });
  $("#scanButton")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "正在顺序扫描已配置房间…";
    try { await json("/api/scan-cycle", { method: "POST" }); }
    finally { await loadDashboard(); button.disabled = false; button.textContent = button.dataset.idleLabel; }
  });
  $("#purgeButton")?.addEventListener("click", async () => {
    const result = await json("/api/purge", { method: "POST" });
    $("#purgeButton").textContent = `已清理 ${result.samples} 个样本`;
  });
  $("#clearButton")?.addEventListener("click", async () => {
    const result = await json("/api/clear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmation: $("#clearPhrase").value }) });
    $("#clearButton").textContent = `已清空 ${result.samples} 个样本`;
  });
});

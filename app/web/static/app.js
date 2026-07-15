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

function reportedRow(device, compact = false) {
  const connected = ["已连接（使用未知）", "使用中", "待机"].includes(device.usage_state);
  return `<div class="reported-row ${compact ? "compact" : ""}">
    <span class="presence ${connected ? "online" : "offline"}"></span>
    <strong>${esc(device.label)}</strong>
    <span>${esc(device.device_type)}</span>
    <b>${esc(device.usage_state)}</b>
  </div>`;
}

function roomCard(room) {
  const devices = (room.devices || []).filter((device) => !device.is_monitor_pc);
  const reported = room.reported_devices || [];
  const current = devices.filter((device) => device.currently_visible);
  const connected = reported.filter((device) => ["已连接（使用未知）", "使用中", "待机"].includes(device.usage_state));
  const sampled = Boolean(room.captured_at);
  const reportedPreview = reported.slice(0, 4).map((device) => reportedRow(device, true)).join("");
  const signalPreview = devices.slice(0, 2).map((device) => deviceRow(device, true)).join("");
  const reportedEmpty = `<div class="room-empty"><b>尚无现场确认台账</b><span>进入房间后可录入已知设备与真实状态。</span></div>`;
  const signalEmpty = `<div class="room-empty"><b>${esc(scanIssue(room.scan_status, sampled))}</b><span>电脑端没有看到可识别的网络信号。</span></div>`;
  return `<article class="room-card ${sampled ? "sampled" : "unsampled"}">
    <header class="room-card-head"><div><span class="room-label">ROOM</span><h3>${esc(room.room_id)}</h3></div><span class="status ${sampled ? "ok" : "pending"}">${sampled ? "已采样" : "未采样"}</span></header>
    <div class="room-stats"><span><strong>${reported.length}</strong> 现场确认</span><span><strong>${connected.length}</strong> 已连接/待机</span><span><strong>${current.length}</strong> 电脑可见信号</span></div>
    <div class="inventory-block"><small>现场确认 · 可作为真实台账</small><div class="device-preview">${reportedPreview || reportedEmpty}</div></div>
    <div class="inventory-block signal-block"><small>自动发现 · 覆盖不完整</small><div class="device-preview">${signalPreview || signalEmpty}</div></div>
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
    <div class="device-verdict"><div><span>信号可能来源</span><strong>${esc(device.probable_type)}</strong></div><b class="confidence-ring ${confidenceClass(confidence)}" style="--confidence:${Math.round(confidence * 100)}">${Math.round(confidence * 100)}<small>%</small></b></div>
    <p class="reason">${esc(device.type_reason)}</p>
    <dl class="device-facts"><div><dt>使用情况</dt><dd>${esc(device.activity_label)} · ${Math.round(Number(device.activity_confidence) * 100)}% 证据强度</dd></div><div><dt>网络速率</dt><dd>${formatRate(device.activity_rate_bps)}</dd></div><div><dt>采样命中</dt><dd>${hitRate}</dd></div><div><dt>可见跨度</dt><dd>${relativeSpan(device.visible_span_seconds)}</dd></div><div><dt>首次出现</dt><dd>${time(device.first_seen)}</dd></div><div><dt>最近出现</dt><dd>${time(device.last_seen)}</dd></div></dl>
    <p class="activity-reason">${esc(device.activity_reason)}</p>
    <div class="classify-control"><label>人工修正类型<select data-device-label="${esc(device.device_id)}">${placeholder}${options}</select></label><button class="tertiary save-label" data-room="${esc(roomId)}" data-device="${esc(device.device_id)}">保存</button></div>
  </article>`;
}

function reportedDeviceCard(device, roomId) {
  const types = ["手机", "平板", "个人电脑", "电视", "其他"];
  const states = ["已连接（使用未知）", "使用中", "待机", "关闭", "离线", "未知"];
  const typeOptions = types.map((value) => `<option ${device.device_type === value ? "selected" : ""}>${value}</option>`).join("");
  const stateOptions = states.map((value) => `<option ${device.usage_state === value ? "selected" : ""}>${value}</option>`).join("");
  return `<article class="reported-card" data-reported-id="${device.id}">
    <header><div><span class="source-tag confirmed">现场确认</span><strong>${esc(device.label)}</strong></div><small>更新 ${time(device.updated_at)}</small></header>
    <div class="reported-form-grid">
      <label>设备名称<input data-field="label" value="${esc(device.label)}" maxlength="80"></label>
      <label>设备类型<select data-field="device_type">${typeOptions}</select></label>
      <label>当前状态<select data-field="usage_state">${stateOptions}</select></label>
      <label>说明<input data-field="note" value="${esc(device.note || "")}" maxlength="500" placeholder="不记录人员身份"></label>
    </div>
    <footer><button class="tertiary save-reported" data-room="${esc(roomId)}">保存状态</button><button class="text-button delete-reported">删除</button></footer>
  </article>`;
}

function addReportedForm(roomId) {
  return `<article class="reported-card add-card" id="addReportedForm">
    <header><div><span class="source-tag confirmed">新增</span><strong>录入现场确认设备</strong></div><small>人工事实与自动信号分开保存</small></header>
    <div class="reported-form-grid">
      <label>设备名称<input data-field="label" maxlength="80" placeholder="例如：电脑 1"></label>
      <label>设备类型<select data-field="device_type"><option>个人电脑</option><option>手机</option><option>平板</option><option>电视</option><option>其他</option></select></label>
      <label>当前状态<select data-field="usage_state"><option>已连接（使用未知）</option><option>使用中</option><option>待机</option><option>关闭</option><option>离线</option><option>未知</option></select></label>
      <label>说明<input data-field="note" maxlength="500" placeholder="可留空"></label>
    </div>
    <footer><button class="primary add-reported" data-room="${esc(roomId)}">加入台账</button><span id="reportedStatus"></span></footer>
  </article>`;
}

async function loadRoom() {
  const root = $("#roomDetail");
  if (!root) return;
  try {
    const detail = await json(`/api/rooms/${root.dataset.room}`);
    const devices = (detail.devices || []).filter((device) => !device.is_monitor_pc);
    const reported = detail.reported_devices || [];
    const current = devices.filter((device) => device.currently_visible).length;
    const connected = reported.filter((device) => ["已连接（使用未知）", "使用中", "待机"].includes(device.usage_state)).length;
    const inUse = reported.filter((device) => device.usage_state === "使用中").length;
    root.innerHTML = `<section class="room-summary">
      <article><span>现场确认设备</span><strong>${reported.length}</strong></article><article><span>已连接/待机</span><strong>${connected}</strong></article><article><span>确认使用中</span><strong>${inUse}</strong></article><article><span>电脑可见信号</span><strong>${current}</strong></article><article class="summary-wide"><span>最新自动样本</span><strong>${time(detail.captured_at)}</strong><small>${esc(detail.raw_source)} · ${esc(scanIssue(detail.scan_status, Boolean(detail.captured_at)))}</small></article>
    </section>
    <section class="section-heading inventory-heading"><div><p class="eyebrow">CONFIRMED INVENTORY</p><h2>现场确认设备</h2></div><span>这里记录人工确认的类型与状态</span></section>
    <section class="reported-grid">${reported.map((device) => reportedDeviceCard(device, detail.room_id)).join("")}${addReportedForm(detail.room_id)}</section>
    <section class="section-heading inventory-heading signal-heading"><div><p class="eyebrow">PC-VISIBLE SIGNALS</p><h2>电脑可见信号</h2></div><span id="labelStatus">不能代表完整 Wi‑Fi 客户端列表</span></section>
    <section class="device-grid">${devices.map((device) => deviceDetail(device, detail.room_id)).join("") || "<div class=\"room-empty large\"><b>这一房间尚未发现网络信号</b><span>这不等于房间没有设备；客户端隔离、防火墙或手机休眠都可能导致漏检。</span></div>"}</section>
    <aside class="evidence-panel"><div><p class="eyebrow">EVIDENCE BOUNDARY</p><h2>两类信息不要混用</h2></div><ul><li>“现场确认设备”来自人工核对，可记录已连接、关闭或使用中；不会自动绑定人员身份。</li><li>“电脑可见信号”只代表这台电脑收到过响应，可能严重漏掉已连 Wi‑Fi 的电脑和手机。</li><li>MediaRenderer 可能来自待机电视、机顶盒或电脑媒体服务，不能证明电视开机、亮屏或播放。</li></ul></aside>
    <section class="panel events-compact"><h2>最近事件</h2>${detail.events.slice(0, 8).map((event) => `<p><span>${esc(event.event_type)}</span><b>${Math.round(event.confidence * 100)}%</b><small>${time(event.last_seen || event.occurred_at)} · ${esc(event.review_status || "待复核")}</small></p>`).join("") || "<p>暂无事件</p>"}</section>`;
  } catch (_error) {
    root.innerHTML = `<div class="room-empty large"><b>房间数据载入失败</b><span>请返回总览后重试。</span><a class="secondary" href="/">返回总览</a></div>`;
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

function reportedPayload(card, roomId) {
  const value = (field) => card.querySelector(`[data-field="${field}"]`).value.trim();
  return {
    room_id: roomId,
    label: value("label"),
    device_type: value("device_type"),
    usage_state: value("usage_state"),
    note: value("note"),
  };
}

async function addReportedDevice(button) {
  const card = button.closest(".reported-card");
  const payload = reportedPayload(card, button.dataset.room);
  const status = $("#reportedStatus");
  if (!payload.label) {
    status.textContent = "请填写设备名称";
    return;
  }
  button.disabled = true;
  try {
    await json("/api/reported-devices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadRoom();
  } catch (_error) {
    status.textContent = "保存失败";
    button.disabled = false;
  }
}

async function saveReportedDevice(button) {
  const card = button.closest(".reported-card");
  const payload = reportedPayload(card, button.dataset.room);
  button.disabled = true;
  try {
    await json(`/api/reported-devices/${card.dataset.reportedId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadRoom();
  } finally {
    button.disabled = false;
  }
}

async function deleteReportedDevice(button) {
  const card = button.closest(".reported-card");
  button.disabled = true;
  try {
    await json(`/api/reported-devices/${card.dataset.reportedId}`, { method: "DELETE" });
    await loadRoom();
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
    const addReported = event.target.closest(".add-reported");
    if (addReported) addReportedDevice(addReported);
    const saveReported = event.target.closest(".save-reported");
    if (saveReported) saveReportedDevice(saveReported);
    const deleteReported = event.target.closest(".delete-reported");
    if (deleteReported) deleteReportedDevice(deleteReported);
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

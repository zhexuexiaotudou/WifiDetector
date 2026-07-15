# 2312 电脑本地发现实机验收（2026-07-15）

## 授权范围与环境

- 使用当前 Windows 11 电脑和用户明确授权的 2312 房间网络与电视。
- Windows 已连接 `CMCC-2312`，已保存 profile 存在；本地 IPv4 与默认网关满足 Gate A。
- 没有企业网关管理权限，因此验收不登录网关、不读取客户端全表或逐设备流量。

## 电脑本地发现结果

- `probe --room 2312`：仅 `local_neighbor_discovery` 与 `ssdp_discovery` 为 `true`；路由器客户端、流量、IPTV、HDMI、CEC、API 和登录自动化能力均为 `false`。
- 多轮 `scan-once --room 2312`：每轮发现 2–3 个匿名本机可见设备，其中持续存在 1 个 `ssdp-media-device`。
- SSDP 只读诊断收到 6 条响应，其中 2 条为媒体服务，类型为 `MediaRenderer` 和 `AVTransport`；没有获取设备描述正文。
- `media_device_visible` 事件按匿名设备去重，重复出现只增加 `occurrence_count`，没有每轮生成新事件。

## 隐私与误判检查

- SQLite 样本只包含 `dev_<HMAC>`、证据类别和能力标志；客户端 IP、完整 MAC、USN、LOCATION URL、主机名和逐设备流量均为空或未持久化。
- 事件置信度为 0.62，明确表述为“媒体设备可见”；没有据此判断电视品牌、亮屏、播放、HDMI 输入或观看人员。
- 本轮只执行单次 `/24` ICMP、ARP 关联和标准 SSDP M-SEARCH；没有端口扫描、域名记录或数据包正文采集。

## UI 与服务

- Ruff、严格 MyPy、JavaScript 语法检查和 29 项 Pytest 全部通过；仅有 1 条上游 TestClient 弃用提示。
- wheel 重新构建成功：`dorm_monitor-0.1.0-py3-none-any.whl`，SHA-256 为 `eb10e9162850b768ada40e51f0e981ba9839b3dc4e95986e591d0dce080a36d5`。
- `app.cli run` 修复后可启动 Uvicorn，实际监听 `127.0.0.1:8765`。
- 首页显示 1 个已配置房间、`field` 模式、本机发现按钮和动态 `1 / 1` 进度。
- 浏览器触发一轮本机发现耗时约 8.3 秒，完成后显示媒体设备广播证据；房间详情只显示匿名 ID 与能力边界。
- Playwright headed 验收控制台为 0 错误、0 警告。

## 硬边界

AP 客户端隔离、设备不响应 ICMP/SSDP、深度待机或有线隔离都可能导致漏检。该结果不是正式八房间验收，也不能替代网关级客户端与电视业务证据。

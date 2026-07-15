# 故障排查

- `wifi_profile_missing`：先在 Windows 设置中手动连接该 SSID 并保存，不要向程序提供 Wi‑Fi 密码。
- `ssid_not_visible`：确认电脑在对应房间覆盖范围，并刷新 Windows Wi‑Fi 列表。
- `wrong_ssid` / `wrong_bssid`：立即停止该房间采集，核对配置和现场网络，避免访问同名网络。
- `dhcp_timeout`：检查 Windows 是否取得 IPv4；不要手工猜测静态地址。
- `router_unreachable`：确认默认网关为 `192.168.1.1`，且管理方授权访问。
- Edge 启动失败：确认 Microsoft Edge 已安装并安装 `.[discovery]` 可选依赖。
- 页面结构变化：停用真实适配器，重新执行发现并人工审查脱敏证据，不要临时猜选择器。

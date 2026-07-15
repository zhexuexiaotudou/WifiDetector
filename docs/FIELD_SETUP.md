# 现场部署清单

1. 取得网络和网关管理方的明确书面授权，确认只读查询范围。
2. 在目标 Windows 10/11 电脑上逐个手动连接八个房间 SSID，选择自动连接，让 Windows 保存 profile。不要把 Wi‑Fi 密码写入项目。
3. 运行 `scripts/setup_windows.ps1`，再运行 `py -m app.cli doctor`。
4. 逐个执行 `connect-test`，确认 SSID、可选 BSSID、本地 IPv4 和默认网关。
5. 对每个房间运行可见 Edge 发现；人工登录并浏览客户端与电视业务页。
6. 只提交 `artifacts/sanitized_discovery/` 中生成的元数据证据。原始 HAR、截图、浏览器目录、Cookie 和现场数据库保持在忽略目录中。
7. 完成客户端、电视、IPTV 字段和刷新周期验证后再实现真实适配器。
8. 分别采集全部空闲、电视待机、智能电视应用播放和 HDMI/IPTV 播放，每种 5–10 分钟。阈值只能来自现场基线。

现场验收不能在当前开发电脑上代替完成，因为目标 SSID 与网关不在当前连接环境中。

# 现场部署清单

1. 取得网络和网关管理方的明确书面授权，确认只读查询范围。
2. 在目标 Windows 10/11 电脑上逐个手动连接八个房间 SSID，选择自动连接，让 Windows 保存 profile。不要把 Wi‑Fi 密码写入项目。
3. 运行 `scripts/setup_windows.ps1`，再运行 `py -m app.cli doctor`。
4. 逐个执行 `connect-test`，确认 SSID、可选 BSSID、本地 IPv4 和默认网关。
5. 对每个房间运行可见 Edge 发现；人工登录并浏览客户端与电视业务页。
6. 只提交 `artifacts/sanitized_discovery/` 中生成的元数据证据。原始 HAR、截图、浏览器目录、Cookie 和现场数据库保持在忽略目录中。
7. 完成客户端、电视、IPTV 字段和刷新周期验证后再实现真实适配器。
8. 分别采集全部空闲、电视待机、智能电视应用播放和 HDMI/IPTV 播放，每种 5–10 分钟。阈值只能来自现场基线。

正式八房间验收不能在当前开发电脑上代替完成，因为八个目标 SSID 与网关不在当前连接环境中。当前电脑上的 2312 授权环境只能执行下述单房间现场测试。

## 2312 单房间现场测试

经管理方授权后，可用 `2312` 房间作为单房间现场证据环境。该模式不需要进入企业网关，只验证 Gate A，并从电脑执行最小化的 ICMP/ARP 邻居发现与 SSDP/UPnP 媒体服务发现；不代表正式八房间全部通过。

```powershell
$env:DORM_MONITOR_CONFIG = "config/rooms.2312.field.yaml"
.\.venv\Scripts\python.exe -m app.cli doctor
.\.venv\Scripts\python.exe -m app.cli connect-test --room 2312
.\.venv\Scripts\python.exe -m app.cli probe --room 2312
.\.venv\Scripts\python.exe -m app.cli scan-once --room 2312
```

该配置使用已保存的 `CMCC-2312` Windows profile，不含 Wi-Fi 或路由器密码。`mock_mode` 为 `false`，数据源为 `local_pc`，不会回退到 Mock 或尝试网关登录。每轮最多向当前 `/24` 内各地址发送一次 ICMP，并发送标准 SSDP M-SEARCH；不扫描 TCP/UDP 端口，不读取响应正文，不记录域名或完整 IP/MAC。

电脑本地模式只能报告“设备或媒体服务在本轮可见”。若 AP 启用了客户端隔离、电视不响应 ICMP/SSDP、电视处于深度待机或使用有线隔离网络，就可能完全看不到。即使看到了媒体设备，也不能据此判断电视亮屏、HDMI 输入、正在播放或观看人员。

# 宿舍夜间电子产品监测系统（单电脑版）

这是一个仅供**已明确授权网络**使用的 Windows 本地只读监测 MVP。它用一块 Wi‑Fi 网卡按顺序轮询 2301、2302、2303、2305、2306、2307、2309、2310 八个独立 SSID，把网关公开的最小元数据写入本机 SQLite，并提供人工复核面板。

系统不会破解密码、绕过验证码、监听数据包正文、记录访问域名、实施中间人攻击或自动认定队员违规。普通页面与持久化数据都不保存完整 MAC；设备标识使用本机随机密钥执行 HMAC-SHA256 后生成。

## 当前可运行能力

- 完整 Mock 闭环：8 房间顺序扫描、匿名设备、事件、SQLite/WAL、日报和暗色面板。
- Windows `netsh wlan` profile、可见 SSID、连接状态、IPv4 与默认网关检查。
- 同地址网关隔离：设计为单任务顺序访问，每房间采用短生命周期适配器。
- H10e-31 证据门禁：没有真实脱敏页面/API 证据时，所有能力默认 `false`，绝不猜接口或 DOM 选择器。
- 可见 Edge 发现流程只保存脱敏后的页面文字摘录和 XHR/fetch 元数据，不保存响应正文、Cookie、原始 HAR 或截图。
- 未知设备、智能电视联网、IPTV 明确状态与接口计数的透明规则事件。
- 默认 72 小时保留、手动清理与确认短语保护的一键清空。
- 分层房间设备台账：现场确认设备记录已知类型与“已连接（使用未知）/使用中/待机/关闭/离线”状态；电脑可见信号单独展示，绝不冒充完整 Wi-Fi 客户端表。
- 可解释信号画像：只根据人工标签、脱敏后的设备名称类别、SSDP 媒体服务或邻居证据提示可能来源；MediaRenderer 仅标为 60% 的“媒体服务端点”，可能来自待机电视、机顶盒或电脑。

## 安装与启动

在 Windows PowerShell 中：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
.\scripts\run_monitor.bat
```

浏览器会打开 <http://127.0.0.1:8765>。首次演示可运行：

```powershell
.\.venv\Scripts\python.exe -m app.cli scan-cycle
.\.venv\Scripts\python.exe -m app.cli run
```

## 现场前检查

确保已获得学校、领队、酒店或设备管理方的明确授权，并手动连接每个 Wi‑Fi 一次，让 Windows 安全保存 profile。不要把密码写入 YAML 或 Git。

```powershell
.\.venv\Scripts\python.exe -m app.cli doctor
.\.venv\Scripts\python.exe -m app.cli connect-test --room 2301
.\.venv\Scripts\python.exe -m app.cli discover --room 2301
```

真实凭据只能通过 Windows 已保存 Wi‑Fi profile、本机 `.env`、Credential Manager 或运行时交互输入提供。详见 [现场部署](docs/FIELD_SETUP.md) 与 [路由器发现](docs/ROUTER_DISCOVERY.md)。

已授权的 `2312` 单房间现场测试使用 `config/rooms.2312.field.yaml`。它不需要路由器管理账号，只从当前电脑执行单次 ICMP/ARP 邻居发现和 SSDP/UPnP 媒体设备发现；不读取客户端全表、逐设备流量或电视亮屏状态。它不改变正式八房间目标，也不代表八房间全部验收。

正式八房间若也没有网关账号，可复制 `config/rooms.pc-local.example.yaml`。程序会用 Windows 已保存的 profile 顺序连接每个房间，再进行本机发现。未保存 profile、当前看不到 SSID 或尚未采样的房间会在总览中显示具体缺口，不会生成模拟设备。

## 能力边界

能较可靠发现的是授权网关所列的新客户端、持续在线及可用的客户端流量，以及网关明确提供的 IPTV/STB/HDMI 业务字段。无法可靠发现 4G/5G 但未连接房间 Wi‑Fi 的设备、完全离线使用、无网络流量的本地视频、短于完整轮询周期的瞬时连接，或没有网关证据的 HDMI 亮屏状态。

“电视在线”不等于“电视开机”，“联网活跃”不等于“某人在观看”。所有结果仅供人工复核。

普通 ARP/ICMP 邻居缺少可解释设备服务时，手机、平板和电脑通常无法可靠区分。此时页面只显示低置信度“手机/平板/电脑候选”，允许操作员用通用设备类型人工校正，但不记录人员姓名。

房间详情允许单独维护“现场确认设备”台账。该台账适合记录操作员已经核对的通用名称、类型与状态，不应填写人员姓名；自动发现结果始终保留在“电脑可见信号”区域，两者不会自动关联或相互覆盖。

## 开发检查

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe app
.\.venv\Scripts\pytest.exe -q
```

当前阶段与现场阻塞见 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) 和 [NEEDS_GPT_REVIEW.md](NEEDS_GPT_REVIEW.md)。

进一步资料：

- [架构、API 与数据模型](docs/ARCHITECTURE.md)
- [命令、环境变量与运维](docs/OPERATOR_GUIDE.md)
- [隐私、安全与能力边界](docs/PRIVACY_AND_LIMITATIONS.md)

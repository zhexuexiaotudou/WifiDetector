# 需要现场证据后继续评估

## 当前阶段

离线项目已推进到 Mock 闭环、Windows Wi‑Fi 调度框架和 H10e-31 安全发现工具。真实 H10e-31 客户端/IPTV 适配器尚未实现，因为当前环境不满足真实 Gate A，且没有授权现场的脱敏页面/API 证据。

## 已运行命令与结果

- `scripts/setup_windows.ps1`：依赖安装成功；失败退出码保护已验证。
- `ruff check .`：通过。
- `mypy app`：严格模式通过，42 个源码文件无问题。
- `pytest -q`：36 项通过；仅有上游 TestClient 弃用提示。
- `py -m app.cli doctor`：配置、数据库、本机监听、Edge、Wi‑Fi 与 Playwright 可用；8 个目标 profile 全缺。
- `connect-test --room 2301`：安全返回 `wifi_profile_missing`，没有尝试密码或切换网络。
- `probe --room 2301`：17 项 H10e-31 能力全部为 `false`。
- `scan-cycle`：8 个房间全部完成，耗时 16.182 秒。
- `soak --cycles 300`：2400 样本、4 个有界开放事件、SQLite 完整，热身后净增长 5534 字节。
- 本地 HTTP：`/`、`/api/health`、`POST /api/scan-cycle`、`/api/rooms` 均返回 200，8 房间可达。
- Playwright 浏览器视觉检查：通过；扫描中实时显示当前房间和进度，结束恢复待命，事件页与房间详情页正常，控制台 0 错误/0 警告。
- 房间设备台账检查：Ruff、严格 MyPy、36 项 Pytest 和 JavaScript 语法检查通过；八房间总览与 2307 详情在 Edge 中完成视觉验收，人工类型修正可立即覆盖规则推断。

## 精确阻塞

- 当前 Windows 没有保存 2301、2302、2303、2305、2306、2307、2309、2310 profile。
- 当前连接不是任一目标房间 SSID，因此不能验证 `192.168.1.1` 是否为对应 H10e-31。
- 没有 H10e-31 的脱敏页面文字、XHR/fetch 元数据或能力证据，不能安全定义 API 地址、选择器或登录自动化。

## 用户现场最少操作

1. 获得管理方明确授权。
2. 在目标电脑逐个手动连接八个 SSID，并让 Windows 保存 profile。
3. 运行 `py -m app.cli doctor` 和 `connect-test --room 2301`。
4. 运行 `discover --room 2301`，人工登录并浏览客户端/IPTV 页面。
5. 提供 `artifacts/sanitized_discovery/` 中的 JSON；不要提供密码、Cookie、Token、完整 MAC、截图或原始 HAR。

## 推荐方案

优先根据脱敏证据实现 JSON API 适配器；只有页面没有稳定 API 时才使用 DOM 抓取。若登录含验证码，保留人工会话，不绕过。若网关没有 IPTV/HDMI 证据，UI 必须保持“能力不可用”，不能推定电视亮屏。

## 2312 无网关权限降级结果

2026-07-15 已在用户授权的 2312 网络完成电脑本地模式实测。Gate A 通过，多轮 ICMP/ARP + SSDP 发现持续看到一个匿名媒体服务设备，服务类型包含 `MediaRenderer` 与 `AVTransport`。这只证明媒体设备在局域网中可见，不解除真实适配器阻塞，也不证明电视亮屏、播放或有人观看。详细证据见 `artifacts/test_reports/pc_local_field_verification_2026-07-15.md`。

同日合并后的标准服务再次采样，设备画像页面显示 2 个匿名设备：媒体设备在 2/2 样本中稳定出现，显示为“电视/媒体设备”候选（82% 类型证据）和“媒体服务可见，使用未知”（35% 使用证据）；另一个普通邻居只在最新 1/2 样本出现，显示为“手机/平板/电脑候选”（30% 类型证据）和“在线可见，使用未知”（25% 使用证据）。正式八房间总览已经具备代码和演示闭环，但当前电脑没有八个目标 profile，不能将 2312 单房间结果扩展为八房间现场验收。

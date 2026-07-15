# 变更日志

## 0.1.0 - 2026-07-15

- 建立授权只读、隐私优先的 Windows 本地监测项目。
- 完成八房间 Mock 顺序轮询、SQLite/WAL、HMAC 匿名化、事件规则、日报和 FastAPI 面板。
- 完成 Windows Wi‑Fi profile/SSID/BSSID/IP/网关验证框架。
- 完成 H10e-31 元数据-only 可见 Edge 发现工具和真实适配器证据门禁。
- 增加单元、集成、加速 soak 测试与 Windows GitHub Actions CI。
- 持续异常改为刷新开放事件并累计出现次数，消失后自动闭合，避免整夜事件膨胀。
- 修复 PowerShell 安装脚本对外部命令非零退出码不敏感的问题。
- 为 soak 增加 SQLite 完整性、事件上限与 tracemalloc 内存证据。
- 根据 Playwright 实机验收增加本地 favicon、单轮扫描状态复位和首页 1 秒实时短轮询。

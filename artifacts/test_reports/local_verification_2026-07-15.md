# 本地验收报告（2026-07-15）

## 质量门禁

- Ruff：通过，0 个问题。
- MyPy strict：通过，40 个源码文件 0 个问题。
- Pytest：19 passed，1 个上游 TestClient 弃用提示。

## Mock 闭环

- 八个房间均成功顺序采样；一轮耗时 16.182 秒。
- HTML、CSV、JSON 日报均成功生成到被 Git 忽略的 `artifacts/reports/`。
- FastAPI 在 `127.0.0.1:8765` 启动并就绪。
- `/`、`/api/health`、`POST /api/scan-cycle`、`/api/rooms` 均返回 200；房间数为 8。
- Playwright headed 模式视觉验收：首页布局和中文显示正常；扫描中显示当前房间 `2306`、进度 `5/8`；结束恢复待命和 `8/8`。
- 事件页展示 4 个透明规则事件；2305 详情页仅展示匿名设备 ID，并明确 HDMI 亮屏不可判断。
- 浏览器控制台：0 错误、0 警告。

## 加速可靠性

- 轮数：300。
- 样本：2400。
- 持续开放事件：4；没有每轮重复新增。
- SQLite `PRAGMA integrity_check`：`ok`。
- tracemalloc 当前：10986 B；峰值：30781 B；总轮数三分之一热身后增长：5534 B。

## 当前机器现场门禁

- Windows 11、Python 3.14、Edge、Wi‑Fi、Playwright 包、SQLite 与回环端口检查通过。
- 2301/2302/2303/2305/2306/2307/2309/2310 八个 Windows Wi‑Fi profile 全部缺失。
- `connect-test --room 2301` 返回 `wifi_profile_missing`；真实 Gate A 未通过。
- H10e-31 未验证能力全部为 false，没有猜测 API 或选择器。

## 未完成验证

- 尚未进入授权现场，不能完成真实网关登录、客户端发现、电视/IPTV 字段校准或连续 8 小时现场运行。

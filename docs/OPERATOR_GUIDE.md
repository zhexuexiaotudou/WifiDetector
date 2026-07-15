# 操作手册

## 命令速查

命令统一使用 `.\.venv\Scripts\python.exe -m app.cli <command>` 调用。

| 命令 | 用途 |
|---|---|
| `doctor` | 检查 Windows、Python、Edge、Wi‑Fi、八个 profile、数据库、监听地址和端口 |
| `profiles` | 列出 Windows 已保存 profile 名称，不导出密码 |
| `connect-test --room 2301` | 验证单房间 SSID/BSSID、IPv4 与默认网关链路 |
| `discover --room 2301` | Gate A 通过后启动可见 Edge，生成脱敏元数据证据 |
| `probe --room 2301` | 显示当前配置的数据源能力；路由器无证据时全假，`local_pc` 仅开放邻居/SSDP 发现 |
| `calibrate --room 2301` | 显示现场校准场景和最小采样要求 |
| `scan-once --room 2301` | 执行单房间采样 |
| `scan-cycle` | 按配置顺序扫描八个房间 |
| `run` | 启动本地面板 |
| `export --date YYYY-MM-DD` | 生成 HTML、CSV 与 JSON 人工复核日报 |
| `purge --older-than-hours 72` | 按保留策略清理样本与事件 |
| `soak --cycles 300` | 执行加速可靠性测试并输出 SQLite、事件和内存证据 |

## 环境变量与配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DORM_MONITOR_CONFIG` | `config/rooms.example.yaml` | 八房间与调度配置；相对路径按项目根解析 |
| `DORM_MONITOR_DATABASE` | `private_artifacts/dorm_monitor.db` | 本机 SQLite 文件；目录自动创建且被 Git 忽略 |
| `DORM_MONITOR_LOG_LEVEL` | `INFO` | 结构化日志级别 |
| `H10E31_USERNAME`、`H10E31_PASSWORD` | 无 | 预留本机凭据名；不得写入仓库或测试报告 |

复制 `.env.example` 为本机 `.env` 时仍应避免明文凭据；优先使用 Windows Credential Manager 或运行时人工输入。配置中的 `dashboard_host` 只接受回环地址。

## 日常运行与故障处理

先运行 `doctor`，再启动面板。现场模式必须先逐房间通过 `connect-test`，失败原因按 [故障排查](TROUBLESHOOTING.md) 处理。日报输出位于被 Git 忽略的 `artifacts/reports/`；数据库和日志分别位于 `private_artifacts/` 与 `logs/`。

面板中的“高置信度异常”也不是违规结论。事件可标为“已核实”“误报”或“无法确认”，底层审计记录在保留期内不允许从复核页删除。

当 `field_data_source: local_pc` 时，`scan-once`/`scan-cycle` 不访问网关页面。`local_ping_sweep` 默认关闭；2312 授权测试配置显式开启，每轮对 `/24` 中每个地址最多发送一次 ICMP。SSDP 只保存是否存在媒体服务这一脱敏类别，不保存设备描述正文或 LOCATION URL。

# 操作手册

- `doctor`：检查 Windows、Python、Edge、Wi‑Fi、八个 profile、数据库、监听地址和端口。
- `profiles`：列出 Windows 已保存 profile 名称，不导出密码。
- `connect-test --room 2301`：只验证单房间连接链路。
- `scan-cycle`：Mock 模式顺序扫描八个房间。
- `run`：启动本地面板。
- `export --date YYYY-MM-DD`：生成 HTML、CSV 与 JSON 人工复核日报。
- `purge --older-than-hours 72`：按保留策略清理。

面板中的“高置信度异常”也不是违规结论。事件可标为“已核实”“误报”或“无法确认”，底层审计记录在保留期内不允许从复核页删除。

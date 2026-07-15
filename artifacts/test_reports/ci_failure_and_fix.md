# CI 失败与修复记录

- Run：`29395458765`
- 失败步骤：`mypy app`
- 原因：Windows runner 只安装 `.[dev]`，严格 MyPy 无法解析可选发现模块 `playwright.async_api`。
- 修复：CI 安装 `.[dev,discovery]`，保持严格 MyPy，不通过忽略规则掩盖缺失依赖。
- 本地对应环境已安装 discovery extra，Ruff、MyPy 和 19 项 Pytest 均通过。

# 安装失败与修复记录

- 时间：2026-07-15
- 首次失败：并行创建文件期间启动安装，Hatchling 读取 `README.md` 时文件尚未存在，元数据生成失败。
- 同时发现：PowerShell 的 `$ErrorActionPreference = 'Stop'` 不会自动把外部程序非零退出码转换为终止错误，脚本错误地继续打印完成提示。
- 修复：README 已创建；每次 `py`/`pip` 调用后显式检查 `$LASTEXITCODE` 并抛出终止错误。
- 后续验证：重新运行完整安装和质量检查。
- 复验结果：依赖安装成功；Ruff、MyPy strict 和 19 项 Pytest 全部通过。

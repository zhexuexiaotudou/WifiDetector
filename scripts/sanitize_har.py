"""Refuse raw HAR ingestion and explain the safe discovery path.

Raw HAR files can contain credentials, cookies and tokens. The MVP intentionally
does not transform them in-place; use `py -m app.cli discover --room ROOM` to
capture metadata-only evidence instead.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "安全策略：不读取或保存原始 HAR。请运行 "
        "`py -m app.cli discover --room 2301` 生成仅含请求元数据的脱敏证据。"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

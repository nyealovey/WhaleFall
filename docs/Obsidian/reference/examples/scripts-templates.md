---
title: Scripts 模板(长示例)
aliases:
  - scripts-templates
tags:
  - reference
  - reference/examples
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: `standards/scripts-standards` 引用的脚本模板集合(非规则 SSOT)
related:
  - "[[reference/examples/README]]"
  - "[[standards/core/guide/scripts]]"
  - "[[standards/doc/guide/document-boundary]]"
---

# Scripts 模板(长示例)

> [!important] 说明
> 本文仅用于承载可复制的脚本模板, 便于 standards 引用与收敛. 规则 SSOT 以 `docs/Obsidian/standards/**` 为准.

## Shell 脚本模板

```bash
#!/usr/bin/env bash
# 脚本简要说明(一行)
#
# 用法: ./scripts/xxx/script_name.sh [选项]
#
# 选项:
#   --option1    选项说明
#   --help       显示帮助信息

set -euo pipefail

# ============================================================
# 常量定义
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# 颜色定义(可选)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# 日志函数
# ============================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# ============================================================
# 帮助信息
# ============================================================
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --help    显示此帮助信息"
}

# ============================================================
# 主逻辑
# ============================================================
main() {
    # 参数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # 业务逻辑
    log_info "开始执行..."
    # ...
    log_success "执行完成"
}

# 执行主函数
main "$@"
```

## Python 脚本模板

```python
#!/usr/bin/env python3
"""脚本简要说明.

详细说明(可选).

用法:
    python scripts/xxx/script_name.py [选项]

示例:
    python scripts/xxx/script_name.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径(如需访问 app 模块)
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器."""
    parser = argparse.ArgumentParser(description="脚本简要说明")
    parser.add_argument("--dry-run", action="store_true", help="仅预览, 不执行")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    return parser


def main() -> int:
    """主入口函数.

    Returns:
        int: 退出码(0 成功, 非 0 失败).

    """
    args = _build_parser().parse_args()

    # 业务逻辑
    if args.dry_run:
        print("Dry-run 模式, 不执行实际操作")
        return 0

    # ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

# scripts/audits

本目录用于存放“可复跑的审计/量化”脚本（非一次性临时脚本），便于在重构期间持续跟踪指标变化。

## python_or_fallback_scan.py

AST 扫描 Python 的 `or` 兜底链（`ast.BoolOp(op=Or)`），并统计包含 `""/0/False/[]/{}` 的候选（可能覆盖合法 falsy 值）。

### 用法

```bash
# Markdown 输出（可重定向到文件）
uv run python scripts/audits/python_or_fallback_scan.py --paths app --exclude 'tests/**' --format md

# JSON 输出（适合后续做可视化/趋势）
uv run python scripts/audits/python_or_fallback_scan.py --paths app --exclude 'tests/**' --format json > /tmp/or-scan.json
```

### 说明

- 该脚本把每个 `BoolOp(Or)` 计为 1 条“or 链”，不强行区分“条件表达式”还是“默认值兜底”；建议结合：
  - `falsy candidate` 计数（`""/0/False/[]/{}`）
  - 目录/Top 文件分布
  - 代码评审与单测
  来做分批治理。


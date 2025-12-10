"""运行 Pyright 并生成摘要 Markdown 及详细 TXT 报告."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT_DIR / "docs" / "reports"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M%S")

TEXT_REPORT = REPORT_DIR / f"pyright_full_{TIMESTAMP}.txt"
SUMMARY_REPORT = REPORT_DIR / "pyright_full_fix_plan.md"


def run_pyright() -> dict[str, Any]:
    """执行 Pyright 并返回 JSON 结果."""
    cmd = ["pyright", "--outputjson"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        print("Pyright 未输出任何内容,请检查环境", file=sys.stderr)
        sys.exit(1)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        TEXT_REPORT.write_text(result.stdout, encoding="utf-8")
        print(f"Pyright 输出无法解析为 JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return payload


def build_statistics(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    """统计规则、文件、严重级别分布."""
    rule_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    file_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for diag in diagnostics:
        rule = diag.get("rule") or diag.get("category") or "unknown"
        rule_map[rule].append(diag)
        file_map[diag.get("file", "unknown")].append(diag)
    return {
        "rule_map": rule_map,
        "file_map": file_map,
        "error_count": sum(1 for d in diagnostics if d.get("severity") == "error"),
        "warning_count": sum(1 for d in diagnostics if d.get("severity") == "warning"),
    }


def format_range(diag: dict[str, Any]) -> tuple[int, int]:
    """提取行列信息(转为 1-based)."""
    rng = diag.get("range") or {}
    start = rng.get("start") or {}
    return start.get("line", 0) + 1, start.get("character", 0) + 1


def write_text_report(diagnostics: list[dict[str, Any]]) -> None:
    """输出详细 TXT 报告."""
    lines = [
        f"Pyright 全量报告 - 生成时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "=" * 80,
    ]
    for diag in diagnostics:
        path = diag.get("file") or "<unknown>"
        line, col = format_range(diag)
        rule = diag.get("rule") or diag.get("category") or "unknown"
        severity = diag.get("severity", "error").upper()
        message = diag.get("message", "").strip()
        lines.append(f"{path}:{line}:{col} | {severity} | {rule} | {message}")
    TEXT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rule_table(rule_map: dict[str, list[dict[str, Any]]]) -> str:
    """构建 Markdown 表格."""
    header = "| 规则 | 数量 | 示例位置 | 处理建议 |\n| --- | --- | --- | --- |\n"
    rows: list[str] = []
    for rule, items in sorted(rule_map.items(), key=lambda kv: len(kv[1]), reverse=True):
        sample = items[0]
        path = Path(sample.get("file", "unknown")).as_posix()
        line, col = format_range(sample)
        rows.append(
            f"| {rule} | {len(items)} | `{path}:{line}:{col}` | 修复所有 {rule} 相关的类型告警 |",
        )
    return header + "\n".join(rows) + ("\n" if rows else "")


def write_summary(diagnostics: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    """输出 Markdown 摘要."""
    total_files = len(stats["file_map"])
    total_diags = len(diagnostics)
    summary_lines = [
        f"# Pyright 类型检查报告 ({datetime.now():%Y-%m-%d %H:%M})",
        "",
        "## 概览",
        f"- 诊断总数: **{total_diags}** (错误 {stats['error_count']}, 警告 {stats['warning_count']})",
        f"- 受影响文件: **{total_files}** 个",
        f"- 详细报告: `{TEXT_REPORT.relative_to(ROOT_DIR)}`",
        "",
        "## 规则分布",
    ]
    summary_lines.append(build_rule_table(stats["rule_map"]))
    summary_lines.extend(
        [
            "## 建议动作",
            "- 优先处理错误级别的规则, 避免 SQLAlchemy/Flask 运行期异常。",
            "- 补齐缺失的类型存根或在 `pyrightconfig.json` 中豁免确实安全的场景。",
            "- 与业务开发同步修复脚本/任务中的未绑定变量及可空引用。",
        ],
    )
    SUMMARY_REPORT.write_text("\n".join(summary_lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = run_pyright()
    diagnostics = payload.get("generalDiagnostics", [])
    write_text_report(diagnostics)
    stats = build_statistics(diagnostics)
    write_summary(diagnostics, stats)
    print(f"✅ 生成完毕: {SUMMARY_REPORT.relative_to(ROOT_DIR)} / {TEXT_REPORT.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()

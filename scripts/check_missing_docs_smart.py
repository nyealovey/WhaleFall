#!/usr/bin/env python3
"""
智能化注释/文档缺失检测脚本。

扫描指定目录下的 Python 文件，统计哪些模块、类、函数缺少 docstring，
并生成 Markdown 报告，方便对照 Google 风格要求补齐说明。
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DEFAULT_INCLUDE = ("app", "scripts", "tests")
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    "migrations",
    "dist",
    "build",
    "static",
}
SKIP_FUNCTION_PREFIXES = ("_", "test_")


@dataclass
class MissingDocReport:
    module_missing: bool = False
    classes: list[tuple[str, int]] = field(default_factory=list)
    functions: list[tuple[str, int]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.module_missing or self.classes or self.functions)


def should_skip_function(name: str) -> bool:
    if name == "__init__":
        return True
    return name.startswith(SKIP_FUNCTION_PREFIXES)


def iter_python_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for filename in filenames:
                if filename.endswith(".py"):
                    yield Path(dirpath, filename)


def analyze_file(path: Path) -> MissingDocReport | None:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    try:
        module = ast.parse(source)
    except SyntaxError:
        return None

    report = MissingDocReport()
    if ast.get_docstring(module) is None:
        report.module_missing = True

    for node in module.body:
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_") and ast.get_docstring(node) is None:
                report.classes.append((node.name, node.lineno))
            for inner in node.body:
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if should_skip_function(inner.name):
                        continue
                    if ast.get_docstring(inner) is None:
                        report.functions.append((f"{node.name}.{inner.name}", inner.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if should_skip_function(node.name):
                continue
            if ast.get_docstring(node) is None:
                report.functions.append((node.name, node.lineno))

    return None if report.is_empty() else report


def build_markdown(results: dict[Path, MissingDocReport], scanned_files: int) -> str:
    missing_modules = sum(1 for rpt in results.values() if rpt.module_missing)
    missing_classes = sum(len(rpt.classes) for rpt in results.values())
    missing_functions = sum(len(rpt.functions) for rpt in results.values())
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 缺失 Docstring 统计报告",
        "",
        f"- 生成时间：{timestamp}",
        f"- 扫描文件：{scanned_files}",
        f"- 模块缺失：{missing_modules}",
        f("- 类缺失：{missing_classes}"),
        f("- 函数/方法缺失：{missing_functions}"),
        "",
        "> 说明：仅统计对外/公共定义（排除了私有、`__init__`、测试函数等），请按需补充 docstring。",
        "",
    ]

    for path in sorted(results):
        rpt = results[path]
        rel_path = path.as_posix()
        lines.append(f"## {rel_path}")
        if rpt.module_missing:
            lines.append("- 模块缺少 docstring")
        if rpt.classes:
            lines.append("- 类缺少 docstring：")
            for name, lineno in rpt.classes:
                lines.append(f"  - `{name}` (行 {lineno})")
        if rpt.functions:
            lines.append("- 函数/方法缺少 docstring：")
            for name, lineno in rpt.functions:
                lines.append(f"  - `{name}` (行 {lineno})")
        lines.append("")

    if not results:
        lines.append("🎉 所有被扫描的文件 docstring 均已完善！")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描缺失的 docstring")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=DEFAULT_INCLUDE,
        help="要扫描的目录，默认 app scripts tests",
    )
    parser.add_argument(
        "--output",
        default="docs/reports/missing_docstrings.md",
        help="结果保存的 Markdown 文件路径",
    )
    args = parser.parse_args()

    include_paths = [Path(p) for p in args.paths]
    python_files = list(iter_python_files(include_paths))
    results: dict[Path, MissingDocReport] = {}
    for file_path in python_files:
        report = analyze_file(file_path)
        if report:
            results[file_path] = report

    markdown = build_markdown(results, len(python_files))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(
        f"✅ 扫描完成：{len(python_files)} 个文件，发现 {len(results)} 个文件缺少 docstring。"
    )
    print(f"📄 详细结果已保存到 {output_path}")


if __name__ == "__main__":
    main()

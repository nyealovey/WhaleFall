#!/usr/bin/env python3
"""Docstring 缺失检测脚本.

该脚本扫描指定目录下的 Python 文件,识别缺失 docstring 的模块、类、
函数,并生成 Markdown 报告,帮助团队持续对齐 Google 风格文档规范.

Typical usage example::

    python scripts/check_missing_docs_smart.py --paths app scripts
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_INCLUDE = ("app", "scripts", "tests")
DEFAULT_JS_INCLUDE = ("static/js", "app/static/js")
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
SKIP_FUNCTION_PREFIXES = ("test_",)

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger("scripts.check_missing_docs_smart")


@dataclass
class MissingDocEntry:
    """缺失文档条目结构体.

    Attributes:
        name: 需要补充文档的对象名称.
        line: 该对象在源文件中的行号.
        details: 缺失部分的列表,例如 Args 或 @returns.

    """

    name: str
    line: int
    details: tuple[str, ...] = ()


@dataclass
class MissingDocReport:
    """Collect missing docstring metadata for a Python module."""

    doc_label: str = "docstring"
    module_missing: bool = False
    classes: list[MissingDocEntry] = field(default_factory=list)
    functions: list[MissingDocEntry] = field(default_factory=list)
    function_sections: list[MissingDocEntry] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True when the report contains no missing docstrings.

        Returns:
            bool: True 表示无缺失项.

        """
        return not (self.module_missing or self.classes or self.functions or self.function_sections)


def should_skip_function(name: str) -> bool:
    """Check whether a function should be excluded from the scan.

    Args:
        name: Function or method name.

    Returns:
        bool: True when the function is private, magic, or test-only.

    """
    if name == "__init__":
        return True
    return name.startswith(SKIP_FUNCTION_PREFIXES)


def iter_python_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Yield Python files under the provided root directories.

    Args:
        roots: Iterable of root directories to walk.

    Returns:
        Iterable[Path]: 逐个 Python 文件路径的生成器.

    """
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for filename in filenames:
                if filename.endswith(".py"):
                    yield Path(dirpath, filename)


def iter_js_files(roots: Sequence[Path]) -> Iterable[Path]:
    """Yield JavaScript files under the provided root directories.

    Args:
        roots: Sequence of directories to walk while discovering `.js` files.

    Returns:
        Iterable[Path]: 遍历到的 JavaScript 源文件.

    """
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for filename in filenames:
                if filename.endswith(".js"):
                    yield Path(dirpath, filename)


def analyze_python_file(path: Path) -> MissingDocReport | None:
    """Create a missing docstring report for a single Python file.

    Args:
        path: Python source path to analyze.

    Returns:
        MissingDocReport | None: Report detailing missing docstrings or None when
            the module already satisfies the documentation requirements.

    """
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    try:
        module = ast.parse(source)
    except SyntaxError:
        return None

    report = MissingDocReport(doc_label="docstring")
    if ast.get_docstring(module) is None:
        report.module_missing = True

    for node in module.body:
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node)
            if not node.name.startswith("_") and class_doc is None:
                report.classes.append(MissingDocEntry(node.name, node.lineno))
            for inner in node.body:
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if should_skip_function(inner.name):
                        continue
                    doc = ast.get_docstring(inner)
                    if doc is None:
                        report.functions.append(
                            MissingDocEntry(f"{node.name}.{inner.name}", inner.lineno),
                        )
                    else:
                        missing_sections = get_python_doc_issues(inner, doc)
                        if missing_sections:
                            report.function_sections.append(
                                MissingDocEntry(
                                    f"{node.name}.{inner.name}",
                                    inner.lineno,
                                    tuple(missing_sections),
                                ),
                            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if should_skip_function(node.name):
                continue
            doc = ast.get_docstring(node)
            if doc is None:
                report.functions.append(MissingDocEntry(node.name, node.lineno))
            else:
                missing_sections = get_python_doc_issues(node, doc)
                if missing_sections:
                    report.function_sections.append(
                        MissingDocEntry(node.name, node.lineno, tuple(missing_sections)),
                    )

    return None if report.is_empty() else report


def get_python_doc_issues(node: ast.AST, docstring: str) -> list[str]:
    """返回函数文档缺失的 Google 风格段落.

    读取函数定义的 docstring,并检查是否包含 Args 与 Returns 区块,
    以便报告脚本能够精准提示缺失项目.

    Args:
        node: 需要检查的函数或协程 AST 节点.
        docstring: 自节点提取的原始文档字符串内容.

    Returns:
        list[str]: 缺失的段落名称列表,例如 ``"Args"`` 或 ``"Returns"``.

    """
    missing: list[str] = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [arg.arg for arg in node.args.args if arg.arg not in {"self", "cls"}]
        if args and "Args:" not in docstring:
            missing.append("Args")
        if "Returns:" not in docstring:
            missing.append("Returns")
    return missing


JS_FUNCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:export\s+)?function\s+([A-Za-z0-9_]+)\s*\("),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s+)?function\b",
    ),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s+)?\([^=]*?\)\s*=>",
    ),
)
JS_CLASS_PATTERN = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z0-9_]+)")


def analyze_js_file(path: Path) -> MissingDocReport | None:
    """Create a missing JSDoc report for a JavaScript file.

    Args:
        path: JavaScript source file path to evaluate.

    Returns:
        MissingDocReport | None: Report enumerating missing JSDoc entries or
            None when the file already satisfies documentation requirements.

    """
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

    lines = source.splitlines()
    report = MissingDocReport(doc_label="JSDoc")
    inside_jsdoc = False
    jsdoc_buffer: list[str] = []
    pending_jsdoc: str | None = None

    for idx, line in enumerate(lines):
        lineno = idx + 1
        stripped = line.strip()

        if inside_jsdoc:
            jsdoc_buffer.append(stripped)
            if "*/" in stripped:
                inside_jsdoc = False
                pending_jsdoc = "\n".join(jsdoc_buffer)
                jsdoc_buffer = []
            continue

        if stripped.startswith("/**"):
            jsdoc_buffer = [stripped]
            if "*/" in stripped and stripped.index("/*") < stripped.rfind("*/"):
                pending_jsdoc = "\n".join(jsdoc_buffer)
                jsdoc_buffer = []
            else:
                inside_jsdoc = True
            continue

        if stripped.startswith("//"):
            continue

        if stripped.startswith("/*"):
            pending_jsdoc = None
            continue

        class_match = JS_CLASS_PATTERN.match(line)
        if class_match:
            class_name = class_match.group(1)
            doc_text = pending_jsdoc
            pending_jsdoc = None
            if doc_text:
                pass
            elif not class_name.startswith(SKIP_FUNCTION_PREFIXES):
                report.classes.append(MissingDocEntry(class_name, lineno))
            continue

        func_name = _match_js_function(line)
        if func_name:
            doc_text = pending_jsdoc
            pending_jsdoc = None
            if should_skip_function(func_name):
                continue
            if not doc_text:
                report.functions.append(MissingDocEntry(func_name, lineno))
            else:
                missing_sections = []
                has_parameters = _has_js_parameters(lines, idx)
                if has_parameters and "@param" not in doc_text:
                    missing_sections.append("@param")
                if "@returns" not in doc_text and "@return" not in doc_text:
                    missing_sections.append("@returns")
                if missing_sections:
                    report.function_sections.append(
                        MissingDocEntry(func_name, lineno, tuple(missing_sections)),
                    )
            continue

    return None if report.is_empty() else report


def _match_js_function(line: str) -> str | None:
    """Return the first matched JavaScript function name, if any.

    Args:
        line: Single line of JavaScript source code.

    Returns:
        str | None: Function name when matched, otherwise None.

    """
    for pattern in JS_FUNCTION_PATTERNS:
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None


def _has_js_parameters(lines: Sequence[str], start_index: int) -> bool:
    """判断匹配的 JavaScript 函数是否声明参数.

    通过解析函数定义所在行及其后续行,拼合完整签名并检测括号内的
    字符是否为空,以此决定是否需要 @param 提示.

    Args:
        lines: JavaScript 文件的全部源代码行集合.
        start_index: 函数声明所在的零基索引.

    Returns:
        bool: 若括号内存在非空参数列表则返回 True.

    """
    signature = _collect_js_signature(lines, start_index)
    start = signature.find("(")
    if start == -1:
        return False
    depth = 0
    param_start = None
    for idx in range(start, len(signature)):
        char = signature[idx]
        if char == "(":
            depth += 1
            if depth == 1:
                param_start = idx + 1
        elif char == ")":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and param_start is not None:
                params = signature[param_start:idx].strip()
                return bool(params)
    return False


def _collect_js_signature(lines: Sequence[str], start_index: int) -> str:
    """收集(可能跨行的)函数签名文本.

    Args:
        lines: 当前 JavaScript 文件的所有源代码行.
        start_index: 函数声明起始的零基索引.

    Returns:
        str: 自起始行开始到匹配到闭合括号之间的拼接文本.

    """
    buffer: list[str] = []
    depth = 0
    saw_paren = False
    for idx in range(start_index, len(lines)):
        fragment = lines[idx]
        buffer.append(fragment.strip())
        for char in fragment:
            if char == "(":
                depth += 1
                saw_paren = True
            elif char == ")":
                if depth == 0:
                    continue
                depth -= 1
        if saw_paren and depth == 0:
            break
    return " ".join(buffer)


def build_markdown(results: dict[Path, MissingDocReport], scanned_files: int) -> str:
    """Render a Markdown summary for missing docstrings or JSDoc entries.

    Args:
        results: Mapping of file paths to their missing documentation report.
        scanned_files: Total number of scanned files across all languages.

    Returns:
        str: Markdown document containing aggregate and per-file statistics.

    """
    missing_modules = sum(1 for rpt in results.values() if rpt.module_missing)
    missing_classes = sum(len(rpt.classes) for rpt in results.values())
    missing_functions = sum(len(rpt.functions) for rpt in results.values())
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 缺失 Docstring 统计报告",
        "",
        f"- 生成时间:{timestamp}",
        f"- 扫描文件:{scanned_files}",
        f"- 模块缺失:{missing_modules}",
        f"- 类缺失:{missing_classes}",
        f"- 函数/方法缺失:{missing_functions}",
        "",
        "> 说明:仅统计对外/公共定义(排除了私有、`__init__`、测试函数等),请按需补充 docstring.",
        "",
    ]

    for path in sorted(results):
        rpt = results[path]
        rel_path = path.as_posix()
        doc_label = rpt.doc_label
        lines.append(f"## {rel_path}")
        if rpt.module_missing:
            lines.append(f"- 模块缺少 {doc_label}")
        if rpt.classes:
            lines.append(f"- 类缺少 {doc_label}:")
            for entry in rpt.classes:
                lines.append(f"  - `{entry.name}` (行 {entry.line})")
        if rpt.functions:
            lines.append(f"- 函数/方法缺少 {doc_label}:")
            for entry in rpt.functions:
                lines.append(f"  - `{entry.name}` (行 {entry.line})")
        if rpt.function_sections:
            lines.append("- 函数/方法文档不完整:")
            for entry in rpt.function_sections:
                detail = ", ".join(entry.details)
                lines.append(f"  - `{entry.name}` (行 {entry.line}) 缺少 {detail}")
        lines.append("")

    if not results:
        lines.append("🎉 所有被扫描的文件 docstring 均已完善!")

    return "\n".join(lines)


def main() -> None:
    """Docstring 扫描 CLI 的入口函数.

    解析命令行参数,遍历 Python 与 JavaScript 文件并生成 Markdown 报告,
    供团队对照修复缺失的文档条目.

    Returns:
        None: 函数以副作用执行 I/O,不返回任何值.

    """
    parser = argparse.ArgumentParser(description="扫描缺失的 docstring")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=DEFAULT_INCLUDE,
        help="要扫描的目录,默认 app scripts tests",
    )
    parser.add_argument(
        "--js-paths",
        nargs="*",
        default=DEFAULT_JS_INCLUDE,
        help="要扫描的 JavaScript 目录,默认 static/js",
    )
    parser.add_argument(
        "--skip-js",
        action="store_true",
        help="仅扫描 Python 文件,不检测 JSDoc",
    )
    parser.add_argument(
        "--output",
        default="docs/reports/missing_docstrings.md",
        help="结果保存的 Markdown 文件路径",
    )
    args = parser.parse_args()

    include_paths = [Path(p) for p in args.paths]
    python_files = list(iter_python_files(include_paths))
    js_paths = [Path(p) for p in args.js_paths]
    js_files: list[Path] = []
    if not args.skip_js:
        js_files = list(iter_js_files(js_paths))

    results: dict[Path, MissingDocReport] = {}
    for file_path in python_files:
        report = analyze_python_file(file_path)
        if report:
            results[file_path] = report
    for js_path in js_files:
        report = analyze_js_file(js_path)
        if report:
            results[js_path] = report

    total_files = len(python_files) + len(js_files)
    markdown = build_markdown(results, total_files)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    summary_parts = [
        f"✅ 扫描完成:共 {total_files} 个文件",
        f"Python:{len(python_files)}",
    ]
    if js_files:
        summary_parts.append(f"JavaScript:{len(js_files)}")
    LOGGER.info("%s,发现 %d 个文件缺少文档.", ",".join(summary_parts), len(results))
    LOGGER.info("📄 详细结果已保存到 %s", output_path)


if __name__ == "__main__":
    main()

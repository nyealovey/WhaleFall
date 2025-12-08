#!/usr/bin/env python3
"""扫描静态资源中的硬编码颜色,辅助色彩收敛专项.

默认扫描 `app/static/css` 与 `app/static/js`,忽略 vendor 目录以及
`variables.css`/`theme-orange.css` 等 token 定义文件.可通过参数
`--json` 输出机器可读的结果,使用 `--strict` 在发现违规时返回非零状态.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = (ROOT / "app/static/css", ROOT / "app/static/js")
ALLOWLIST = {
    ROOT / "app/static/css/variables.css",
    ROOT / "app/static/css/theme-orange.css",
}
IGNORE_DIRS = {
    ROOT / "app/static/vendor",
    ROOT / "app/static/js/vendor",
}
HEX_PATTERN = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGBA_PATTERN = re.compile(r"\brgba?\([^)]*\)")

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger("scripts.audit_colors")


def iter_files(paths: Sequence[Path]) -> Sequence[Path]:
    for base in paths:
        if not base.exists():
            continue
        base_path = base.resolve()
        if base_path.is_file():
            yield base_path
            continue
        for path in base_path.rglob("*"):
            if path.is_dir():
                continue
            if any(ignored in path.parents for ignored in IGNORE_DIRS):
                continue
            yield path


def scan_file(path: Path) -> list[tuple[int, str]]:
    if path in ALLOWLIST:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    matches: list[tuple[int, str]] = []
    word_char = re.compile(r"[A-Za-z0-9_-]")
    for idx, line in enumerate(text.splitlines(), start=1):
        tokens: list[str] = []
        for match in HEX_PATTERN.finditer(line):
            end = match.end()
            if end < len(line) and word_char.match(line[end]):
                continue
            tokens.append(match.group(0))
        tokens.extend(RGBA_PATTERN.findall(line))
        if tokens:
            matches.append((idx, ", ".join(tokens)))
    return matches


def format_report(results: dict[str, list[tuple[int, str]]]) -> str:
    lines: list[str] = []
    for path, entries in sorted(results.items()):
        rel = Path(path).relative_to(ROOT)
        lines.append(f"{rel}")
        for lineno, token in entries:
            lines.append(f"  L{lineno}: {token}")
    return "\n".join(lines)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_SCAN_ROOTS,
                        help="待扫描目录或文件,默认检查 app/static/css, app/static/js")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="以 JSON 形式输出结果")
    parser.add_argument("--strict", action="store_true",
                        help="检测到硬编码颜色时返回非零状态")
    args = parser.parse_args(list(argv)[1:])

    findings: dict[str, list[tuple[int, str]]] = {}
    for path in iter_files(args.paths):
        matches = scan_file(path)
        if matches:
            findings[str(path.resolve())] = matches

    if args.as_json:
        payload = {
            "violations": [
                {
                    "file": str(Path(path).relative_to(ROOT)),
                    "entries": [
                        {"line": lineno, "value": value} for lineno, value in matches
                    ],
                }
                for path, matches in sorted(findings.items())
            ],
        }
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    elif findings:
        LOGGER.info("%s", format_report(findings))
    else:
        LOGGER.info("未检测到硬编码颜色,已全部引用 token ✅")

    if args.strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

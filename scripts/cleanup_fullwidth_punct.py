#!/usr/bin/env python3
"""批量替换全角标点为半角字符."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TRANSLATION_MAP = {
    "，": ",",
    "。": ".",
    "：": ":",
    "；": ";",
    "！": "!",
    "？": "?",
    "（": "(",
    "）": ")",
    "【": "[",
    "】": "]",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}

SUPPORTED_SUFFIXES = {".py", ".pyi", ".md", ".txt"}


def should_process(path: Path) -> bool:
    return path.suffix in SUPPORTED_SUFFIXES


def normalize_text(text: str) -> str:
    result = text
    for full, half in TRANSLATION_MAP.items():
        result = result.replace(full, half)
    return result


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = normalize_text(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def main() -> int:
    parser = argparse.ArgumentParser("cleanup_fullwidth_punct")
    parser.add_argument("paths", nargs="*", default=["app"], help="目标路径，默认 app")
    args = parser.parse_args()

    changed_files: list[Path] = []
    skipped_files: list[Path] = []

    for path_str in args.paths:
        root = Path(path_str).resolve()
        if not root.exists():
            print(f"路径不存在: {root}", file=sys.stderr)
            continue
        for file_path in iter_files(root):
            if not should_process(file_path):
                continue
            if process_file(file_path):
                changed_files.append(file_path)
            else:
                skipped_files.append(file_path)

    print(f"处理完成: 修改 {len(changed_files)} 个文件，跳过 {len(skipped_files)} 个文件。")
    for file_path in changed_files:
        print(f"更新 -> {file_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

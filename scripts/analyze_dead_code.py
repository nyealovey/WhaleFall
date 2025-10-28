#!/usr/bin/env python3
"""Scan the app/ package for unused code symbols using vulture."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any, Iterable, List, Sequence

try:
    from vulture import Vulture
except ImportError as exc:
    print(
        "vulture is required for this script. Install it with 'pip install vulture'.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


DEFAULT_TARGET = "app"
SUPPORTED_FORMATS = {"table", "json"}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect Python symbols that are defined but never used. "
            "This is a thin wrapper around vulture configured for the Taifish app."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[DEFAULT_TARGET],
        help="One or more paths to scan (defaults to 'app').",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=80,
        help="Minimum confidence score reported by vulture (0-100, default: 80).",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help=(
            "Glob patterns (evaluated against absolute paths) to exclude from the report. "
            "Example: --exclude '*/tests/*'"
        ),
    )
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="table",
        help="Output format for the analysis results (default: table).",
    )
    parser.add_argument(
        "--json-indent",
        type=int,
        default=2,
        help="Indentation level applied when --format json is selected (default: 2).",
    )
    parser.add_argument(
        "--sort-by",
        choices=["confidence", "name", "path"],
        default="confidence",
        help="Sorting key for results (default: confidence).",
    )
    return parser.parse_args(argv)


def sort_items(items: Iterable[Any], *, sort_by: str) -> List[Any]:
    if sort_by == "confidence":
        # Higher confidence first, tie-breaker on file path and line number.
        return sorted(
            items,
            key=lambda item: (-item.confidence, str(item.filename), item.first_lineno, item.name),
        )
    if sort_by == "name":
        return sorted(items, key=lambda item: (item.name, str(item.filename), item.first_lineno))
    return sorted(items, key=lambda item: (str(item.filename), item.first_lineno, item.name))


def format_item(item: Any) -> dict:
    resolved = Path(item.filename).resolve()
    try:
        relative = resolved.relative_to(Path.cwd())
    except ValueError:
        relative = resolved
    return {
        "name": item.name,
        "type": item.typ,
        "path": str(relative),
        "line": item.first_lineno,
        "confidence": item.confidence,
        "message": item.message,
    }


def print_table(items: Sequence[dict]) -> None:
    if not items:
        print("No dead code candidates found.")
        return

    headers = ("Type", "Name", "Location", "Conf")
    rows = [
        (
            entry["type"],
            entry["name"],
            f"{entry['path']}:{entry['line']}",
            f"{entry['confidence']}%",
        )
        for entry in items
    ]
    col_widths = [
        max(len(header), *(len(row[idx]) for row in rows)) for idx, header in enumerate(headers)
    ]

    def fmt_row(row: Sequence[str]) -> str:
        return "  ".join(cell.ljust(col_widths[idx]) for idx, cell in enumerate(row))

    print(fmt_row(headers))
    print("  ".join("-" * width for width in col_widths))
    for row in rows:
        print(fmt_row(row))


def print_json(items: Sequence[dict], indent: int) -> None:
    print(json.dumps(items, indent=indent))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    for path in args.paths:
        if not Path(path).exists():
            print(f"error: path '{path}' does not exist", file=sys.stderr)
            return 2

    vulture = Vulture(verbose=False)
    vulture.scavenge(args.paths)

    exclude_patterns = tuple(args.exclude or [])

    def is_excluded(path: Path) -> bool:
        if not exclude_patterns:
            return False
        path_str = str(path)
        return any(fnmatch.fnmatch(path_str, pattern) for pattern in exclude_patterns)

    collected: List[Any] = []
    for item in vulture.get_unused_code():
        path = Path(item.filename).resolve()
        if is_excluded(path):
            continue
        if item.confidence < args.min_confidence:
            continue
        collected.append(item)

    items = sort_items(collected, sort_by=args.sort_by)
    formatted = [format_item(item) for item in items]

    if args.format == "json":
        print_json(formatted, indent=args.json_indent)
    else:
        print_table(formatted)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

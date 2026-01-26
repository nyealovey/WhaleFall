#!/usr/bin/env python3
"""AST-based `or` fallback scan for Python code.

Goals (per docs/plans/2026-01-16-backend-or-fallback-downshift-to-schemas.md):
- Quantify `or` fallback chains (BoolOp(Or)) over time.
- Flag chains containing potential "dangerous falsy candidates": ""/0/False/[]/{}.
- Provide directory and top-file distributions to guide refactors.

Notes:
- This script treats every `ast.BoolOp(op=Or)` as one "or chain". It does not try to
  distinguish "boolean condition" vs "fallback defaulting" intent; use the
  "falsy candidate" signals + path distribution to triage.
- Output is designed for tracking baselines (MD/JSON) and CI trends.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _echo(message: str = "") -> None:
    """Write a line to stdout (avoid Ruff T201)."""
    sys.stdout.write(f"{message}\n")


@dataclass(frozen=True)
class OrFallbackHit:
    file: str
    lineno: int
    col: int
    end_lineno: int | None
    end_col: int | None
    values_count: int
    falsy_literals: list[str]
    patterns: list[str]
    line: str


def _path_matches_any_glob(path: str, patterns: list[str]) -> bool:
    # Normalize path separators for glob matching.
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _iter_python_files(paths: list[str], *, exclude: list[str]) -> list[Path]:
    output: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix != ".py":
                continue
            rel = path.as_posix()
            if _path_matches_any_glob(rel, exclude):
                continue
            output.append(path)
            continue

        if path.is_dir():
            for file_path in sorted(path.rglob("*.py")):
                rel = file_path.as_posix()
                if _path_matches_any_glob(rel, exclude):
                    continue
                output.append(file_path)
    return output


def _bucket_dir(path: str) -> str:
    # Group by `app/<layer>/**` for app code, else `<top>/**`.
    parts = Path(path).as_posix().split("/")
    if len(parts) >= 2 and parts[0] == "app":
        return f"app/{parts[1]}/**"
    if parts:
        return f"{parts[0]}/**"
    return path


def _extract_falsy_literal(node: ast.AST) -> str | None:
    # Keep labels aligned with audit report wording.
    literal: str | None = None

    if isinstance(node, ast.Constant):
        value = node.value
        if type(value) is bool and value is False:
            literal = "False"
        elif type(value) is str and value == "":
            literal = '""'
        elif type(value) in (int, float) and value == 0:
            literal = "0"
    elif isinstance(node, ast.List) and not node.elts:
        literal = "[]"
    elif isinstance(node, ast.Dict) and not node.keys and not node.values:
        literal = "{}"

    return literal


def _is_dict_get_call(node: ast.AST) -> bool:
    # `something.get("key")` (key must be non-empty string literal)
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr != "get":
        return False
    if not node.args:
        return False
    key = node.args[0]
    return isinstance(key, ast.Constant) and isinstance(key.value, str) and bool(key.value)


class _OrFallbackVisitor(ast.NodeVisitor):
    def __init__(self, *, file_path: str, source_lines: list[str], exclude_node_ids: set[int]) -> None:
        self._file_path = file_path
        self._source_lines = source_lines
        self._exclude_node_ids = exclude_node_ids
        self.hits: list[OrFallbackHit] = []

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:  # NodeVisitor signature
        if isinstance(node.op, ast.Or) and id(node) not in self._exclude_node_ids:
            falsy_literals = sorted(
                {literal for value in node.values if (literal := _extract_falsy_literal(value)) is not None}
            )

            patterns: set[str] = set()
            if len(node.values) >= 2 and all(_is_dict_get_call(value) for value in node.values):
                patterns.add("dict.get(...) or dict.get(...)")
            if any(isinstance(value, ast.Dict) and not value.keys and not value.values for value in node.values):
                patterns.add("... or {}")
            if any(isinstance(value, ast.List) and not value.elts for value in node.values):
                patterns.add("... or []")
            if any(
                isinstance(value, ast.Constant) and type(value.value) is str and value.value == ""
                for value in node.values
            ):
                patterns.add('... or ""')
            if any(
                isinstance(value, ast.Constant) and type(value.value) is bool and value.value is False
                for value in node.values
            ):
                patterns.add("... or False")
            if any(
                isinstance(value, ast.Constant) and type(value.value) in (int, float) and value.value == 0
                for value in node.values
            ):
                patterns.add("... or 0")

            lineno = getattr(node, "lineno", 0) or 0
            col = getattr(node, "col_offset", 0) or 0
            end_lineno = getattr(node, "end_lineno", None)
            end_col = getattr(node, "end_col_offset", None)
            line = ""
            if lineno and 0 < lineno <= len(self._source_lines):
                line = self._source_lines[lineno - 1].rstrip("\n")

            self.hits.append(
                OrFallbackHit(
                    file=self._file_path,
                    lineno=lineno,
                    col=col,
                    end_lineno=end_lineno,
                    end_col=end_col,
                    values_count=len(node.values),
                    falsy_literals=falsy_literals,
                    patterns=sorted(patterns),
                    line=line.strip(),
                )
            )

        return self.generic_visit(node)


def _scan_file(path: Path) -> tuple[list[OrFallbackHit], str | None]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], f"read_error: {exc}"

    try:
        tree = ast.parse(source, filename=path.as_posix())
    except SyntaxError as exc:
        return [], f"syntax_error: {exc}"

    # The audit plan tracks "or fallback chains (non-test positions)". Exclude BoolOp(Or)
    # nodes that are used as boolean "test" expressions (if/while/assert/ifexp guards, etc).
    exclude_node_ids: set[int] = set()

    def _collect_or_boolops(expr: ast.AST | None) -> None:
        if expr is None:
            return
        for sub in ast.walk(expr):
            if isinstance(sub, ast.BoolOp) and isinstance(sub.op, ast.Or):
                exclude_node_ids.add(id(sub))

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.Assert, ast.IfExp)):
            _collect_or_boolops(getattr(node, "test", None))
            continue
        if isinstance(node, ast.comprehension):
            for cond in node.ifs:
                _collect_or_boolops(cond)
            continue
        if isinstance(node, ast.match_case):
            _collect_or_boolops(node.guard)
            continue

    visitor = _OrFallbackVisitor(
        file_path=path.as_posix(),
        source_lines=source.splitlines(keepends=True),
        exclude_node_ids=exclude_node_ids,
    )
    visitor.visit(tree)
    return visitor.hits, None


def _count_bool(value: bool) -> int:
    return 1 if value else 0


def _build_distributions(
    hits: list[OrFallbackHit],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]], Counter[str]]:
    dir_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"or": 0, "candidate": 0})
    file_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"or": 0, "candidate": 0})
    pattern_counts: Counter[str] = Counter()

    for hit in hits:
        bucket = _bucket_dir(hit.file)
        dir_counts[bucket]["or"] += 1
        dir_counts[bucket]["candidate"] += _count_bool(bool(hit.falsy_literals))

        file_counts[hit.file]["or"] += 1
        file_counts[hit.file]["candidate"] += _count_bool(bool(hit.falsy_literals))

        for p in hit.patterns:
            pattern_counts[p] += 1

    return dir_counts, file_counts, pattern_counts


def _render_markdown(
    *,
    generated_at: str,
    paths: list[str],
    exclude: list[str],
    python_files: int,
    parse_failures: dict[str, str],
    hits: list[OrFallbackHit],
) -> str:
    total_or = len(hits)
    total_candidate = sum(_count_bool(bool(hit.falsy_literals)) for hit in hits)

    dir_counts, file_counts, pattern_counts = _build_distributions(hits)
    dir_rows = sorted(dir_counts.items(), key=lambda kv: (kv[1]["candidate"], kv[1]["or"]), reverse=True)
    top_files = sorted(file_counts.items(), key=lambda kv: (kv[1]["candidate"], kv[1]["or"]), reverse=True)[:30]

    lines: list[str] = []
    lines.append("# Python `or` Fallback Scan (AST)")
    lines.append("")
    lines.append(f"- Generated: {generated_at}")
    lines.append(f"- Paths: {', '.join(paths)}")
    lines.append(f"- Exclude: {', '.join(exclude) if exclude else '(none)'}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Python files scanned: {python_files}")
    lines.append(f"- AST parse failures: {len(parse_failures)}")
    lines.append(f"- `or` chains (BoolOp(Or)): {total_or}")
    lines.append(f'- Chains with `""/0/False/[]/{{}}` candidates: {total_candidate}')
    lines.append("")

    if parse_failures:
        lines.append("## Parse Failures")
        lines.append("")
        lines.append("| File | Error |")
        lines.append("|---|---|")
        for file, err in sorted(parse_failures.items()):
            lines.append(f"| `{file}` | {err} |")
        lines.append("")

    lines.append("## Directory Distribution")
    lines.append("")
    lines.append("| Directory | `or` chains | candidate chains |")
    lines.append("|---|---:|---:|")
    for bucket, counts in dir_rows:
        lines.append(f"| `{bucket}` | {counts['or']} | {counts['candidate']} |")
    lines.append("")

    lines.append("## Top Files (by candidate chains, then total)")
    lines.append("")
    lines.append("| File | `or` chains | candidate chains |")
    lines.append("|---|---:|---:|")
    for file, counts in top_files:
        lines.append(f"| `{file}` | {counts['or']} | {counts['candidate']} |")
    lines.append("")

    if pattern_counts:
        lines.append("## Pattern Counts")
        lines.append("")
        lines.append("| Pattern | Hits |")
        lines.append("|---|---:|")
        for pattern, count in pattern_counts.most_common():
            lines.append(f"| `{pattern}` | {count} |")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="AST-based scan for Python `or` fallback chains.")
    parser.add_argument(
        "--paths",
        nargs="+",
        default=["app"],
        help="Paths to scan (files or directories). Default: app",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob patterns to exclude (matched against repo-relative paths), e.g. 'tests/**'. Repeatable.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "md"),
        default="md",
        help="Output format. Default: md",
    )
    args = parser.parse_args(argv)

    python_files = _iter_python_files(args.paths, exclude=list(args.exclude))
    parse_failures: dict[str, str] = {}
    hits: list[OrFallbackHit] = []

    for file_path in python_files:
        file_hits, failure = _scan_file(file_path)
        if failure is not None:
            parse_failures[file_path.as_posix()] = failure
            continue
        hits.extend(file_hits)

    generated_at = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S %Z")

    if args.format == "json":
        dir_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"or": 0, "candidate": 0})
        file_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"or": 0, "candidate": 0})
        pattern_counts: Counter[str] = Counter()

        for hit in hits:
            bucket = _bucket_dir(hit.file)
            dir_counts[bucket]["or"] += 1
            dir_counts[bucket]["candidate"] += _count_bool(bool(hit.falsy_literals))

            file_counts[hit.file]["or"] += 1
            file_counts[hit.file]["candidate"] += _count_bool(bool(hit.falsy_literals))

            for p in hit.patterns:
                pattern_counts[p] += 1

        payload: dict[str, Any] = {
            "generated_at": generated_at,
            "paths": list(args.paths),
            "exclude": list(args.exclude),
            "python_files_scanned": len(python_files),
            "ast_parse_failures": parse_failures,
            "or_chains_total": len(hits),
            "or_chains_with_falsy_candidates_total": sum(_count_bool(bool(hit.falsy_literals)) for hit in hits),
            "directory_distribution": dict(sorted(dir_counts.items(), key=lambda kv: kv[0])),
            "file_distribution": dict(sorted(file_counts.items(), key=lambda kv: kv[0])),
            "pattern_counts": dict(pattern_counts.most_common()),
            "hits": [asdict(hit) for hit in hits],
        }
        _echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    md = _render_markdown(
        generated_at=generated_at,
        paths=list(args.paths),
        exclude=list(args.exclude),
        python_files=len(python_files),
        parse_failures=parse_failures,
        hits=hits,
    )
    _echo(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

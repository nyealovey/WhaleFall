#!/usr/bin/env python3
"""Generate/check a `/api` route inventory derived from the route reference doc.

Background
----------
Some migration docs keep a manually maintained endpoint list (METHOD + Path). That
list can drift from:
  - the source route reference doc: `docs/reference/api/api-routes-documentation.md`
  - the actual Flask routes (which are already checkable via
    `scripts/dev/docs/check_api_routes_reference.py`)

This script provides:
  - a **generated** inventory file (single source for "METHOD + Path" counting)
  - a **check** mode to guard drift
  - an optional progress-doc check to ensure its endpoint set stays in sync
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_DOC = REPO_ROOT / "docs/reference/api/api-routes-documentation.md"
DEFAULT_INVENTORY_OUT = REPO_ROOT / "docs/changes/refactor/artifacts/004-phase3-api-routes.md"
DEFAULT_PROGRESS_DOC = REPO_ROOT / "docs/changes/refactor/004-flask-restx-openapi-migration-progress.md"


@dataclass(frozen=True)
class Endpoint:
    module_no: int
    module_name: str
    method: str
    path: str
    description: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.method, self.path)


_MODULE_RE = re.compile(r"^##\s+(?P<num>\d+)\.\s+(?P<name>.+?)\s*$")
_API_SECTION_RE = re.compile(r"^###\s+API 接口\s*$")
_ROW_RE = re.compile(
    r"^[|]\s*(?:`(?P<path_bt>[^`]+)`|(?P<path>/[^|]+?))\s*[|]\s*(?P<methods>[^|]+?)\s*[|]\s*(?P<handler>[^|]+?)\s*[|]\s*(?P<desc>[^|]+?)\s*[|]\s*$"
)


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _split_methods(raw: str) -> list[str]:
    methods = [part.strip().upper() for part in raw.split(",") if part.strip()]
    return [m for m in methods if re.fullmatch(r"[A-Z]+", m)]


def iter_api_endpoints_from_reference_doc(doc_text: str) -> Iterator[Endpoint]:
    module_no: int | None = None
    module_name: str | None = None
    in_api_section = False

    for line in doc_text.splitlines():
        module_match = _MODULE_RE.match(line)
        if module_match:
            module_no = int(module_match.group("num"))
            module_name = _normalize_ws(module_match.group("name"))
            in_api_section = False
            continue

        if _API_SECTION_RE.match(line):
            in_api_section = True
            continue

        if line.startswith("### "):
            in_api_section = False
            continue

        if not in_api_section or module_no is None or module_name is None:
            continue

        row_match = _ROW_RE.match(line)
        if not row_match:
            continue

        path = (row_match.group("path_bt") or row_match.group("path") or "").strip()
        if path in {"路径", "------"} or not path.startswith("/"):
            continue
        if "/api" not in path:
            # "API 接口" 理论上都包含 `/api`, 但这里加一个保险过滤.
            continue

        methods = _split_methods(row_match.group("methods").strip())
        if not methods:
            continue

        desc = row_match.group("desc").strip()
        desc = desc if desc not in {"描述", "------"} else ""

        for method in methods:
            yield Endpoint(
                module_no=module_no,
                module_name=module_name,
                method=method,
                path=path,
                description=_normalize_ws(desc),
            )


def _dedupe_preserve_order(items: Iterable[Endpoint]) -> list[Endpoint]:
    seen: set[tuple[str, str]] = set()
    result: list[Endpoint] = []
    for item in items:
        if item.key in seen:
            continue
        seen.add(item.key)
        result.append(item)
    return result


def _group_by_module(endpoints: Iterable[Endpoint]) -> list[tuple[int, str, list[Endpoint]]]:
    groups: dict[tuple[int, str], list[Endpoint]] = {}
    order: list[tuple[int, str]] = []
    for ep in endpoints:
        key = (ep.module_no, ep.module_name)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(ep)
    return [(no, name, groups[(no, name)]) for no, name in order]


def render_inventory_markdown(endpoints: Iterable[Endpoint], *, source_doc_rel: str) -> str:
    endpoints_list = list(endpoints)
    total = len(endpoints_list)

    lines: list[str] = []
    lines.append("# Phase 3 `/api` 端点清单（自动生成）")
    lines.append("")
    lines.append("> 注意: 本文件为生成产物，请勿手工编辑。")
    lines.append(f"> 来源: `{source_doc_rel}` 的 `### API 接口` 表格。")
    lines.append("> 口径: 路径包含 `/api` 的 JSON API 端点。")
    lines.append("> 去重规则: `METHOD + Path`。")
    lines.append(f"> 总计: {total}")
    lines.append("> 生成命令: `python3 scripts/dev/docs/generate_api_routes_inventory.py`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## API 清单(按模块)")
    lines.append("")

    for module_no, module_name, module_endpoints in _group_by_module(endpoints_list):
        lines.append(f"### {module_no}. {module_name}")
        lines.append("")
        lines.append("| 路径 | 方法 | 描述 |")
        lines.append("|------|------|------|")
        for ep in module_endpoints:
            lines.append(f"| `{ep.path}` | {ep.method} | {ep.description} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _print_unified_diff(*, from_text: str, to_text: str, from_name: str, to_name: str) -> None:
    diff = difflib.unified_diff(
        from_text.splitlines(keepends=True),
        to_text.splitlines(keepends=True),
        fromfile=from_name,
        tofile=to_name,
    )
    sys.stdout.writelines(diff)


def _extract_progress_endpoints(progress_text: str) -> set[tuple[str, str]]:
    # Progress doc stores endpoints as backticks: `METHOD /path` - we only need the set.
    # NOTE: do not try to parse status columns; this is intentionally tolerant.
    pattern = re.compile(r"`(?P<method>[A-Z]+)\s+(?P<path>/[^`\s]+)`")
    endpoints: set[tuple[str, str]] = set()
    for match in pattern.finditer(progress_text):
        method = match.group("method").strip().upper()
        path = match.group("path").strip()
        if "/api" not in path:
            continue
        endpoints.add((method, path))
    return endpoints


def check_progress_doc(*, source_doc: Path, progress_doc: Path) -> int:
    source_text = _read_text(source_doc)
    expected = _dedupe_preserve_order(iter_api_endpoints_from_reference_doc(source_text))
    expected_set = {ep.key for ep in expected}

    progress_text = _read_text(progress_doc)
    actual_set = _extract_progress_endpoints(progress_text)

    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)

    sys.stdout.write(f"expected_endpoints: {len(expected_set)}\n")
    sys.stdout.write(f"progress_endpoints : {len(actual_set)}\n")
    sys.stdout.write(f"missing            : {len(missing)}\n")
    sys.stdout.write(f"extra              : {len(extra)}\n")

    if missing:
        sys.stdout.write("\nMissing in progress doc (METHOD Path):\n")
        for method, path in missing[:50]:
            sys.stdout.write(f"- {method} {path}\n")
        if len(missing) > 50:
            sys.stdout.write(f"... ({len(missing) - 50} more)\n")

    if extra:
        sys.stdout.write("\nExtra in progress doc (METHOD Path):\n")
        for method, path in extra[:50]:
            sys.stdout.write(f"- {method} {path}\n")
        if len(extra) > 50:
            sys.stdout.write(f"... ({len(extra) - 50} more)\n")

    return 1 if (missing or extra) else 0


def _run_check_progress(args: argparse.Namespace) -> int:
    if not args.progress_doc.exists():
        sys.stderr.write(f"progress doc not found: {args.progress_doc}\n")
        return 2
    return check_progress_doc(source_doc=args.source_doc, progress_doc=args.progress_doc)


def _run_inventory(args: argparse.Namespace) -> int:
    source_text = _read_text(args.source_doc)
    endpoints = _dedupe_preserve_order(iter_api_endpoints_from_reference_doc(source_text))
    rendered = render_inventory_markdown(endpoints, source_doc_rel=str(args.source_doc.relative_to(REPO_ROOT)))

    if args.check_inventory:
        if not args.inventory_out.exists():
            sys.stderr.write(f"inventory file not found: {args.inventory_out}\n")
            return 2

        current = _read_text(args.inventory_out)
        if current != rendered:
            _print_unified_diff(
                from_text=current,
                to_text=rendered,
                from_name=str(args.inventory_out),
                to_name="(generated)",
            )
            return 1

        sys.stdout.write("OK: inventory file is up to date\n")
        return 0

    _write_text(args.inventory_out, rendered)
    sys.stdout.write(f"Wrote inventory: {args.inventory_out.relative_to(REPO_ROOT)} ({len(endpoints)} endpoints)\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-doc", type=Path, default=DEFAULT_SOURCE_DOC)
    parser.add_argument("--inventory-out", type=Path, default=DEFAULT_INVENTORY_OUT)
    parser.add_argument("--progress-doc", type=Path, default=DEFAULT_PROGRESS_DOC)

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-inventory", action="store_true", help="fail if inventory file is out of date")
    mode.add_argument("--check-progress", action="store_true", help="fail if progress doc endpoint set drifted")

    args = parser.parse_args(argv)

    if not args.source_doc.exists():
        sys.stderr.write(f"source doc not found: {args.source_doc}\n")
        return 2

    if args.check_progress:
        return _run_check_progress(args)

    return _run_inventory(args)


if __name__ == "__main__":
    raise SystemExit(main())

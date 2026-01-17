#!/usr/bin/env python3
"""(Deprecated) 生成 `/api/v1` API contract 索引画布, 并校验 contract 覆盖率.

Deprecated:
- API contract SSOT 已迁移到 Obsidian Markdown: `docs/Obsidian/API/**-api-contract.md`
- 标准: `docs/Obsidian/standards/doc/api-contract-markdown-standards.md`

本脚本仅用于历史遗留的 `.canvas` contract 维护与审计.

约定:
- 每个域 contract: `docs/Obsidian/canvas/**/**-api-contract.canvas`
- API v1 索引: `docs/Obsidian/canvas/api-v1-api-contract.canvas` (仅索引, 不承载全量 endpoint 表)

用法:
  # 生成索引(覆盖写入)
  uv run python scripts/dev/openapi/export_api_contract_canvas.py \\
    --output docs/Obsidian/canvas/api-v1-api-contract.canvas

  # 校验覆盖率(不写入)
  uv run python scripts/dev/openapi/export_api_contract_canvas.py --check
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import create_app
from app.settings import Settings

CANVAS_ROOT = Path("docs/Obsidian/canvas")
INDEX_CANVAS_FILENAME = "api-v1-api-contract.canvas"
REQUIRED_ENDPOINTS_TABLE_HEADER = ["method", "path", "purpose", "idempotency", "pagination", "notes"]


@dataclass(frozen=True)
class OpenApiOperation:
    method: str
    path: str
    tags: tuple[str, ...]
    summary: str


def _load_openapi_spec(*, endpoint: str) -> dict[str, Any]:
    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)

    client = app.test_client()
    resp = client.get(endpoint)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAPI endpoint 返回非 200: {resp.status_code}")

    spec = resp.get_json()
    if not isinstance(spec, dict):
        raise RuntimeError("OpenAPI endpoint 未返回 JSON object")

    if "openapi" not in spec and "swagger" not in spec:
        raise ValueError("OpenAPI spec 缺少 `openapi` 或 `swagger` 字段")

    return spec


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _canonicalize_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _iter_contract_canvases(*, canvas_root: Path, index_filename: str) -> list[Path]:
    return sorted(
        [
            path
            for path in canvas_root.glob("**/*-api-contract.canvas")
            if path.is_file() and path.name != index_filename
        ]
    )


def _extract_operations_from_markdown(text: str, *, base_path: str) -> tuple[set[tuple[str, str]], list[list[str]]]:
    operations: set[tuple[str, str]] = set()
    table_headers: list[list[str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        header_line = lines[i].strip()
        if not header_line.startswith("|"):
            i += 1
            continue

        header = [cell.strip() for cell in header_line.strip("|").split("|")]
        normalized = [cell.lower() for cell in header]
        if "method" not in normalized or "path" not in normalized:
            i += 1
            continue

        method_idx = normalized.index("method")
        path_idx = normalized.index("path")
        table_headers.append(normalized)

        # Skip separator row if present.
        i += 2
        while i < len(lines):
            row_line = lines[i].strip()
            if not row_line.startswith("|"):
                break
            row = [cell.strip() for cell in row_line.strip("|").split("|")]
            if len(row) <= max(method_idx, path_idx):
                i += 1
                continue
            method = row[method_idx].upper()
            path = row[path_idx].strip()
            if not method or not path:
                i += 1
                continue
            if path.startswith("/api/"):
                full_path = path
            elif path.startswith("/"):
                full_path = f"{base_path.rstrip('/')}{path}"
            else:
                # Not a path; ignore.
                i += 1
                continue
            operations.add((method, full_path))
            i += 1

        continue
    return operations, table_headers


def _extract_operations_from_canvas(path: Path, *, base_path: str) -> tuple[set[tuple[str, str]], list[list[str]]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"canvas 文件不是 JSON object: {path}")

    operations: set[tuple[str, str]] = set()
    table_headers: list[list[str]] = []
    for node in obj.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("type") != "text":
            continue
        text = node.get("text")
        if not isinstance(text, str):
            continue
        extracted_ops, extracted_headers = _extract_operations_from_markdown(text, base_path=base_path)
        operations |= extracted_ops
        table_headers.extend(extracted_headers)

    return operations, table_headers


def _extract_group_label(path: Path) -> str:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return path.stem
    for node in obj.get("nodes", []):
        if (
            isinstance(node, dict)
            and node.get("type") == "group"
            and isinstance(node.get("label"), str)
            and node["label"]
        ):
            return node["label"]
    return path.stem


def _build_openapi_operations(spec: dict[str, Any]) -> dict[tuple[str, str], OpenApiOperation]:
    base_path = str(spec.get("basePath", "/api/v1")).rstrip("/")
    paths = spec.get("paths", {})
    if not isinstance(paths, dict) or not paths:
        raise ValueError("OpenAPI spec 的 `paths` 为空或不是 object")

    operations: dict[tuple[str, str], OpenApiOperation] = {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method == "parameters":
                continue
            if not isinstance(op, dict):
                continue
            method_upper = str(method).upper()
            full_path = f"{base_path}{path}"
            tags = tuple(str(tag) for tag in (op.get("tags") or []) if isinstance(tag, str))
            summary = str(op.get("summary") or "").strip()
            operations[(method_upper, full_path)] = OpenApiOperation(
                method=method_upper,
                path=full_path,
                tags=tags,
                summary=summary,
            )
    return operations


def _generate_index_canvas(
    *,
    spec: dict[str, Any],
    contract_paths: list[Path],
    per_file_valid_ops: dict[Path, set[tuple[str, str]]],
) -> dict[str, Any]:
    base_path = str(spec.get("basePath", "/api/v1")).rstrip("/")
    openapi_ops = _build_openapi_operations(spec)

    index_rows: list[tuple[str, str, str, int]] = []
    for contract_path in contract_paths:
        label = _extract_group_label(contract_path)
        ops = per_file_valid_ops.get(contract_path, set())
        # Derive tags from OpenAPI by looking up ops in spec.
        tags: set[str] = set()
        for op in ops:
            match = openapi_ops.get(op)
            if match:
                tags |= set(match.tags)
        rel = contract_path.relative_to(CANVAS_ROOT.parent).as_posix()  # "canvas/xxx/yyy.canvas"
        index_rows.append((label, rel, ",".join(sorted(tags)), len(ops)))

    index_rows.sort(key=lambda r: r[0].lower())

    lines = [
        "## Contracts",
        "",
        "| Domain | Canvas | Tags | Operations |",
        "| --- | --- | --- | --- |",
    ]
    for label, rel, tags_csv, count in index_rows:
        lines.append(
            f"| {_escape_table_cell(label)} | `{_escape_table_cell(rel)}` | {_escape_table_cell(tags_csv)} | {count} |"
        )
    index_table = "\n".join(lines) + "\n"

    # Layout: a group + intro + table + file nodes.
    nodes: list[dict[str, Any]] = [
        {
            "id": "f106000000000001",
            "type": "group",
            "x": -80,
            "y": -80,
            "width": 2560,
            "height": 1400,
            "color": "2",
            "label": "API v1 - API Contract Index",
        },
        {
            "id": "f106000000000002",
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 2420,
            "height": 220,
            "color": "2",
            "text": (
                "## 说明\n\n"
                f"- (Legacy) 本画布仅作为 `{base_path}/**` contract canvas 的索引\n"
                "- SSOT: `docs/Obsidian/API/api-v1-api-contract.md`\n"
                f"- Schema 细节以 OpenAPI 为准: `{base_path}/openapi.json`\n"
                "- (Legacy) 更新索引: `uv run python scripts/dev/openapi/export_api_contract_canvas.py "
                f"--output {CANVAS_ROOT.as_posix()}/{INDEX_CANVAS_FILENAME}`\n"
                "- (Legacy) 校验覆盖率: `uv run python scripts/dev/openapi/export_api_contract_canvas.py --check`\n\n"
                "Source: `docs/Obsidian/standards/doc/api-contract-markdown-standards.md`\n"
            ),
        },
        {
            "id": "f106000000000003",
            "type": "text",
            "x": 0,
            "y": 260,
            "width": 2420,
            "height": 420,
            "color": "3",
            "text": index_table,
        },
    ]

    # Add file nodes for navigation.
    cols = 4
    node_width = 560
    node_height = 240
    gap_x = 60
    gap_y = 40
    start_x = 0
    start_y = 720

    for idx, (_label, rel, _tags, _count) in enumerate(index_rows):
        col = idx % cols
        row = idx // cols
        x = start_x + col * (node_width + gap_x)
        y = start_y + row * (node_height + gap_y)
        nodes.append(
            {
                "id": f"f106000000001{idx:03d}",
                "type": "file",
                "x": x,
                "y": y,
                "width": node_width,
                "height": node_height,
                "color": "6",
                "file": rel,
            }
        )

    # Resize group height to fit the last node.
    group = nodes[0]
    last = nodes[-1]
    needed_height = int(last["y"]) + int(last["height"]) - int(group["y"]) + 80
    group["height"] = max(int(group["height"]), needed_height)

    return {"nodes": nodes, "edges": []}


def _check_coverage(
    *,
    spec: dict[str, Any],
    contract_paths: list[Path],
    base_path: str,
) -> tuple[
    set[tuple[str, str]],
    dict[Path, set[tuple[str, str]]],
    dict[Path, set[tuple[str, str]]],
    dict[Path, list[list[str]]],
    dict[tuple[str, str], list[Path]],
]:
    openapi_ops = _build_openapi_operations(spec)
    expected = set(openapi_ops.keys())

    per_file_ops: dict[Path, set[tuple[str, str]]] = {}
    per_file_extra_ops: dict[Path, set[tuple[str, str]]] = {}
    per_file_table_headers: dict[Path, list[list[str]]] = {}
    owners: dict[tuple[str, str], list[Path]] = defaultdict(list)
    observed: set[tuple[str, str]] = set()

    for contract_path in contract_paths:
        ops, table_headers = _extract_operations_from_canvas(contract_path, base_path=base_path)
        valid = {op for op in ops if op in expected}
        extra = {op for op in ops if op not in expected}
        per_file_ops[contract_path] = valid
        per_file_extra_ops[contract_path] = extra
        per_file_table_headers[contract_path] = table_headers
        for op in valid:
            owners[op].append(contract_path)
        observed |= valid

    missing = expected - observed
    return missing, per_file_ops, per_file_extra_ops, per_file_table_headers, owners


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=CANVAS_ROOT / INDEX_CANVAS_FILENAME,
        help=f"输出索引 canvas 文件路径(默认: {CANVAS_ROOT.as_posix()}/{INDEX_CANVAS_FILENAME})",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="/api/v1/openapi.json",
        help="OpenAPI JSON 路由(默认: /api/v1/openapi.json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="校验 contract 覆盖率 + 索引是否最新(不写入文件)",
    )
    args = parser.parse_args()

    spec = _load_openapi_spec(endpoint=args.endpoint)
    base_path = str(spec.get("basePath", "/api/v1")).rstrip("/")
    contract_paths = _iter_contract_canvases(canvas_root=CANVAS_ROOT, index_filename=INDEX_CANVAS_FILENAME)

    missing, per_file_valid_ops, per_file_extra_ops, per_file_table_headers, owners = _check_coverage(
        spec=spec, contract_paths=contract_paths, base_path=base_path
    )

    if args.check:
        schema_violations = []
        for canvas_path, headers in per_file_table_headers.items():
            # Only validate tables that look like endpoints tables (contain method+path).
            if not headers:
                schema_violations.append((canvas_path, "missing endpoints table", []))
                continue
            for header in headers:
                if header != REQUIRED_ENDPOINTS_TABLE_HEADER:
                    schema_violations.append((canvas_path, "non-standard header", header))
        if schema_violations:
            print("API contract 校验失败: endpoints 表格格式不符合标准")
            for canvas_path, reason, header in sorted(schema_violations, key=lambda x: x[0].as_posix()):
                rel = canvas_path.relative_to(CANVAS_ROOT).as_posix()
                if reason == "missing endpoints table":
                    print(f"\n[{rel}] missing endpoints table header: {REQUIRED_ENDPOINTS_TABLE_HEADER}")
                    continue
                print(f"\n[{rel}] non-standard header: {header}")
                print(f"  expected: {REQUIRED_ENDPOINTS_TABLE_HEADER}")
            return 1

        extra_items = [(path, extra_ops) for path, extra_ops in per_file_extra_ops.items() if extra_ops]
        if extra_items:
            print("API contract 校验失败: 发现 OpenAPI 中不存在的 endpoints(可能已过期或拼写不一致)")
            for canvas_path, extra_ops in sorted(extra_items, key=lambda x: x[0].as_posix()):
                rel = canvas_path.relative_to(CANVAS_ROOT).as_posix()
                print(f"\n[{rel}] extra={len(extra_ops)}")
                for method, path in sorted(extra_ops)[:200]:
                    print(f"  - {method:6} {path}")
            return 1

        if missing:
            openapi_ops = _build_openapi_operations(spec)
            missing_by_tag: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
            for op_key in sorted(missing):
                op = openapi_ops[op_key]
                tag = op.tags[0] if op.tags else "untagged"
                missing_by_tag[tag].append((op.method, op.path, op.summary))

            print("API contract 覆盖率校验失败: 发现缺失 endpoints")
            for tag in sorted(missing_by_tag.keys()):
                print(f"\n[{tag}] missing={len(missing_by_tag[tag])}")
                for method, path, summary in missing_by_tag[tag]:
                    print(f"  - {method:6} {path}  # {summary}")
            return 1

        # Index freshness check (compare canonical JSON).
        expected_index = _generate_index_canvas(
            spec=spec, contract_paths=contract_paths, per_file_valid_ops=per_file_valid_ops
        )
        output_path: Path = args.output
        if not output_path.exists():
            print(f"索引 canvas 不存在: {output_path}")
            print(
                "请先生成: uv run python scripts/dev/openapi/export_api_contract_canvas.py "
                f"--output {output_path.as_posix()}"
            )
            return 1
        current = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise RuntimeError("索引 canvas 文件不是 JSON object")
        if _canonicalize_json(current) != _canonicalize_json(expected_index):
            print("索引 canvas 已过期, 请重新生成:")
            print(
                "  uv run python scripts/dev/openapi/export_api_contract_canvas.py "
                f"--output {output_path.as_posix()}"
            )
            return 1

        # Duplicate warnings (do not fail).
        duplicates = sorted([(op, files) for op, files in owners.items() if len(files) > 1], key=lambda x: x[0])
        if duplicates:
            print("\nWarning: 发现重复收录的 endpoints (建议收敛到单一 contract canvas):")
            for (method, path), files in duplicates[:50]:
                joined = ", ".join(p.relative_to(CANVAS_ROOT).as_posix() for p in files)
                print(f"  - {method:6} {path}  => {joined}")

        return 0

    # Generate index.
    index_canvas = _generate_index_canvas(
        spec=spec, contract_paths=contract_paths, per_file_valid_ops=per_file_valid_ops
    )
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index_canvas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

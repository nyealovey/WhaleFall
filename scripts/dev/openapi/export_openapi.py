#!/usr/bin/env python3
"""导出 WhaleFall `/api/v1` OpenAPI/Swagger JSON 并做最小校验.

用法:
  python3 scripts/dev/openapi/export_openapi.py --output openapi.json
  python3 scripts/dev/openapi/export_openapi.py --check
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from app import create_app
from app.settings import Settings


def _validate_spec(spec: dict[str, Any]) -> None:
    if not isinstance(spec, dict):
        raise ValueError("OpenAPI spec 必须为 JSON object")

    if "openapi" not in spec and "swagger" not in spec:
        raise ValueError("OpenAPI spec 缺少 `openapi` 或 `swagger` 字段")

    info = spec.get("info")
    if not isinstance(info, dict) or not info.get("title") or not info.get("version"):
        raise ValueError("OpenAPI spec 缺少 `info.title` / `info.version`")

    paths = spec.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise ValueError("OpenAPI spec 的 `paths` 为空")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi.json"),
        help="输出文件路径(默认: ./openapi.json)",
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
        help="仅校验(不写入文件)，校验失败返回非 0",
    )
    args = parser.parse_args()

    settings = Settings.load()
    settings = replace(settings, api_v1_enabled=True)
    app = create_app(init_scheduler_on_start=False, settings=settings)

    client = app.test_client()
    resp = client.get(args.endpoint)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAPI endpoint 返回非 200: {resp.status_code}")

    spec = resp.get_json()
    if not isinstance(spec, dict):
        raise RuntimeError("OpenAPI endpoint 未返回 JSON object")

    _validate_spec(spec)

    if args.check:
        return 0

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

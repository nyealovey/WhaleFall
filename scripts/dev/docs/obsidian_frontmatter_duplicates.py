#!/usr/bin/env python3
"""Check Obsidian frontmatter duplicates (title/aliases).

This script scans Obsidian notes under:
  - docs/Obsidian/standards
  - docs/Obsidian/reference

It reports duplicates for:
  - YAML frontmatter `title`
  - YAML frontmatter `aliases` (list)

Usage:
  python3 scripts/dev/docs/obsidian_frontmatter_duplicates.py

Exit codes:
  0: no duplicates found
  1: duplicates found
  2: invalid arguments or unexpected error
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _parse_frontmatter(text: str) -> dict[str, object]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}

    fm = match.group(1)
    lines = fm.splitlines()

    data: dict[str, object] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue

        if re.match(r"^\s", line):
            i += 1
            continue

        if ":" not in line:
            i += 1
            continue

        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()

        if raw == "":
            items: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if not nxt.strip():
                    j += 1
                    continue
                if not re.match(r"^\s+-\s+", nxt):
                    break
                item = re.sub(r"^\s+-\s+", "", nxt).strip()
                if (item.startswith('"') and item.endswith('"')) or (
                    item.startswith("'") and item.endswith("'")
                ):
                    item = item[1:-1]
                items.append(item)
                j += 1
            data[key] = items
            i = j
            continue

        value = raw
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        data[key] = value
        i += 1

    return data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Obsidian frontmatter title/aliases duplicates.")
    parser.add_argument(
        "--roots",
        nargs="+",
        default=["docs/Obsidian/standards", "docs/Obsidian/reference"],
        help="Roots to scan (default: standards + reference).",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    roots = [Path(p) for p in args.roots]
    for root in roots:
        if not root.exists():
            print(f"[ERROR] root not found: {root}", file=sys.stderr)
            return 2

    records: list[dict[str, object]] = []
    for root in roots:
        for path in sorted(root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                text = path.read_text(errors="ignore")
            fm = _parse_frontmatter(text)
            records.append(
                {
                    "path": str(path),
                    "title": fm.get("title"),
                    "aliases": fm.get("aliases", []),
                },
            )

    alias_to_paths: dict[str, list[str]] = defaultdict(list)
    title_to_paths: dict[str, list[str]] = defaultdict(list)

    for rec in records:
        aliases = rec["aliases"] if isinstance(rec["aliases"], list) else []
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                alias_to_paths[alias.strip()].append(rec["path"])  # type: ignore[arg-type]

        title = rec["title"]
        if isinstance(title, str) and title.strip():
            title_to_paths[title.strip()].append(rec["path"])  # type: ignore[arg-type]

    dup_aliases = {a: ps for a, ps in alias_to_paths.items() if len(ps) > 1}
    dup_titles = {t: ps for t, ps in title_to_paths.items() if len(ps) > 1}

    print("Duplicate aliases:", len(dup_aliases))
    for alias, paths in sorted(dup_aliases.items(), key=lambda x: (-len(x[1]), x[0])):
        print("-", alias, "->", paths)

    print("Duplicate titles:", len(dup_titles))
    for title, paths in sorted(dup_titles.items(), key=lambda x: (-len(x[1]), x[0])):
        print("-", title, "->", paths)

    if dup_aliases or dup_titles:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


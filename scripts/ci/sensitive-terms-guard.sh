#!/usr/bin/env bash
# Guard against reintroducing blocked organization/domain terms.
#
# Usage:
#   ./scripts/ci/sensitive-terms-guard.sh
#   ./scripts/ci/sensitive-terms-guard.sh --history

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="current"

if [[ "${1:-}" == "--history" ]]; then
  MODE="history"
  shift
fi

if (( $# != 0 )); then
  echo "Usage: $0 [--history]" >&2
  exit 2
fi

BLOCKED_ASCII="$(printf '%s%s' 'ch' 'int')"
BLOCKED_ZH="$(printf '\346\255\243\346\263\260')"

if [[ "${MODE}" == "current" ]]; then
  cd "${ROOT_DIR}"
  if git grep -n -I -i -e "${BLOCKED_ASCII}" -e "${BLOCKED_ZH}" -- .; then
    echo "" >&2
    echo "Blocked terms found in tracked files." >&2
    exit 1
  fi

  echo "Sensitive terms guard passed for tracked files."
  exit 0
fi

python3 - "${ROOT_DIR}" <<'PY'
from __future__ import annotations

import subprocess
import sys
from collections import defaultdict

root = sys.argv[1]
needle_ascii = b"ch" + b"int"
needle_zh = bytes([0xE6, 0xAD, 0xA3, 0xE6, 0xB3, 0xB0])
max_reported = 50

rev_list = subprocess.check_output(
    ["git", "rev-list", "--objects", "--all"],
    cwd=root,
    text=True,
    errors="replace",
)

paths_by_oid: dict[str, set[str]] = defaultdict(set)
oids: list[str] = []
for raw_line in rev_list.splitlines():
    if not raw_line:
        continue
    if " " in raw_line:
        oid, path = raw_line.split(" ", 1)
        paths_by_oid[oid].add(path)
    else:
        oid = raw_line
    oids.append(oid)

unique_oids = list(dict.fromkeys(oids))
if not unique_oids:
    print("Sensitive terms guard passed for history.")
    raise SystemExit(0)

batch_check = subprocess.run(
    ["git", "cat-file", "--batch-check=%(objecttype) %(objectname) %(objectsize)"],
    cwd=root,
    input="\n".join(unique_oids) + "\n",
    text=True,
    capture_output=True,
    check=True,
)

blob_oids: list[str] = []
for raw_line in batch_check.stdout.splitlines():
    parts = raw_line.split(" ", 2)
    if len(parts) == 3 and parts[0] == "blob":
        blob_oids.append(parts[1])

proc = subprocess.Popen(
    ["git", "cat-file", "--batch"],
    cwd=root,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)
assert proc.stdin is not None
assert proc.stdout is not None

match_count = 0
try:
    for oid in blob_oids:
        proc.stdin.write(f"{oid}\n".encode("ascii"))
        proc.stdin.flush()

        header = proc.stdout.readline()
        if not header:
            break
        header_parts = header.decode("ascii", errors="replace").strip().split(" ")
        if len(header_parts) < 3 or header_parts[1] != "blob":
            continue

        size = int(header_parts[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)

        if needle_ascii in data.lower() or needle_zh in data:
            match_count += 1
            if match_count <= max_reported:
                paths = sorted(paths_by_oid.get(oid, []))
                path_label = ", ".join(paths[:5]) if paths else "(no path)"
                print(f"{oid}\t{path_label}")
finally:
    proc.stdin.close()
    proc.wait()

if match_count:
    if match_count > max_reported:
        print(f"... and {match_count - max_reported} more matching blob(s)")
    print("Blocked terms found in reachable history.", file=sys.stderr)
    raise SystemExit(1)

print("Sensitive terms guard passed for history.")
PY

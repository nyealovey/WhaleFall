#!/usr/bin/env bash
# Services -> Repository 门禁（drift guard）：
# 锁定 services 内的 `.query` / `db.session.query/execute` 命中 baseline，禁止新增（允许减少）。
#
# 说明：
# - services-layer-standards 约定 Service 的数据访问与 Query 组装应下沉到 Repository。
# - 当前仓库仍存在历史命中，因此采用 baseline 方式先“禁止新增”，再逐步清理。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="app/services"
TARGET_DIR_ABS="${ROOT_DIR}/${TARGET_DIR}"
BASELINE_FILE="${ROOT_DIR}/scripts/ci/baselines/services-repository-enforcement.txt"

RG_BIN="${RG_BIN:-rg}"
UPDATE_BASELINE="false"

if [[ "${1:-}" == "--update-baseline" ]]; then
  UPDATE_BASELINE="true"
  shift
fi

if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "未检测到 python3 命令，请先安装 Python 3。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR_ABS}" ]]; then
  echo "未找到 ${TARGET_DIR_ABS}，跳过检查。"
  exit 0
fi

PATTERN="\\.query\\b|db\\.session\\.(query|execute)\\b"

current_file="$(mktemp)"
baseline_sorted_file="$(mktemp)"
trap 'rm -f "${current_file}" "${baseline_sorted_file}"' EXIT

cd "${ROOT_DIR}"

python3 - <<'PY' 3< <("${RG_BIN}" -n --hidden --type py "${PATTERN}" "${TARGET_DIR}" || true) >"${current_file}"
import re
import os
import sys

def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()

for raw in os.fdopen(3):
    raw = raw.rstrip("\n")
    if not raw:
        continue
    # rg -n format: path:line:content (content may contain ':')
    parts = raw.split(":", 2)
    if len(parts) < 3:
        continue
    path, _lineno, content = parts
    print(f"{path}\t{normalize_whitespace(content)}")
PY

LC_ALL=C sort "${current_file}" -o "${current_file}"
current_count="$(wc -l <"${current_file}" | tr -d '[:space:]')"

if [[ "${UPDATE_BASELINE}" == "true" ]]; then
  mkdir -p "$(dirname "${BASELINE_FILE}")"
  cp "${current_file}" "${BASELINE_FILE}"
  echo "已更新 baseline：${BASELINE_FILE}"
  echo "当前命中数：${current_count}"
  exit 0
fi

if [[ ! -f "${BASELINE_FILE}" ]]; then
  echo "未找到 baseline 文件：${BASELINE_FILE}" >&2
  echo "请先运行：./scripts/ci/services-repository-enforcement-guard.sh --update-baseline" >&2
  exit 1
fi

LC_ALL=C sort "${BASELINE_FILE}" >"${baseline_sorted_file}"

new_hits="$(comm -13 "${baseline_sorted_file}" "${current_file}" || true)"
if [[ -n "${new_hits}" ]]; then
  echo "检测到新增的 services 直查库/query 命中（禁止新增）：" >&2
  echo "${new_hits}" >&2
  echo "" >&2
  echo "请将查询与数据访问下沉到 Repository，由 Service 负责业务编排。" >&2
  echo "参考：" >&2
  echo "- docs/Obsidian/standards/backend/layer/services-layer-standards.md" >&2
  echo "- docs/Obsidian/standards/backend/layer/repository-layer-standards.md" >&2
  exit 1
fi

echo "检查通过：当前命中数 ${current_count}（允许减少，禁止新增）。"

#!/usr/bin/env bash
# db.session.commit 漂移门禁（services）：锁定 baseline，禁止新增命中（允许减少）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="app/services"
BASELINE_FILE="${ROOT_DIR}/scripts/ci/baselines/db-session-commit-services.txt"

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

PATTERN="db\\.session\\.commit\\("

current_file="$(mktemp)"
baseline_sorted_file="$(mktemp)"
trap 'rm -f "${current_file}" "${baseline_sorted_file}"' EXIT

cd "${ROOT_DIR}"

# rg 无命中会返回 1，这里视为“当前 0 命中”
("${RG_BIN}" -n --hidden --type py "${PATTERN}" "${TARGET_DIR}" || true) | LC_ALL=C sort >"${current_file}"

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
  echo "请先运行：./scripts/ci/db-session-commit-services-drift-guard.sh --update-baseline" >&2
  exit 1
fi

LC_ALL=C sort "${BASELINE_FILE}" >"${baseline_sorted_file}"

new_hits="$(comm -13 "${baseline_sorted_file}" "${current_file}" || true)"
if [[ -n "${new_hits}" ]]; then
  echo "检测到新增的 db.session.commit 命中（禁止新增）：" >&2
  echo "${new_hits}" >&2
  echo "" >&2
  echo "请将事务提交收敛到事务边界入口（safe_route_call / tasks / worker / scripts），services 仅使用 flush。" >&2
  echo "参考：docs/changes/refactor/002-backend-write-operation-boundary-plan.md" >&2
  exit 1
fi

echo "检查通过：当前命中数 ${current_count}（允许减少，禁止新增）。"


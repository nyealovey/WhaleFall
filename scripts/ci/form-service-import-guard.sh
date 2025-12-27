#!/usr/bin/env bash
# form_service import 门禁: 禁止继续引用已移除的 app.services.form_service

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令, 请先安装 ripgrep, 或设置 RG_BIN 指向可执行文件." >&2
  exit 1
fi

cd "${ROOT_DIR}"

PATTERN='^\\s*(from\\s+app\\.services\\.form_service\\b|import\\s+app\\.services\\.form_service\\b)'
hits="$("${RG_BIN}" -n --hidden --type py "${PATTERN}" app tests scripts || true)"

if [[ -z "${hits}" ]]; then
  echo "✅ form_service import 门禁通过: 未发现对 app.services.form_service 的 import."
  exit 0
fi

echo "检测到对已移除模块 app.services.form_service 的 import (禁止):" >&2
echo "${hits}" >&2
echo "" >&2
echo "请将调用迁移到对应的 write services / form handlers (参考: docs/changes/refactor/003-backend-form-service-removal-plan.md)."
exit 1

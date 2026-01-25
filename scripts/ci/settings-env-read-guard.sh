#!/usr/bin/env bash
# Settings 门禁：禁止在 settings/入口脚本之外读取环境变量（os.environ.get/os.getenv）
#
# 参考：
# - docs/Obsidian/standards/backend/gate/layer/settings-layer.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/settings-env-read-guard.sh

Checks:
  - app/**/*.py 禁止出现 os.environ.get/os.getenv（允许：app/settings.py）
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

TARGET_DIR="app"
ALLOW_FILES_REGEX='^app/settings\.py:'
PATTERN='\\bos\\.(?:environ\\.get|getenv)\\('

hits="$("${RG_BIN}" -n --hidden --type py --glob "!app/settings.py" -- "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${hits}" ]]; then
  # 双保险：如果未来调整 glob 排除逻辑，仍按 allowlist 过滤一次
  unexpected="$(echo "${hits}" | grep -v -E "${ALLOW_FILES_REGEX}" || true)"
  if [[ -n "${unexpected}" ]]; then
    echo "检测到 settings 之外的环境变量读取（禁止）：" >&2
    echo "${unexpected}" >&2
    echo "" >&2
    echo "请将配置读取/默认值/校验集中到 app/settings.py。" >&2
    echo "参考：docs/Obsidian/standards/backend/gate/layer/settings-layer.md" >&2
    exit 1
  fi
fi

echo "✅ settings env 读取门禁通过：未发现 settings 之外的 os.environ.get/os.getenv。"


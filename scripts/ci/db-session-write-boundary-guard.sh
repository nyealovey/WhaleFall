#!/usr/bin/env bash
# 全局写操作边界门禁：组合 routes 写门禁 + services commit 漂移门禁 + commit allowlist 门禁

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

./scripts/ci/db-session-route-write-guard.sh
./scripts/ci/db-session-commit-services-drift-guard.sh
./scripts/ci/db-session-commit-allowlist-guard.sh

echo "✅ 全局写操作边界门禁通过。"


#!/usr/bin/env bash
# UI standards audit 门禁：聚合 UI 防回归检查（JS 颜色字面量 / 模板固定 id / Grid.js 直用等）
#
# 参考：
# - docs/Obsidian/standards/ui/guide/color.md
# - docs/Obsidian/standards/ui/gate/component-dom-id-scope.md
# - docs/Obsidian/standards/ui/gate/grid.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/ui-standards-audit-guard.sh

Requires:
  - python3
  - node (and repo node_modules with espree available)
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "未检测到 python3，无法执行 UI standards audit 门禁检查。" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "未检测到 node，无法执行 UI standards audit 门禁检查。" >&2
  exit 1
fi

"${PY_BIN}" - <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment
from jinja2.visitor import NodeVisitor


def _repo_root() -> Path:
    return Path.cwd()


def _run_node_json(script: str, args: list[str]) -> object:
    completed = subprocess.run(
        ["node", "-", *args],
        input=script,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise AssertionError(
            "Node 脚本执行失败:\n"
            f"exit={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}\n",
        )

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            "Node 输出不是合法 JSON:\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}\n",
        ) from exc


class _TemplateDataTokenVisitor(NodeVisitor):
    def __init__(self, token: str) -> None:
        super().__init__()
        self.token = token
        self.hits: list[tuple[int, str]] = []

    def visit_TemplateData(self, node):  # type: ignore[override]
        data = getattr(node, "data", "") or ""
        if self.token in data:
            lineno = int(getattr(node, "lineno", 0) or 0)
            self.hits.append((lineno, data.strip()))


def _fail(msg: str) -> None:
    raise AssertionError(msg)


def _check_no_hardcoded_hex_colors_in_project_js() -> None:
    repo_root = _repo_root()
    scan_root = repo_root / "app/static/js"
    vendor_root = repo_root / "app/static/vendor"

    payload = _run_node_json(
        r"""
const fs = require("fs");
const path = require("path");
const espree = require("espree");

function walkDir(dir, out) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkDir(full, out);
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".js")) {
      out.push(full);
    }
  }
}

function isHexColorLiteral(value) {
  if (typeof value !== "string") return false;
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(value);
}

function visit(node, fn) {
  if (!node || typeof node !== "object") return;
  fn(node);
  for (const key of Object.keys(node)) {
    const child = node[key];
    if (Array.isArray(child)) {
      for (const item of child) visit(item, fn);
    } else if (child && typeof child === "object" && typeof child.type === "string") {
      visit(child, fn);
    }
  }
}

const repoRoot = process.cwd();
const scanRoot = process.argv[2];
const vendorRoot = process.argv[3];

const files = [];
walkDir(scanRoot, files);

const hits = [];
const parseErrors = [];

for (const file of files) {
  const rel = path.relative(repoRoot, file).split(path.sep).join("/");
  if (vendorRoot && rel.startsWith(path.relative(repoRoot, vendorRoot).split(path.sep).join("/") + "/")) {
    continue;
  }

  const code = fs.readFileSync(file, "utf8");
  let ast;
  try {
    ast = espree.parse(code, {
      ecmaVersion: "latest",
      sourceType: "script",
      loc: true,
    });
  } catch (error) {
    parseErrors.push({
      file: rel,
      message: String(error && error.message ? error.message : error),
    });
    continue;
  }

  visit(ast, (node) => {
    if (node.type === "Literal" && isHexColorLiteral(node.value)) {
      hits.push({ file: rel, line: node.loc.start.line, value: node.value });
      return;
    }
    if (node.type === "TemplateElement" && isHexColorLiteral(node.value && node.value.cooked)) {
      hits.push({ file: rel, line: node.loc.start.line, value: node.value.cooked });
      return;
    }
  });
}

process.stdout.write(JSON.stringify({ hits, parseErrors }));
        """.strip(),
        args=[str(scan_root), str(vendor_root)],
    )

    parse_errors = payload.get("parseErrors", []) if isinstance(payload, dict) else []
    if parse_errors:
        _fail(
            "JS 解析失败（espree）:\n"
            + "\n".join(f"- {item.get('file')}: {item.get('message')}" for item in parse_errors[:20])
        )

    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    if hits:
        _fail(
            "发现硬编码 HEX 颜色字面量:\n"
            + "\n".join(f"- {item.get('file')}:{item.get('line')} {item.get('value')}" for item in hits[:50])
        )


def _check_instances_detail_no_legacy_instance_stat_card() -> None:
    repo_root = _repo_root()

    rel_path = "app/templates/instances/detail.html"
    template_text = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
    env = Environment()
    ast = env.parse(template_text)
    visitor = _TemplateDataTokenVisitor("instance-stat-card")
    visitor.visit(ast)
    if visitor.hits:
        _fail(
            f"{rel_path} 仍包含 instance-stat-card:\n"
            + "\n".join(f"- {rel_path}:{lineno} {snippet[:120]}" for lineno, snippet in visitor.hits[:20])
        )

    rel_path = "app/static/css/pages/instances/detail.css"
    css_text = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
    forbidden_tokens = [
        ".instance-stat-card",
        ".instance-stat-card__label",
        ".instance-stat-card__value",
    ]
    hits = [token for token in forbidden_tokens if token in css_text]
    if hits:
        _fail(f"{rel_path} 仍包含私有指标卡样式 token: {', '.join(hits)}")


def _check_templates_no_fixed_component_ids() -> None:
    repo_root = _repo_root()
    env = Environment()

    rel_path = "app/templates/components/filters/macros.html"
    template_text = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
    ast = env.parse(template_text)
    tokens = [
        'id="instance"',
        'for="instance"',
        'id="database"',
        'for="database"',
    ]
    hits: list[str] = []
    for token in tokens:
        visitor = _TemplateDataTokenVisitor(token)
        visitor.visit(ast)
        for lineno, snippet in visitor.hits:
            hits.append(f"- {rel_path}:{lineno} {token} {snippet[:120]}")
    if hits:
        _fail("发现 filters 宏内固定 id/for:\n" + "\n".join(hits[:30]))

    rel_path = "app/templates/components/ui/danger_confirm_modal.html"
    template_text = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
    ast = env.parse(template_text)
    tokens = [
        'id="dangerConfirmModal"',
        "dangerConfirmModalLabel",
    ]
    hits = []
    for token in tokens:
        visitor = _TemplateDataTokenVisitor(token)
        visitor.visit(ast)
        for lineno, snippet in visitor.hits:
            hits.append(f"- {rel_path}:{lineno} {token} {snippet[:120]}")
    if hits:
        _fail("发现 danger_confirm_modal 内固定 id:\n" + "\n".join(hits[:30]))


def _check_no_direct_gridjs_grid_in_views_modules() -> None:
    repo_root = _repo_root()
    scan_root = repo_root / "app/static/js/modules/views"

    payload = _run_node_json(
        r"""
const fs = require("fs");
const path = require("path");
const espree = require("espree");

function walkDir(dir, out) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkDir(full, out);
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".js")) {
      out.push(full);
    }
  }
}

function visit(node, fn) {
  if (!node || typeof node !== "object") return;
  fn(node);
  for (const key of Object.keys(node)) {
    const child = node[key];
    if (Array.isArray(child)) {
      for (const item of child) visit(item, fn);
    } else if (child && typeof child === "object" && typeof child.type === "string") {
      visit(child, fn);
    }
  }
}

function isGridjsGridMember(expr) {
  return (
    expr &&
    expr.type === "MemberExpression" &&
    !expr.computed &&
    expr.object &&
    expr.object.type === "Identifier" &&
    expr.object.name === "gridjs" &&
    expr.property &&
    expr.property.type === "Identifier" &&
    expr.property.name === "Grid"
  );
}

function collectGridAliases(ast) {
  const aliases = new Set();
  visit(ast, (node) => {
    if (node.type !== "VariableDeclarator") return;
    const id = node.id;
    const init = node.init;
    if (!init) return;

    // const Grid = gridjs.Grid;
    if (id && id.type === "Identifier" && isGridjsGridMember(init)) {
      aliases.add(id.name);
      return;
    }

    // const { Grid } = gridjs;
    if (
      id &&
      id.type === "ObjectPattern" &&
      init.type === "Identifier" &&
      init.name === "gridjs"
    ) {
      for (const prop of id.properties || []) {
        if (!prop || prop.type !== "Property") continue;
        if (prop.key && prop.key.type === "Identifier" && prop.key.name === "Grid") {
          if (prop.value && prop.value.type === "Identifier") {
            aliases.add(prop.value.name);
          }
        }
      }
    }
  });
  return aliases;
}

const repoRoot = process.cwd();
const scanRoot = process.argv[2];

const files = [];
walkDir(scanRoot, files);

const hits = [];
const parseErrors = [];

for (const file of files) {
  const rel = path.relative(repoRoot, file).split(path.sep).join("/");
  const code = fs.readFileSync(file, "utf8");
  let ast;
  try {
    ast = espree.parse(code, {
      ecmaVersion: "latest",
      sourceType: "script",
      loc: true,
    });
  } catch (error) {
    parseErrors.push({
      file: rel,
      message: String(error && error.message ? error.message : error),
    });
    continue;
  }

  const aliases = collectGridAliases(ast);

  visit(ast, (node) => {
    if (node.type !== "NewExpression") return;
    const callee = node.callee;
    if (isGridjsGridMember(callee)) {
      hits.push({ file: rel, line: node.loc.start.line, form: "new gridjs.Grid" });
      return;
    }
    if (callee && callee.type === "Identifier" && aliases.has(callee.name)) {
      hits.push({ file: rel, line: node.loc.start.line, form: `new ${callee.name}` });
    }
  });
}

process.stdout.write(JSON.stringify({ hits, parseErrors }));
        """.strip(),
        args=[str(scan_root)],
    )

    parse_errors = payload.get("parseErrors", []) if isinstance(payload, dict) else []
    if parse_errors:
        _fail(
            "JS 解析失败（espree）:\n" + "\n".join(f"- {item.get('file')}: {item.get('message')}" for item in parse_errors[:20])
        )

    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    if hits:
        _fail(
            "发现 views 内直接 new gridjs.Grid:\n"
            + "\n".join(f"- {item.get('file')}:{item.get('line')} {item.get('form')}" for item in hits[:50])
        )


def main() -> int:
    failures: list[str] = []
    checks = [
        _check_no_hardcoded_hex_colors_in_project_js,
        _check_instances_detail_no_legacy_instance_stat_card,
        _check_templates_no_fixed_component_ids,
        _check_no_direct_gridjs_grid_in_views_modules,
    ]
    for check in checks:
        try:
            check()
        except AssertionError as exc:
            failures.append(f"[{check.__name__}] {exc}")

    if failures:
        sys.stderr.write("UI standards audit 门禁失败：\n\n")
        sys.stderr.write("\n\n".join(failures) + "\n")
        return 1

    sys.stdout.write("✅ UI standards audit 门禁通过。\n")
    return 0


raise SystemExit(main())
PY


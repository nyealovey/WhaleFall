#!/usr/bin/env python3
"""CRUD 场景烟雾测试脚本。.

该脚本通过配置化方式对指定资源完成“新增-查询-更新-删除”全链路校验，
默认调用正在运行的 Flask 服务接口：

1. 先获取 CSRF 令牌并完成登录；
2. 根据 YAML 场景配置逐步发送请求，自动替换变量、写入上下文；
3. 校验 HTTP 状态码以及关键 JSON 字段；
4. 将每一步的结果打印为中文报告，失败时返回非零状态码。

示例用法：

    python scripts/crud_smoke.py \
        --scenario scripts/crud_scenarios.example.yml \
        --base-url http://127.0.0.1:5001 \
        --username admin --password secret

可以配合 `--dry-run` 先验证配置是否正确，再连接真实环境执行。
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*}}")

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger("scripts.crud_smoke")


class CrudScenarioError(RuntimeError):
    """表示 CRUD 场景执行失败的异常。."""


@dataclass
class StepResult:
    """单个步骤的执行结果。."""

    scenario: str
    step: str
    success: bool
    elapsed_ms: float
    message: str
    status_code: int | None = None


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    """从 YAML/JSON 文件加载场景定义。."""
    if not path.exists():
        msg = f"找不到场景文件: {path}"
        raise FileNotFoundError(msg)

    text = path.read_text(encoding="utf-8")
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:  # pragma: no cover - YAML 解析错误提示
        msg = f"解析场景文件失败: {exc}"
        raise ValueError(msg) from exc

    if not isinstance(parsed, Mapping) or "scenarios" not in parsed:
        msg = "场景文件需包含 'scenarios' 顶层键"
        raise ValueError(msg)

    scenarios = parsed["scenarios"]
    if not isinstance(scenarios, list):
        msg = "'scenarios' 必须是列表"
        raise ValueError(msg)
    return [s for s in scenarios if isinstance(s, Mapping)]


def render_template(value: Any, context: Mapping[str, Any]) -> Any:
    """递归替换模板占位符。."""
    if isinstance(value, str) and "{{" in value and "}}" in value:
        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in context:
                msg = f"未定义的变量: {key}"
                raise KeyError(msg)
            return str(context[key])

        rendered = TEMPLATE_PATTERN.sub(_replace, value)
        if "{{" in rendered and "}}" in rendered:
            msg = f"存在未解析模板片段: {rendered}"
            raise KeyError(msg)
        return rendered
    if isinstance(value, list):
        return [render_template(item, context) for item in value]
    if isinstance(value, dict):
        return {k: render_template(v, context) for k, v in value.items()}
    return value


def extract_value(payload: Any, path: str) -> Any:
    """通过简单路径语法从 JSON 结构中提取值。."""
    if not path:
        return payload
    current = payload
    for raw_token in path.split("."):
        if raw_token == "":
            continue
        current = _walk_token(current, raw_token)
    return current


def _walk_token(current: Any, token: str) -> Any:
    """处理 `foo[0]` 这类 token。."""
    while token:
        if "[" in token:
            attr, remainder = token.split("[", 1)
            if attr:
                current = current[attr]
            idx_str, rest = remainder.split("]", 1)
            idx = int(idx_str)
            current = current[idx]
            token = rest
            token = token.removeprefix(".")
            continue
        current = current[token]
        token = ""
    return current


class CrudSmokeRunner:
    """根据配置执行 CRUD 场景的执行器。."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        scenario_path: Path,
        filters: set[str] | None = None,
        dry_run: bool = False,
        timeout: float = 20.0,
        stop_on_failure: bool = False,
        login_path: str = "/auth/api/login",
        csrf_path: str = "/auth/api/csrf-token",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.timeout = timeout
        self.stop_on_failure = stop_on_failure
        self.login_path = login_path
        self.csrf_path = csrf_path
        self.dry_run = dry_run
        self.scenario_path = scenario_path
        self.scenario_filters = filters or set()
        self.results: list[StepResult] = []
        self.current_csrf: str | None = None
        self.scenarios = load_scenarios(scenario_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> None:
        """执行所有匹配条件的场景。."""
        if not self.dry_run:
            self._login()
        for scenario in self.scenarios:
            name = str(scenario.get("name") or "unnamed")
            if self.scenario_filters and name not in self.scenario_filters:
                continue
            if not scenario.get("enabled", True):
                LOGGER.info("⚪️ 跳过场景 `%s`（enabled=false）", name)
                continue
            LOGGER.info("")
            LOGGER.info("▶️  开始执行场景: %s", name)
            description = scenario.get("description")
            if description:
                LOGGER.info("    说明: %s", description)
            context = self._build_base_context(scenario)
            steps = scenario.get("steps", [])
            for step in steps:
                self._run_step(name, step, context)
                if self.stop_on_failure and self.results and not self.results[-1].success:
                    msg = "检测到失败，已根据参数中止执行"
                    raise CrudScenarioError(msg)

    # ------------------------------------------------------------------
    # Core Steps
    # ------------------------------------------------------------------
    def _login(self) -> None:
        """拉取 CSRF 并完成登录。."""
        token = self._refresh_csrf_token()
        payload = {"username": self.username, "password": self.password}
        url = f"{self.base_url}{self.login_path}"
        headers = {"X-CSRFToken": token, "Accept": "application/json"}
        resp = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        self._ensure_success_response(resp, expected_status=200, step_name="登录")
        self._refresh_csrf_token()
        LOGGER.info("✅ 登录成功，开始执行 CRUD 场景")

    def _run_step(self, scenario_name: str, step_cfg: Mapping[str, Any], context: MutableMapping[str, Any]) -> None:
        """执行单个步骤。."""
        step_name = str(step_cfg.get("name") or f"step_{len(self.results) + 1}")
        if not step_cfg.get("enabled", True):
            LOGGER.info("  ⚪️ 跳过步骤 %s（enabled=false）", step_name)
            return

        method = str(step_cfg.get("method", "GET")).upper()
        path = render_template(str(step_cfg.get("path", "/")), context)
        full_url = f"{self.base_url}{path}"
        params = render_template(step_cfg.get("params"), context)
        json_payload = render_template(step_cfg.get("json"), context)
        headers = {"Accept": "application/json"}
        custom_headers = render_template(step_cfg.get("headers") or {}, context)
        if isinstance(custom_headers, Mapping):
            headers.update({str(k): str(v) for k, v in custom_headers.items()})

        request_kwargs: dict[str, Any] = {
            "method": method,
            "url": full_url,
            "headers": headers,
            "timeout": self.timeout,
        }
        if params:
            request_kwargs["params"] = params
        if json_payload is not None:
            request_kwargs["json"] = json_payload

        if method not in SAFE_METHODS and not self.dry_run:
            headers["X-CSRFToken"] = self._refresh_csrf_token()

        start = time.perf_counter()
        if self.dry_run:
            self._apply_fake_store(step_cfg, context, step_name)
            elapsed = (time.perf_counter() - start) * 1000
            message = f"[DRY-RUN] 将调用 {method} {path}"
            LOGGER.info("  💡 %s", message)
            self.results.append(
                StepResult(
                    scenario=scenario_name,
                    step=step_name,
                    success=True,
                    elapsed_ms=elapsed,
                    message=message,
                    status_code=None,
                ),
            )
            return

        try:
            response = self.session.request(**request_kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            expected_status = int(step_cfg.get("expect_status", 200))
            self._ensure_success_response(
                response,
                expected_status=expected_status,
                step_name=step_name,
                expect_json=step_cfg.get("expect_json"),
                store=step_cfg.get("store"),
                context=context,
            )
            message = f"{method} {path} ✅"
            self.results.append(
                StepResult(
                    scenario=scenario_name,
                    step=step_name,
                    success=True,
                    elapsed_ms=elapsed,
                    message=message,
                    status_code=response.status_code,
                ),
            )
            LOGGER.info("  ✅ %s: %s (%.1f ms)", step_name, response.status_code, elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            error_message = f"{method} {path} 失败: {exc}"
            self.results.append(
                StepResult(
                    scenario=scenario_name,
                    step=step_name,
                    success=False,
                    elapsed_ms=elapsed,
                    message=error_message,
                ),
            )
            LOGGER.exception("  ❌ %s: %s", step_name, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_csrf_token(self) -> str:
        """调用 CSRF 接口获取最新 token。."""
        url = f"{self.base_url}{self.csrf_path}"
        resp = self.session.get(url, timeout=self.timeout)
        payload = self._safe_json(resp)
        try:
            token = str(payload["data"]["csrf_token"])
        except Exception as exc:
            msg = "CSRF 接口返回异常，缺少 data.csrf_token"
            raise ValueError(msg) from exc
        self.current_csrf = token
        return token

    def _ensure_success_response(
        self,
        response: requests.Response,
        *,
        expected_status: int,
        step_name: str,
        expect_json: Mapping[str, Any] | None = None,
        store: Mapping[str, str] | None = None,
        context: MutableMapping[str, Any] | None = None,
    ) -> None:
        """校验状态码与 JSON 内容。."""
        if response.status_code != expected_status:
            msg = f"期望状态码 {expected_status}，实得 {response.status_code}，响应体: {response.text}"
            raise AssertionError(
                msg,
            )

        if not expect_json and not store:
            return

        payload = self._safe_json(response)

        if expect_json:
            for raw_path, expected in expect_json.items():
                actual = extract_value(payload, str(raw_path))
                rendered_expected = render_template(expected, context or {}) if context else expected
                if actual != rendered_expected:
                    msg = f"字段 {raw_path} 校验失败，期望 {rendered_expected}，实得 {actual}"
                    raise AssertionError(
                        msg,
                    )

        if store and context is not None:
            for alias, raw_path in store.items():
                context[str(alias)] = extract_value(payload, str(raw_path))

    def _safe_json(self, response: requests.Response) -> Any:
        """解析 JSON，失败时抛出详细异常。."""
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            msg = f"响应并非 JSON：{response.text[:200]}"
            raise ValueError(msg) from exc

    def _build_base_context(self, scenario: Mapping[str, Any]) -> MutableMapping[str, Any]:
        """构建每个场景的基础上下文。."""
        from datetime import datetime
        from uuid import uuid4

        ctx: MutableMapping[str, Any] = {
            "uuid": uuid4().hex,
            "rand_suffix": uuid4().hex[:8],
            "timestamp": datetime.utcnow().isoformat(),
        }
        extra_vars = scenario.get("variables")
        if isinstance(extra_vars, Mapping):
            for key, value in extra_vars.items():
                ctx[str(key)] = render_template(value, ctx)
        return ctx

    def _apply_fake_store(
        self,
        step_cfg: Mapping[str, Any],
        context: MutableMapping[str, Any],
        step_name: str,
    ) -> None:
        """将 store 字段转换为假的占位符，便于 dry-run 渲染。."""
        store_cfg = step_cfg.get("store")
        if not isinstance(store_cfg, Mapping):
            return
        for alias in store_cfg:
            context[str(alias)] = f"<{step_name}.{alias}>"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    """解析命令行参数。."""
    parser = argparse.ArgumentParser(description="CRUD 自动化测试脚本")
    parser.add_argument("--scenario", type=Path, required=True, help="场景配置文件 (YAML/JSON)")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001", help="服务基础地址")
    parser.add_argument("--username", help="登录用户名")
    parser.add_argument("--password", help="登录密码")
    parser.add_argument("--only", nargs="*", metavar="NAME", help="只执行指定场景名称")
    parser.add_argument("--timeout", type=float, default=20.0, help="请求超时时间（秒）")
    parser.add_argument("--stop-on-failure", action="store_true", help="遇到失败立即停止")
    parser.add_argument("--dry-run", action="store_true", help="仅打印步骤，不发送请求")
    parser.add_argument("--login-path", default="/auth/api/login", help="登录接口路径")
    parser.add_argument("--csrf-path", default="/auth/api/csrf-token", help="CSRF 接口路径")
    return parser.parse_args(list(argv)[1:])


def main(argv: Iterable[str]) -> int:
    """脚本入口。."""
    args = parse_args(argv)
    filters = set(args.only or [])

    if not args.dry_run and (not args.username or not args.password):
        LOGGER.error("❌ 未提供用户名/密码，无法执行登录")
        return 2

    runner = CrudSmokeRunner(
        base_url=args.base_url,
        username=args.username or "",
        password=args.password or "",
        scenario_path=args.scenario,
        filters=filters,
        dry_run=args.dry_run,
        timeout=args.timeout,
        stop_on_failure=args.stop_on_failure,
        login_path=args.login_path,
        csrf_path=args.csrf_path,
    )

    try:
        runner.run()
    except CrudScenarioError as exc:
        LOGGER.exception("❌ %s", exc)
    except Exception as exc:
        LOGGER.exception("❌ 执行过程中出现异常: %s", exc)

    failed = [result for result in runner.results if not result.success]

    LOGGER.info("")
    LOGGER.info("==== 执行汇总 ====")
    for result in runner.results:
        status = "✅" if result.success else "❌"
        code_part = f"[{result.status_code}]" if result.status_code is not None else ""
        LOGGER.info(
            "%s %s :: %s %s 耗时 %.1f ms - %s",
            status,
            result.scenario,
            result.step,
            code_part,
            result.elapsed_ms,
            result.message,
        )

    if failed:
        LOGGER.error("")
        LOGGER.error("❌ 共 %d 个步骤失败，请查看上方日志。", len(failed))
        return 1

    LOGGER.info("")
    LOGGER.info("✅ 所有步骤执行完成，无失败。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

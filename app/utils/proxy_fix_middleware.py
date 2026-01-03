"""鲸落 - 代理头部解析中间件.

用于在反向代理（例如 Nginx）场景下安全解析 `X-Forwarded-*` 头部,让 Flask
能够得到真实客户端 IP 与协议等信息.
"""

from __future__ import annotations

from collections.abc import Iterable
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment

from werkzeug.middleware.proxy_fix import ProxyFix


class TrustedProxyFix:
    """仅对可信代理来源请求应用 ProxyFix 的 WSGI 中间件.

    说明:
    - `ProxyFix` 本身会信任传入的 `X-Forwarded-*` 头,若应用端口被直连暴露
      （例如误把 Gunicorn 端口对外开放）,攻击者可伪造这些头部导致 IP/协议识别失真.
    - 本中间件通过 `REMOTE_ADDR` 白名单,仅对来自可信代理地址的请求启用 `ProxyFix`,
      从而降低直连场景下的风险.

    Args:
        app: 原始 WSGI 应用.
        trusted_proxy_ips: 可信代理 IP 集合,仅当 `REMOTE_ADDR` 命中时才解析 `X-Forwarded-*`.
        x_for: 可信 `X-Forwarded-For` 代理层数.
        x_proto: 可信 `X-Forwarded-Proto` 代理层数.
        x_host: 可信 `X-Forwarded-Host` 代理层数.
        x_port: 可信 `X-Forwarded-Port` 代理层数.
        x_prefix: 可信 `X-Forwarded-Prefix` 代理层数.

    """

    def __init__(
        self,
        app: WSGIApplication,
        *,
        trusted_proxy_ips: set[str],
        x_for: int = 0,
        x_proto: int = 0,
        x_host: int = 0,
        x_port: int = 0,
        x_prefix: int = 0,
    ) -> None:
        """初始化中间件并配置 ProxyFix."""
        self._app = app
        self._trusted_proxy_ips = trusted_proxy_ips
        self._proxy_fix = ProxyFix(
            app,
            x_for=x_for,
            x_proto=x_proto,
            x_host=x_host,
            x_port=x_port,
            x_prefix=x_prefix,
        )

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        """WSGI 调用入口,仅对可信代理应用 ProxyFix."""
        remote_addr = environ.get("REMOTE_ADDR")
        if isinstance(remote_addr, str) and remote_addr in self._trusted_proxy_ips:
            return self._proxy_fix(environ, start_response)
        return self._app(environ, start_response)

"""HTTP 头常量。

仅保留当前代码路径实际使用的 header 名称，避免“顺手”堆叠未用常量。
"""


class HttpHeaders:
    """HTTP 头名称常量（避免魔法字符串）。"""

    CONTENT_TYPE = "Content-Type"
    AUTHORIZATION = "Authorization"
    USER_AGENT = "User-Agent"

    # 代理和转发
    X_FORWARDED_PROTO = "X-Forwarded-Proto"
    X_FORWARDED_SSL = "X-Forwarded-Ssl"

    # CSRF 头部标识（仅键名，无任何凭据信息）
    X_CSRF_TOKEN = "X-CSRFToken"

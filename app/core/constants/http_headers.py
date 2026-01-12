"""HTTP头常量.

定义常用的HTTP头名称,避免魔法字符串.
"""

from __future__ import annotations

from typing import Final

CSRF_HEADER_NAMES: Final[tuple[str, str]] = (
    "X-CSRFToken",
    "X-XSRF-TOKEN",
)


class HttpHeaders:
    """HTTP头常量.

    定义标准和自定义的HTTP头名称.
    """

    # 标准HTTP头

    # 通用头
    CONTENT_TYPE = "Content-Type"
    CONTENT_LENGTH = "Content-Length"
    CONTENT_ENCODING = "Content-Encoding"
    CONTENT_LANGUAGE = "Content-Language"
    CONTENT_DISPOSITION = "Content-Disposition"

    # 请求头
    ACCEPT = "Accept"
    ACCEPT_LANGUAGE = "Accept-Language"
    ACCEPT_ENCODING = "Accept-Encoding"
    AUTHORIZATION = "Authorization"
    USER_AGENT = "User-Agent"
    REFERER = "Referer"
    HOST = "Host"
    ORIGIN = "Origin"

    # 响应头
    LOCATION = "Location"
    SERVER = "Server"
    SET_COOKIE = "Set-Cookie"
    CACHE_CONTROL = "Cache-Control"
    EXPIRES = "Expires"
    ETAG = "ETag"
    LAST_MODIFIED = "Last-Modified"

    # 跨域相关
    ACCESS_CONTROL_ALLOW_ORIGIN = "Access-Control-Allow-Origin"
    ACCESS_CONTROL_ALLOW_METHODS = "Access-Control-Allow-Methods"
    ACCESS_CONTROL_ALLOW_HEADERS = "Access-Control-Allow-Headers"
    ACCESS_CONTROL_ALLOW_CREDENTIALS = "Access-Control-Allow-Credentials"
    ACCESS_CONTROL_MAX_AGE = "Access-Control-Max-Age"

    # CSRF 头部标识,仅作为键名,无任何凭据信息.
    X_CSRF_TOKEN = CSRF_HEADER_NAMES[0]
    X_XSRF_TOKEN = CSRF_HEADER_NAMES[1]

    # 速率限制
    X_RATE_LIMIT_LIMIT = "X-RateLimit-Limit"
    X_RATE_LIMIT_REMAINING = "X-RateLimit-Remaining"
    X_RATE_LIMIT_RESET = "X-RateLimit-Reset"

    # 代理和转发
    X_FORWARDED_FOR = "X-Forwarded-For"
    X_FORWARDED_PROTO = "X-Forwarded-Proto"
    X_FORWARDED_HOST = "X-Forwarded-Host"
    X_FORWARDED_SSL = "X-Forwarded-Ssl"
    X_REAL_IP = "X-Real-IP"

    # API相关
    X_API_KEY = "X-API-Key"
    X_API_VERSION = "X-API-Version"
    X_REQUEST_ID = "X-Request-ID"
    X_CORRELATION_ID = "X-Correlation-ID"

    # 其他自定义头
    X_FRAME_OPTIONS = "X-Frame-Options"
    X_CONTENT_TYPE_OPTIONS = "X-Content-Type-Options"
    X_XSS_PROTECTION = "X-XSS-Protection"

    # Content-Type常用值

    # 常用的Content-Type值
    class ContentType:
        """Content-Type常用值."""

        # 文本类型
        TEXT_PLAIN = "text/plain"
        TEXT_HTML = "text/html"
        TEXT_CSS = "text/css"
        TEXT_JAVASCRIPT = "text/javascript"
        TEXT_XML = "text/xml"
        TEXT_CSV = "text/csv"

        # 应用类型
        APPLICATION_JSON = "application/json"
        APPLICATION_XML = "application/xml"
        APPLICATION_PDF = "application/pdf"
        APPLICATION_ZIP = "application/zip"
        APPLICATION_OCTET_STREAM = "application/octet-stream"
        APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"

        # 多部分类型
        MULTIPART_FORM_DATA = "multipart/form-data"
        MULTIPART_MIXED = "multipart/mixed"

        # 图片类型
        IMAGE_PNG = "image/png"
        IMAGE_JPEG = "image/jpeg"
        IMAGE_GIF = "image/gif"
        IMAGE_SVG = "image/svg+xml"
        IMAGE_WEBP = "image/webp"

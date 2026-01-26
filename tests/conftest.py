# tests/conftest.py
"""全局测试配置.

IMPORTANT: 环境变量必须在文件最顶部设置，在任何 import 之前。
这是唯一设置测试环境变量的地方，测试文件中不要重复设置。
"""

import os

# ============================================================
# 环境变量设置（必须在所有 import 之前）
# ============================================================
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CACHE_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-key")
os.environ.setdefault("FLASK_ENV", "testing")

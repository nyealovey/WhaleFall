# tests/integration/
"""集成测试模块.

需要真实数据库（PostgreSQL）和 Redis 连接。
运行前请确保：
1. docker compose up -d postgres redis
2. 设置正确的 DATABASE_URL 环境变量
"""

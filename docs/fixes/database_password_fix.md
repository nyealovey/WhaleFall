# 数据库密码修复说明

## 问题描述

启动应用时出现数据库密码认证失败错误：

```
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432 failed: FATAL: password authentication failed for user "whalefall_user"
```

## 问题原因

`.env` 文件中的数据库密码与Docker容器中的实际密码不匹配：

- **Docker容器密码**: `WhaleFall2024!`
- **.env文件密码**: `xAfbY3VRSlPmHY8ell3iUYmXZqcCt9iz`

## 解决方案

更新 `.env` 文件中的数据库连接URL，使用正确的密码：

```bash
# 修复前
DATABASE_URL=postgresql+psycopg://whalefall_user:xAfbY3VRSlPmHY8ell3iUYmXZqcCt9iz@localhost:5432/whalefall_dev

# 修复后
DATABASE_URL=postgresql+psycopg://whalefall_user:WhaleFall2024!@localhost:5432/whalefall_dev
```

## 修复命令

```bash
cd /Users/shiyijiufei/WahleFall/TaifishingV4
sed -i '' 's/xAfbY3VRSlPmHY8ell3iUYmXZqcCt9iz/WhaleFall2024!/g' .env
```

## 验证方法

1. 检查Docker容器密码：
   ```bash
   docker exec whalefall_postgres_dev env | grep POSTGRES
   ```

2. 测试数据库连接：
   ```bash
   docker exec whalefall_postgres_dev psql -U whalefall_user -d whalefall_dev -c "SELECT 1;"
   ```

3. 启动应用：
   ```bash
   ./start_uv.sh
   ```

4. 验证应用启动：
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "http://localhost:5001/"
   # 应该返回 302 (重定向到登录页面)
   ```

## 注意事项

- `.env` 文件被 `.gitignore` 忽略，不会提交到版本控制
- 每个开发环境需要确保 `.env` 文件中的密码与Docker容器密码一致
- 生产环境使用不同的密码配置

## 相关文件

- `.env` - 环境变量配置文件
- `docker-compose.dev.yml` - Docker开发环境配置
- `start_uv.sh` - 应用启动脚本

## 修复时间

2025-09-27 07:21

## 修复状态

✅ 已修复并验证

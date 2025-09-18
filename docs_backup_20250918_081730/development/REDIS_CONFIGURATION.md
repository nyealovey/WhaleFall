# Redis配置管理

## 概述

泰摸鱼吧使用Redis作为缓存和速率限制的后端存储。本文档说明如何正确配置和管理Redis连接。

## 配置方式

### 1. 环境变量配置（推荐）

在 `.env` 文件中设置以下环境变量：

```bash
# Redis配置
REDIS_URL=redis://:Taifish2024!@localhost:6379/0
CACHE_REDIS_URL=redis://:Taifish2024!@localhost:6379/0
CACHE_TYPE=redis
CACHE_DEFAULT_TIMEOUT=300
```

**注意**: 项目使用 `.env` 文件作为环境配置，通过 `load_dotenv()` 默认行为加载。

### 2. 配置文件配置

在 `app/config.py` 中的 `DefaultConfig` 类中设置默认值：

```python
class DefaultConfig:
    REDIS_URL = "redis://:Taifish2024!@localhost:6379/0"
    CACHE_REDIS_URL = "redis://:Taifish2024!@localhost:6379/0"
    CACHE_TYPE = "redis"
    CACHE_DEFAULT_TIMEOUT = 300
```

## Docker Redis配置

### Docker Compose配置

```yaml
redis:
  image: redis:7-alpine
  container_name: taifish_redis_dev
  restart: unless-stopped
  command: redis-server --appendonly yes --requirepass Taifish2024! --maxmemory 128mb --maxmemory-policy allkeys-lru
  volumes:
    - redis_dev_data:/data
    - ./docker/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
  ports:
    - "6379:6379"
  networks:
    - taifish_dev_network
  healthcheck:
    test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
    interval: 10s
    timeout: 3s
    retries: 5
```

### Redis配置文件

Redis配置文件位于 `docker/redis/redis.conf`，包含以下关键配置：

```conf
# 网络配置
bind 0.0.0.0
port 6379

# 认证配置
requirepass Taifish2024!

# 持久化配置
appendonly yes
appendfsync everysec

# 内存配置
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## 连接测试

### 1. 使用脚本测试

```bash
# 运行环境设置脚本
./setup_env.sh

# 测试应用启动
uv run python -c "from app import create_app; app = create_app()"
```

### 2. 手动测试Redis连接

```bash
# 使用Docker Redis
docker exec taifish_redis_dev redis-cli -a Taifish2024! ping

# 使用本地Redis客户端
redis-cli -a Taifish2024! ping
```

## 常见问题

### 1. Redis连接失败

**问题**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**解决方案**:
1. 检查Redis服务是否运行：`docker ps | grep redis`
2. 检查端口是否被占用：`lsof -i :6379`
3. 验证密码是否正确：`redis-cli -a Taifish2024! ping`

### 2. 密码认证失败

**问题**: `redis.exceptions.AuthenticationError: AUTH failed`

**解决方案**:
1. 确认Redis密码配置：`requirepass Taifish2024!`
2. 检查环境变量中的密码：`echo $REDIS_URL`
3. 验证URL格式：`redis://:password@host:port/db`

### 3. 端口冲突

**问题**: `Redis server can't start: bind: Address already in use`

**解决方案**:
1. 停止本地Redis服务：`brew services stop redis`
2. 杀死占用进程：`lsof -i :6379` 然后 `kill <PID>`
3. 使用Docker Redis：`docker-compose up redis`

## 安全配置

### 1. 密码安全

- 使用强密码：`Taifish2024!`
- 定期更换密码
- 不在代码中硬编码密码

### 2. 网络安全

- 绑定到本地接口：`bind 127.0.0.1`
- 使用防火墙限制访问
- 启用TLS加密（生产环境）

### 3. 数据安全

- 启用持久化：`appendonly yes`
- 定期备份数据
- 设置内存限制：`maxmemory 256mb`

## 监控和维护

### 1. 健康检查

```bash
# 检查Redis状态
docker exec taifish_redis_dev redis-cli info server

# 检查内存使用
docker exec taifish_redis_dev redis-cli info memory

# 检查连接数
docker exec taifish_redis_dev redis-cli info clients
```

### 2. 日志监控

```bash
# 查看Redis日志
docker logs taifish_redis_dev

# 查看应用日志
tail -f userdata/logs/app.log | grep -i redis
```

### 3. 性能优化

- 调整内存策略：`maxmemory-policy allkeys-lru`
- 优化持久化配置：`appendfsync everysec`
- 监控慢查询：`slowlog-log-slower-than 10000`

## 开发环境设置

### 1. 快速启动

```bash
# 启动Docker服务
docker-compose up -d redis

# 设置环境变量
source setup_env.sh

# 启动应用
uv run python app.py
```

### 2. 调试模式

```bash
# 启用Redis调试日志
export REDIS_DEBUG=1

# 查看Redis连接详情
uv run python -c "
import redis
r = redis.from_url('redis://:Taifish2024!@localhost:6379/0')
print('Redis连接信息:', r.info())
"
```

## 生产环境配置

### 1. 高可用配置

- 使用Redis Sentinel
- 配置主从复制
- 设置故障转移

### 2. 性能优化

- 调整内存配置
- 优化网络设置
- 启用压缩

### 3. 安全加固

- 使用TLS加密
- 配置访问控制
- 定期安全审计

## 故障排除

### 1. 连接超时

```bash
# 检查网络连通性
ping localhost

# 检查端口开放
telnet localhost 6379

# 检查防火墙
sudo ufw status
```

### 2. 内存不足

```bash
# 检查内存使用
docker exec taifish_redis_dev redis-cli info memory

# 清理过期键
docker exec taifish_redis_dev redis-cli --scan --pattern "*" | head -100 | xargs docker exec taifish_redis_dev redis-cli del
```

### 3. 数据丢失

```bash
# 检查持久化状态
docker exec taifish_redis_dev redis-cli info persistence

# 手动保存
docker exec taifish_redis_dev redis-cli bgsave
```

## 总结

正确的Redis配置对于泰摸鱼吧的正常运行至关重要。通过环境变量管理配置，可以确保开发和生产环境的一致性，同时保持配置的灵活性和安全性。

记住：
- 使用环境变量管理敏感配置
- 定期测试Redis连接
- 监控Redis性能和健康状态
- 保持配置文档的更新

# Flask应用更新指南

## 概述

本文档介绍如何使用专门的Flask更新脚本来快速更新鲸落项目的Flask应用，无需重建整个环境。

## 更新脚本

### 1. 完整更新脚本 (`update-flask-v1.0.1.sh`)

**适用场景**：生产环境、需要完整验证的更新

**特点**：
- ✅ 完整备份当前代码
- ✅ 详细的环境检查
- ✅ 自动回滚机制
- ✅ 完整的健康检查
- ✅ 保留所有数据

**使用方法**：
```bash
# 执行完整更新
./scripts/deployment/update-flask-v1.0.1.sh
```

### 2. 快速更新脚本 (`quick-update-flask.sh`)

**适用场景**：生产环境、容器重建更新

**特点**：
- ⚡ 极速更新（2-3分钟）
- ⚡ 容器重建模式
- ⚡ 销毁重建Flask容器
- ⚡ 保留数据，只更新应用
- ⚡ 快速回滚

**使用方法**：
```bash
# 执行快速更新
./scripts/deployment/quick-update-flask.sh
```

## 更新流程对比

| 步骤 | 完整更新 | 快速更新 |
|------|---------|---------|
| **环境检查** | 详细检查 | 快速检查 |
| **代码备份** | 完整备份 | Git暂存 |
| **代码更新** | Git拉取 | Git拉取 |
| **镜像构建** | 完整构建 | 完整构建 |
| **服务更新** | 停止→启动 | 销毁→重建 |
| **健康检查** | 详细验证 | 快速验证 |
| **回滚机制** | 完整回滚 | 快速回滚 |
| **预计时间** | 5-10分钟 | 2-3分钟 |

## 使用场景

### 生产环境更新

**推荐使用**：`update-flask-v1.0.1.sh`

**执行步骤**：
1. 确保服务正在运行
2. 执行更新脚本
3. 验证更新结果
4. 如有问题，自动回滚

```bash
# 1. 检查服务状态
docker compose -f docker-compose.prod.yml ps

# 2. 执行更新
./scripts/deployment/update-flask-v1.0.1.sh

# 3. 验证更新
curl http://localhost:5001/health
```

### 生产环境快速更新

**推荐使用**：`quick-update-flask.sh`

**执行步骤**：
1. 确保代码已提交
2. 执行快速更新（容器重建）
3. 验证功能正常

```bash
# 1. 提交代码
git add .
git commit -m "Update Flask app"
git push origin main

# 2. 执行快速更新
./scripts/deployment/quick-update-flask.sh

# 3. 验证功能
curl http://localhost:5001/health
```

## 更新前准备

### 1. 环境要求

- Docker 和 Docker Compose 已安装
- Git 已安装并配置
- 服务正在运行
- 环境变量已配置

### 2. 代码准备

```bash
# 确保代码已提交
git status
git add .
git commit -m "Prepare for update"

# 推送到远程仓库
git push origin main
```

### 3. 服务检查

```bash
# 检查服务状态
docker compose -f docker-compose.prod.yml ps

# 检查健康状态
curl http://localhost:5001/health

# 检查日志
docker compose -f docker-compose.prod.yml logs whalefall
```

## 更新后验证

### 1. 健康检查

```bash
# 基本健康检查
curl http://localhost:5001/health

# 详细健康检查
curl -s http://localhost:5001/health | jq .
```

### 2. 功能验证

```bash
# 检查应用首页
curl -I http://localhost/

# 检查API接口
curl http://localhost/api/health

# 检查数据库连接
curl http://localhost/health | grep -o "database.*healthy"
```

### 3. 性能监控

```bash
# 查看容器资源使用
docker stats whalefall_app_prod

# 查看应用日志
docker compose -f docker-compose.prod.yml logs -f whalefall

# 查看系统资源
htop
```

## 故障排除

### 1. 更新失败

**症状**：更新过程中出现错误

**解决方案**：
```bash
# 查看详细日志
docker compose -f docker-compose.prod.yml logs whalefall

# 手动回滚
git reset --hard HEAD~1
docker compose -f docker-compose.prod.yml restart whalefall

# 检查服务状态
docker compose -f docker-compose.prod.yml ps
```

### 2. 健康检查失败

**症状**：更新后健康检查不通过

**解决方案**：
```bash
# 检查容器状态
docker compose -f docker-compose.prod.yml ps whalefall

# 查看启动日志
docker compose -f docker-compose.prod.yml logs whalefall

# 重启服务
docker compose -f docker-compose.prod.yml restart whalefall

# 等待服务启动
sleep 30
curl http://localhost:5001/health
```

### 3. 数据库连接问题

**症状**：应用无法连接数据库

**解决方案**：
```bash
# 检查数据库状态
docker compose -f docker-compose.prod.yml ps postgres

# 检查数据库连接
docker compose -f docker-compose.prod.yml exec postgres psql -U whalefall_user -d whalefall_prod -c "SELECT 1;"

# 重启数据库
docker compose -f docker-compose.prod.yml restart postgres
```

### 4. Redis连接问题

**症状**：应用无法连接Redis

**解决方案**：
```bash
# 检查Redis状态
docker compose -f docker-compose.prod.yml ps redis

# 检查Redis连接
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# 重启Redis
docker compose -f docker-compose.prod.yml restart redis
```

## 最佳实践

### 1. 更新前

- ✅ 确保代码已测试
- ✅ 提交所有更改
- ✅ 备份重要数据
- ✅ 检查服务状态
- ✅ 通知相关人员

### 2. 更新中

- ✅ 监控更新进度
- ✅ 观察日志输出
- ✅ 准备回滚方案
- ✅ 保持网络连接

### 3. 更新后

- ✅ 验证功能正常
- ✅ 检查性能指标
- ✅ 监控错误日志
- ✅ 更新文档记录

## 自动化集成

### 1. CI/CD集成

```yaml
# .github/workflows/update-flask.yml
name: Update Flask App
on:
  push:
    branches: [main]
    paths: ['app/**', 'requirements*.txt', 'Dockerfile.prod']

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Update Flask App
        run: |
          chmod +x scripts/deployment/update-flask-v1.0.1.sh
          ./scripts/deployment/update-flask-v1.0.1.sh
```

### 2. 定时更新

```bash
# 添加到crontab
# 每天凌晨2点自动更新
0 2 * * * /path/to/scripts/deployment/update-flask-v1.0.1.sh >> /var/log/flask-update.log 2>&1
```

### 3. 监控集成

```bash
# 更新后发送通知
curl -X POST "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"text":"Flask应用更新完成: $(git rev-parse --short HEAD)"}'
```

## 总结

Flask更新脚本提供了两种更新模式：

1. **完整更新**：适用于生产环境，提供完整的备份、验证和回滚机制
2. **快速更新**：适用于开发环境，提供极速更新和零停机部署

选择合适的更新脚本，可以大大提高开发和部署效率，同时保证系统的稳定性和可靠性。

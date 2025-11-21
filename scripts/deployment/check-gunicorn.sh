#!/bin/bash

# Gunicorn 状态检查快捷脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Gunicorn 状态检查工具                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查容器是否运行
if ! docker compose -f docker-compose.prod.yml ps whalefall | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Flask容器未运行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Flask容器正在运行${NC}"
echo ""

# 1. 查看Gunicorn进程
echo -e "${BLUE}📊 Gunicorn进程状态：${NC}"
docker compose -f docker-compose.prod.yml exec whalefall ps aux | grep -E "gunicorn|PID" | grep -v grep
echo ""

# 2. 查看Gunicorn配置
echo -e "${BLUE}⚙️  Gunicorn配置文件：${NC}"
if docker compose -f docker-compose.prod.yml exec whalefall test -f /app/gunicorn.conf.py; then
    echo -e "${GREEN}✅ gunicorn.conf.py 存在${NC}"
    echo ""
    echo -e "${BLUE}配置内容：${NC}"
    docker compose -f docker-compose.prod.yml exec whalefall cat /app/gunicorn.conf.py | head -20
else
    echo -e "${YELLOW}⚠️  gunicorn.conf.py 不存在${NC}"
fi
echo ""

# 3. 查看最近的访问日志
echo -e "${BLUE}📝 最近的访问日志（最后10行）：${NC}"
if docker compose -f docker-compose.prod.yml exec whalefall test -f /var/log/gunicorn/access.log; then
    docker compose -f docker-compose.prod.yml exec whalefall tail -10 /var/log/gunicorn/access.log
else
    echo -e "${YELLOW}⚠️  访问日志文件不存在${NC}"
fi
echo ""

# 4. 查看最近的错误日志
echo -e "${BLUE}❌ 最近的错误日志（最后10行）：${NC}"
if docker compose -f docker-compose.prod.yml exec whalefall test -f /var/log/gunicorn/error.log; then
    docker compose -f docker-compose.prod.yml exec whalefall tail -10 /var/log/gunicorn/error.log
else
    echo -e "${YELLOW}⚠️  错误日志文件不存在${NC}"
fi
echo ""

# 5. 查看端口监听状态
echo -e "${BLUE}🔌 端口监听状态：${NC}"
docker compose -f docker-compose.prod.yml exec whalefall netstat -tlnp 2>/dev/null | grep -E "5001|Proto" || \
docker compose -f docker-compose.prod.yml exec whalefall ss -tlnp 2>/dev/null | grep -E "5001|Netid"
echo ""

# 6. 快捷命令提示
echo -e "${BLUE}🔧 常用命令：${NC}"
echo "  查看完整访问日志: docker compose -f docker-compose.prod.yml exec whalefall cat /var/log/gunicorn/access.log"
echo "  查看完整错误日志: docker compose -f docker-compose.prod.yml exec whalefall cat /var/log/gunicorn/error.log"
echo "  实时监控访问日志: docker compose -f docker-compose.prod.yml exec whalefall tail -f /var/log/gunicorn/access.log"
echo "  实时监控错误日志: docker compose -f docker-compose.prod.yml exec whalefall tail -f /var/log/gunicorn/error.log"
echo "  重启Flask服务: docker compose -f docker-compose.prod.yml restart whalefall"
echo ""

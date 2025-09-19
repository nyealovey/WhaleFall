# 鲸落生产环境部署 Makefile
# 提供简化的部署和管理命令

.PHONY: help install base flask all stop clean status logs backup restore update rollback

# 默认目标
help:
	@echo "🐟 鲸落生产环境部署命令"
	@echo "=================================="
	@echo "安装和配置:"
	@echo "  install     - 安装系统依赖"
	@echo "  config      - 配置环境文件"
	@echo ""
	@echo "部署命令:"
	@echo "  base        - 部署基础环境（PostgreSQL、Redis、Nginx）"
	@echo "  flask       - 部署Flask应用"
	@echo "  all         - 部署所有服务"
	@echo ""
	@echo "服务管理:"
	@echo "  start       - 启动所有服务"
	@echo "  stop        - 停止所有服务"
	@echo "  restart     - 重启所有服务"
	@echo "  status      - 查看服务状态"
	@echo ""
	@echo "日志和监控:"
	@echo "  logs        - 查看所有日志"
	@echo "  logs-base   - 查看基础环境日志"
	@echo "  logs-flask  - 查看Flask应用日志"
	@echo ""
	@echo "备份和恢复:"
	@echo "  backup      - 备份数据"
	@echo "  restore     - 恢复数据"
	@echo ""
	@echo "版本管理:"
	@echo "  update      - 更新到最新版本"
	@echo "  rollback    - 回滚到上一个版本"
	@echo ""
	@echo "维护命令:"
	@echo "  clean       - 清理Docker资源"
	@echo "  health      - 健康检查"
	@echo "  shell       - 进入Flask容器"
	@echo "=================================="

# 安装系统依赖
install:
	@echo "📦 安装系统依赖..."
	@sudo apt update
	@sudo apt install -y curl wget git docker.io docker-compose-plugin
	@sudo usermod -aG docker $$USER
	@echo "✅ 系统依赖安装完成"
	@echo "⚠️  请重新登录以使Docker组权限生效"

# 配置环境文件
config:
	@echo "⚙️  配置环境文件..."
	@if [ ! -f ".env" ]; then \
		cp env.production .env; \
		echo "✅ 环境文件已创建: .env"; \
		echo "⚠️  请编辑 .env 文件设置必要的配置"; \
	else \
		echo "✅ 环境文件已存在: .env"; \
	fi

# 部署基础环境
base:
	@echo "🏗️  部署基础环境..."
	@chmod +x scripts/deployment/deploy-base.sh
	@./scripts/deployment/deploy-base.sh

# 部署Flask应用
flask:
	@echo "🐍 部署Flask应用..."
	@chmod +x scripts/deployment/deploy-flask.sh
	@./scripts/deployment/deploy-flask.sh

# 部署所有服务
all:
	@echo "🚀 部署所有服务..."
	@chmod +x scripts/deployment/start-all.sh
	@./scripts/deployment/start-all.sh

# 启动所有服务
start:
	@echo "▶️  启动所有服务..."
	@chmod +x scripts/deployment/start-all.sh
	@./scripts/deployment/start-all.sh

# 停止所有服务
stop:
	@echo "⏹️  停止所有服务..."
	@chmod +x scripts/deployment/stop-all.sh
	@./scripts/deployment/stop-all.sh

# 重启所有服务
restart: stop start

# 查看服务状态
status:
	@echo "📊 服务状态："
	@echo "=================================="
	@echo "基础环境服务："
	@docker-compose -f docker-compose.base.yml ps
	@echo ""
	@echo "Flask应用服务："
	@docker-compose -f docker-compose.flask.yml ps
	@echo "=================================="

# 查看所有日志
logs:
	@echo "📋 查看所有日志..."
	@docker-compose -f docker-compose.base.yml logs -f &
	@docker-compose -f docker-compose.flask.yml logs -f

# 查看基础环境日志
logs-base:
	@echo "📋 查看基础环境日志..."
	@docker-compose -f docker-compose.base.yml logs -f

# 查看Flask应用日志
logs-flask:
	@echo "📋 查看Flask应用日志..."
	@docker-compose -f docker-compose.flask.yml logs -f

# 备份数据
backup:
	@echo "💾 备份数据..."
	@mkdir -p /opt/whale_fall_data/backups
	@docker-compose -f docker-compose.base.yml exec postgres pg_dump -U $$(grep POSTGRES_USER .env | cut -d'=' -f2) -d $$(grep POSTGRES_DB .env | cut -d'=' -f2) > /opt/whale_fall_data/backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ 数据备份完成"

# 恢复数据
restore:
	@echo "🔄 恢复数据..."
	@echo "请指定备份文件: make restore FILE=backup_file.sql"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ 请指定备份文件"; \
		exit 1; \
	fi
	@docker-compose -f docker-compose.base.yml exec -T postgres psql -U $$(grep POSTGRES_USER .env | cut -d'=' -f2) -d $$(grep POSTGRES_DB .env | cut -d'=' -f2) < $(FILE)
	@echo "✅ 数据恢复完成"

# 更新到最新版本
update:
	@echo "🔄 更新到最新版本..."
	@chmod +x scripts/deployment/update-version.sh
	@./scripts/deployment/update-version.sh latest

# 回滚到上一个版本
rollback:
	@echo "⏪ 回滚到上一个版本..."
	@chmod +x scripts/deployment/update-version.sh
	@./scripts/deployment/update-version.sh -r

# 清理Docker资源
clean:
	@echo "🧹 清理Docker资源..."
	@docker system prune -f
	@docker image prune -a -f
	@echo "✅ Docker资源清理完成"

# 健康检查
health:
	@echo "🏥 健康检查..."
	@echo "检查Flask应用健康状态..."
	@curl -s http://localhost:5001/health || echo "❌ Flask应用健康检查失败"
	@echo "检查Nginx代理状态..."
	@curl -s http://localhost/health || echo "❌ Nginx代理健康检查失败"
	@echo "检查PostgreSQL连接..."
	@docker-compose -f docker-compose.base.yml exec postgres pg_isready -U $$(grep POSTGRES_USER .env | cut -d'=' -f2) -d $$(grep POSTGRES_DB .env | cut -d'=' -f2) || echo "❌ PostgreSQL连接失败"
	@echo "检查Redis连接..."
	@docker-compose -f docker-compose.base.yml exec redis redis-cli ping || echo "❌ Redis连接失败"

# 进入Flask容器
shell:
	@echo "🐚 进入Flask容器..."
	@docker-compose -f docker-compose.flask.yml exec whalefall bash

# 构建Flask镜像
build:
	@echo "🔨 构建Flask镜像..."
	@docker build -t whalefall:latest .

# 查看版本信息
version:
	@echo "📋 版本信息："
	@echo "应用版本: $$(grep APP_VERSION .env | cut -d'=' -f2)"
	@echo "部署版本: $$(grep DEPLOYMENT_VERSION .env | cut -d'=' -f2)"
	@echo "Docker版本: $$(docker --version)"
	@echo "Docker Compose版本: $$(docker-compose --version)"

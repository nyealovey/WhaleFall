# 鲸落项目 Makefile
# 环境选择器和通用命令

.PHONY: help dev prod install clean

# 默认目标
help:
	@echo "🐟 鲸落项目管理命令"
	@echo "=================================="
	@echo "环境选择:"
	@echo "  dev         - 切换到开发环境"
	@echo "  prod        - 切换到生产环境"
	@echo ""
	@echo "开发环境命令:"
	@echo "  make dev help    - 查看开发环境命令"
	@echo "  make dev start   - 启动开发环境"
	@echo "  make dev stop    - 停止开发环境"
	@echo "  make dev logs    - 查看开发环境日志"
	@echo ""
	@echo "生产环境命令:"
	@echo "  make prod help   - 查看生产环境命令"
	@echo "  make prod deploy - 部署生产环境"
	@echo "  make prod start  - 启动生产环境"
	@echo "  make prod stop   - 停止生产环境"
	@echo "  make prod logs   - 查看生产环境日志"
	@echo ""
	@echo "通用命令:"
	@echo "  install     - 安装项目依赖"
	@echo "  clean       - 清理Docker资源"
	@echo "  version     - 查看版本信息"
	@echo "=================================="

# 开发环境命令
dev:
	@if [ -z "$(filter-out dev,$(MAKECMDGOALS))" ]; then \
		echo "请指定开发环境命令，例如: make dev help"; \
		echo "可用命令: help, start, stop, restart, status, logs, logs-db, logs-redis, logs-app, shell, health, init-db, init-db-quick, clean, clean-data, build, test, quality, format"; \
	else \
		$(MAKE) -f Makefile.dev $(filter-out dev,$(MAKECMDGOALS)); \
	fi

# 生产环境命令
prod:
	@if [ -z "$(filter-out prod,$(MAKECMDGOALS))" ]; then \
		echo "请指定生产环境命令，例如: make prod help"; \
		echo "可用命令: help, install, config, deploy, start, stop, restart, status, logs, logs-db, logs-redis, logs-app, shell, health, init-db, init-db-quick, backup, restore, update, rollback, clean, build, version"; \
	else \
		$(MAKE) -f Makefile.prod $(filter-out prod,$(MAKECMDGOALS)); \
	fi

# 安装项目依赖
install:
	@echo "📦 安装项目依赖..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "使用 uv 安装依赖..."; \
		uv sync; \
	else \
		echo "使用 pip 安装依赖..."; \
		pip install -r requirements.txt; \
	fi
	@echo "✅ 项目依赖安装完成"

# 清理Docker资源
clean:
	@echo "🧹 清理Docker资源..."
	@docker system prune -f
	@docker image prune -a -f
	@echo "✅ Docker资源清理完成"

# 查看版本信息
version:
	@echo "📋 版本信息："
	@echo "项目版本: $$(grep APP_VERSION .env 2>/dev/null | cut -d'=' -f2 || echo '未设置')"
	@echo "Docker版本: $$(docker --version)"
	@echo "Docker Compose版本: $$(docker-compose --version)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "UV版本: $$(uv --version)"; \
	fi

# 快速启动开发环境
dev-start:
	@echo "🚀 快速启动开发环境..."
	@$(MAKE) -f Makefile.dev start

# 快速启动生产环境
prod-start:
	@echo "🚀 快速启动生产环境..."
	@$(MAKE) -f Makefile.prod start

# 快速停止开发环境
dev-stop:
	@echo "⏹️  快速停止开发环境..."
	@$(MAKE) -f Makefile.dev stop

# 快速停止生产环境
prod-stop:
	@echo "⏹️  快速停止生产环境..."
	@$(MAKE) -f Makefile.prod stop

# 快速查看开发环境状态
dev-status:
	@echo "📊 开发环境状态..."
	@$(MAKE) -f Makefile.dev status

# 快速查看生产环境状态
prod-status:
	@echo "📊 生产环境状态..."
	@$(MAKE) -f Makefile.prod status

# 快速查看开发环境日志
dev-logs:
	@echo "📋 开发环境日志..."
	@$(MAKE) -f Makefile.dev logs

# 快速查看生产环境日志
prod-logs:
	@echo "📋 生产环境日志..."
	@$(MAKE) -f Makefile.prod logs

# 健康检查
health:
	@echo "🏥 健康检查..."
	@echo "检查开发环境..."
	@$(MAKE) -f Makefile.dev health 2>/dev/null || echo "❌ 开发环境未运行"
	@echo ""
	@echo "检查生产环境..."
	@$(MAKE) -f Makefile.prod health 2>/dev/null || echo "❌ 生产环境未运行"

# 数据库初始化（开发环境）
init-db:
	@echo "🗄️ 初始化数据库（开发环境）..."
	@$(MAKE) -f Makefile.dev init-db

# 快速数据库初始化（开发环境）
init-db-quick:
	@echo "⚡ 快速初始化数据库（开发环境）..."
	@$(MAKE) -f Makefile.dev init-db-quick

# 代码质量检查
quality:
	@echo "🔍 代码质量检查..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run ruff check .; \
		uv run mypy .; \
	else \
		ruff check .; \
		mypy .; \
	fi

# 格式化代码
format:
	@echo "🎨 格式化代码..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run black .; \
		uv run isort .; \
	else \
		black .; \
		isort .; \
	fi

# 运行测试
test:
	@echo "🧪 运行测试..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run pytest tests/; \
	else \
		python -m pytest tests/; \
	fi

# 防止目标被当作文件
%:
	@:
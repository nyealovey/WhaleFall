# Makefile for TaifishingV4 代码质量工具

.PHONY: help install check format fix lint type security clean test quality

# 默认目标
help:
	@echo "TaifishingV4 代码质量工具"
	@echo "=========================="
	@echo ""
	@echo "可用命令:"
	@echo "  install    安装开发依赖"
	@echo "  check      运行所有质量检查"
	@echo "  format     格式化代码 (Black + isort)"
	@echo "  fix        自动修复可修复的问题"
	@echo "  lint       运行 Ruff 代码检查"
	@echo "  type       运行 Mypy 类型检查"
	@echo "  security   运行 Bandit 安全扫描"
	@echo "  quality    运行快速质量检查脚本"
	@echo "  quality-full 运行完整质量检查脚本"
	@echo "  fix-code   自动修复代码问题"
	@echo "  fix-priority 按优先级修复代码问题"
	@echo "  fix-ruff   修复Ruff问题"
	@echo "  clean      清理临时文件"
	@echo "  test       运行测试"
	@echo ""

# 安装开发依赖
install:
	@echo "📦 安装开发依赖..."
	uv sync --dev
	@echo "✅ 依赖安装完成"

# 运行所有质量检查
check: format lint type security
	@echo "🎉 所有质量检查完成！"

# 格式化代码
format:
	@echo "🎨 格式化代码..."
	uv run black app/
	uv run isort app/
	@echo "✅ 代码格式化完成"

# 自动修复问题
fix:
	@echo "🔧 自动修复问题..."
	uv run ruff check app/ --fix
	uv run black app/
	uv run isort app/
	@echo "✅ 自动修复完成"

# Ruff 代码检查
lint:
	@echo "🔍 运行 Ruff 代码检查..."
	uv run ruff check app/
	@echo "✅ Ruff 检查完成"

# Mypy 类型检查
type:
	@echo "🔍 运行 Mypy 类型检查..."
	uv run mypy app/
	@echo "✅ Mypy 检查完成"

# Bandit 安全扫描
security:
	@echo "🔒 运行 Bandit 安全扫描..."
	uv run bandit -r app/ -f json -o bandit-report.json
	@echo "✅ Bandit 扫描完成"

# 快速质量检查
quality:
	@echo "⚡ 运行快速质量检查..."
	uv run python scripts/quick_check.py

# 完整质量检查
quality-full:
	@echo "🔍 运行完整质量检查..."
	uv run python scripts/quality_check.py

# 自动修复代码
fix-code:
	@echo "🔧 自动修复代码..."
	uv run python scripts/fix_code.py

# 优先级修复代码
fix-priority:
	@echo "🎯 优先级修复代码..."
	uv run python scripts/fix_priority.py

# 修复Ruff问题
fix-ruff:
	@echo "🔍 修复Ruff问题..."
	uv run python scripts/fix_ruff_only.py

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf app/__pycache__/
	rm -rf app/*/__pycache__/
	rm -rf *.pyc
	rm -rf app/*.pyc
	rm -rf app/*/*.pyc
	rm -rf bandit-report.json
	rm -rf mypy-report/
	rm -rf ruff-report.json
	@echo "✅ 清理完成"

# 运行测试
test:
	@echo "🧪 运行测试..."
	uv run pytest tests/ -v
	@echo "✅ 测试完成"

# 安装 pre-commit hooks
install-hooks:
	@echo "🪝 安装 pre-commit hooks..."
	uv run pre-commit install
	@echo "✅ pre-commit hooks 安装完成"

# 更新 pre-commit hooks
update-hooks:
	@echo "🔄 更新 pre-commit hooks..."
	uv run pre-commit autoupdate
	@echo "✅ pre-commit hooks 更新完成"

# 运行 pre-commit 检查
pre-commit:
	@echo "🪝 运行 pre-commit 检查..."
	uv run pre-commit run --all-files
	@echo "✅ pre-commit 检查完成"

# 生成报告
reports:
	@echo "📊 生成质量报告..."
	@mkdir -p reports
	uv run ruff check app/ --output-format=json > reports/ruff-report.json
	uv run mypy app/ --html-report reports/mypy-report/
	uv run bandit -r app/ -f json -o reports/bandit-report.json
	@echo "✅ 报告生成完成，查看 reports/ 目录"

# 开发环境设置
dev-setup: install install-hooks
	@echo "🚀 开发环境设置完成！"
	@echo "现在可以开始开发了。"
	@echo "提交代码时会自动运行质量检查。"

# 泰摸鱼吧 - 代码质量检查脚本

本目录包含用于代码质量检查和修复的脚本工具。

## 📁 脚本文件

### 1. `quality_check.py` - 完整质量检查
**功能**: 运行所有代码质量检查工具，包括测试
**用法**: 
```bash
uv run python scripts/quality_check.py
# 或
make quality-full
```

**检查项目**:
- ✅ Ruff 代码检查
- ✅ Black 格式化检查  
- ✅ isort 导入排序检查
- ✅ MyPy 类型检查
- ✅ Bandit 安全扫描
- ✅ pytest 测试
- ✅ 未使用导入检查
- ✅ 代码复杂度检查

### 2. `quick_check.py` - 快速质量检查
**功能**: 运行基本的代码质量检查，不包含测试
**用法**:
```bash
uv run python scripts/quick_check.py
# 或
make quality
```

**检查项目**:
- ✅ Ruff 代码检查
- ✅ Black 格式化检查
- ✅ isort 导入排序检查

### 3. `fix_code.py` - 自动修复代码
**功能**: 自动修复常见的代码质量问题
**用法**:
```bash
uv run python scripts/fix_code.py
# 或
make fix-code
```

**修复项目**:
- 🔧 Black 代码格式化
- 🔧 isort 导入排序
- 🔧 Ruff 自动修复
- 🔧 Ruff 格式化

## 🚀 快速开始

### 1. 检查代码质量
```bash
# 快速检查（推荐日常使用）
make quality

# 完整检查（包含测试）
make quality-full
```

### 2. 自动修复问题
```bash
# 自动修复代码问题
make fix-code

# 验证修复结果
make quality
```

### 3. 手动修复
```bash
# 格式化代码
uv run black .
uv run isort .

# 自动修复 Ruff 问题
uv run ruff check --fix .

# 运行 Ruff 格式化
uv run ruff format .
```

## 📊 检查报告

### 快速检查报告
- 在终端显示检查结果
- 显示通过/失败的检查数量
- 提供修复建议

### 完整检查报告
- 生成详细的 JSON 报告
- 保存到 `userdata/logs/quality_check_report.json`
- 包含所有检查的详细结果

## 🔧 配置说明

### Pre-commit 集成
脚本已集成到 `.pre-commit-config.yaml` 中，会在提交时自动运行快速检查。

### Makefile 集成
所有脚本都可通过 `make` 命令运行，详见 `Makefile` 文件。

## ⚠️ 注意事项

1. **运行环境**: 确保在项目根目录运行脚本
2. **依赖检查**: 脚本会自动检查 `uv` 是否可用
3. **超时设置**: 每个检查都有超时限制，避免长时间等待
4. **错误处理**: 脚本会捕获并显示详细的错误信息

## 🐛 故障排除

### 常见问题

1. **命令未找到**
   ```bash
   # 确保 uv 已安装
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **权限问题**
   ```bash
   # 给脚本添加执行权限
   chmod +x scripts/*.py
   ```

3. **依赖问题**
   ```bash
   # 安装开发依赖
   make install
   ```

### 获取帮助
```bash
# 查看所有可用命令
make help

# 查看脚本帮助
uv run python scripts/quality_check.py --help
```

## 📈 持续改进

这些脚本会随着项目发展持续改进，包括：
- 添加新的检查规则
- 优化检查性能
- 改进错误报告
- 增强自动修复能力

---

**维护者**: TaifishingV4 Team  
**最后更新**: 2025-09-18

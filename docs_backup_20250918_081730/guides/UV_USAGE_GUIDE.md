# UV 使用指南

## 概述

泰摸鱼吧项目已成功集成 UV 包管理器，这是一个现代化的 Python 包管理工具，比传统的 pip 快 10-100 倍。

## 安装 UV

### 方法一：使用 Homebrew（推荐）
```bash
brew install uv
```

### 方法二：使用官方安装脚本
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

## 快速开始

### 1. 启动应用
```bash
./start_uv.sh
```

### 2. 开发环境
```bash
./dev_uv.sh
# 或
make dev
```

### 3. 依赖管理
```bash
./manage_deps_uv.sh help
```

## 常用命令

### 环境管理
```bash
# 安装所有依赖
uv sync

# 安装开发依赖
uv sync --dev

# 更新依赖
uv sync --upgrade

# 清理缓存
uv cache clean
```

### 运行应用
```bash
# 直接运行
uv run python app.py

# 运行特定脚本
uv run python scripts/init_database.py

# 运行测试
uv run pytest tests/
```

### 依赖管理
```bash
# 添加依赖
uv add requests

# 添加开发依赖
uv add --dev pytest

# 移除依赖
uv remove requests

# 查看已安装的包
uv pip list

# 查看依赖树
uv pip show --tree
```

## Makefile 命令

项目提供了便捷的 Makefile 命令：

```bash
# 查看所有命令
make help

# 环境管理
make install      # 安装生产依赖
make install-dev  # 安装开发依赖
make clean        # 清理缓存

# 运行应用
make run          # 启动应用
make dev          # 启动开发环境

# 代码质量
make format       # 格式化代码
make lint         # 代码检查
make type-check   # 类型检查
make test         # 运行测试
make check        # 全部检查

# 依赖管理
make deps-add PACKAGE=requests     # 添加依赖
make deps-remove PACKAGE=requests  # 移除依赖
make deps-update                   # 更新依赖
```

## 项目结构

```
TaifishingV4/
├── pyproject.toml          # 项目配置文件
├── uv.lock                 # 依赖锁定文件
├── .uvignore              # UV 忽略文件
├── start_uv.sh            # 启动脚本
├── dev_uv.sh              # 开发脚本
├── manage_deps_uv.sh      # 依赖管理脚本
├── Makefile               # 便捷命令
└── .venv/                 # UV 虚拟环境
```

## 配置文件说明

### pyproject.toml
- 项目元数据和依赖配置
- 开发工具配置（black, flake8, mypy, pytest）
- 构建系统配置

### .uvignore
- 指定 UV 忽略的文件和目录
- 类似 .gitignore 的语法

## 优势对比

| 特性 | UV | pip + venv |
|------|----|-----------| 
| 安装速度 | 10-100x 更快 | 标准速度 |
| 依赖解析 | 智能解析 | 基础解析 |
| 锁定文件 | 自动生成 | 手动管理 |
| 项目配置 | pyproject.toml | requirements.txt |
| Python 版本管理 | 自动管理 | 手动管理 |
| 缓存机制 | 高效缓存 | 基础缓存 |

## 故障排除

### 1. UV 未找到
```bash
# 检查安装
which uv
uv --version

# 重新安装
brew install uv
```

### 2. 依赖安装失败
```bash
# 清理缓存
uv cache clean

# 重新安装
uv sync --reinstall
```

### 3. Python 版本问题
```bash
# 查看可用版本
uv python list

# 安装特定版本
uv python install 3.13
```

### 4. 权限问题
```bash
# 检查权限
ls -la .venv/

# 修复权限
chmod -R 755 .venv/
```

## 最佳实践

1. **定期更新依赖**
   ```bash
   make deps-update
   ```

2. **使用锁定文件**
   - 提交 `uv.lock` 到版本控制
   - 确保团队环境一致

3. **分离开发依赖**
   ```bash
   uv add --dev pytest black flake8
   ```

4. **使用 Makefile**
   - 统一团队命令
   - 简化复杂操作

5. **定期清理**
   ```bash
   make clean
   ```

## 迁移指南

### 从 pip + venv 迁移
1. 备份现有环境
2. 安装 UV
3. 运行 `uv sync`
4. 测试应用功能
5. 删除旧环境

### 从 conda 迁移
1. 导出环境配置
2. 转换为 pyproject.toml
3. 安装 UV
4. 运行 `uv sync`

## 参考资源

- [UV 官方文档](https://docs.astral.sh/uv/)
- [pyproject.toml 规范](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python 包管理最佳实践](https://packaging.python.org/en/latest/guides/)

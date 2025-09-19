# UV Docker 集成说明

## 概述

本项目已集成 `uv` 作为 Python 包管理器，确保开发环境和 Docker 构建环境的一致性。`uv` 是一个快速的 Python 包管理工具，比传统的 `pip` 更快、更可靠。

## 优势

- **速度更快**: `uv` 比 `pip` 快 10-100 倍
- **依赖解析更准确**: 使用现代依赖解析算法
- **锁定文件**: 通过 `uv.lock` 确保依赖版本一致性
- **环境一致性**: 开发环境和生产环境使用相同的依赖管理工具

## 文件结构

```
TaifishV4/
├── pyproject.toml          # 项目配置和依赖定义
├── uv.lock                 # 锁定的依赖版本（自动生成）
├── Dockerfile.dev          # 开发环境Dockerfile（使用uv）
├── Dockerfile.prod         # 生产环境Dockerfile（使用uv，支持代理）
└── scripts/docker/
    └── build-with-uv.sh    # uv构建脚本
```

## 开发环境使用

### 1. 安装uv（如果未安装）

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或者使用pip
pip install uv
```

### 2. 同步依赖

```bash
# 安装所有依赖（包括开发依赖）
uv sync

# 只安装生产依赖
uv sync --no-dev

# 更新依赖
uv sync --upgrade
```

### 3. 运行应用

```bash
# 使用uv运行
uv run python app.py

# 或者激活虚拟环境后运行
source .venv/bin/activate
python app.py
```

### 4. 添加新依赖

```bash
# 添加生产依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 添加可选依赖组
uv add --optional dev package-name
```

## Docker 构建

### 1. 开发环境构建

```bash
# 使用Docker Compose构建
docker-compose -f docker-compose.dev.yml build

# 或使用构建脚本
./scripts/docker/build-with-uv.sh dev
```

### 2. 生产环境构建

```bash
# 无代理环境
./scripts/docker/build-with-uv.sh prod

# 有代理环境
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,::1
./scripts/docker/build-with-uv.sh prod
```

### 3. 使用Docker Compose构建

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml build

# 生产环境
docker-compose -f docker-compose.prod.yml build
```

## Dockerfile 配置说明

### 开发环境 (Dockerfile.dev)

```dockerfile
# 安装uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# 创建虚拟环境
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 复制项目配置文件
COPY --chown=whalefall:whalefall pyproject.toml uv.lock /app/

# 安装Python依赖
RUN uv sync --frozen --no-dev
```

### 生产环境 (Dockerfile.prod)

```dockerfile
# 安装uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# 创建虚拟环境
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 配置uv代理（如果设置了代理）
RUN if [ -n "$HTTP_PROXY" ]; then \
        uv config set global.index-url https://pypi.org/simple/ && \
        uv config set global.extra-index-url https://pypi.org/simple/; \
    fi

# 复制项目配置文件
COPY --chown=whalefall:whalefall pyproject.toml uv.lock /app/

# 安装Python依赖
RUN uv sync --frozen --no-dev
```

## 关键特性

### 1. 锁定文件 (uv.lock)

`uv.lock` 文件确保所有环境使用完全相同的依赖版本：

```bash
# 生成锁定文件
uv lock

# 使用锁定文件安装依赖
uv sync --frozen
```

### 2. 多阶段构建

Dockerfile 支持多阶段构建：

- `base`: 基础环境，包含系统依赖和uv
- `development`: 开发环境，包含开发工具
- `production`: 生产环境，只包含运行时依赖

### 3. 代理支持

生产环境Dockerfile支持代理配置：

```bash
docker build \
  --build-arg HTTP_PROXY=http://proxy.company.com:8080 \
  --build-arg HTTPS_PROXY=http://proxy.company.com:8080 \
  --build-arg NO_PROXY=localhost,127.0.0.1,::1 \
  -f Dockerfile.prod \
  --target production .
```

## 常用命令

### 开发环境

```bash
# 安装依赖
uv sync

# 运行应用
uv run python app.py

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run isort .

# 类型检查
uv run mypy .
```

### Docker 环境

```bash
# 构建开发镜像
./scripts/docker/build-with-uv.sh dev

# 构建生产镜像
./scripts/docker/build-with-uv.sh prod

# 启动开发环境
./scripts/docker/start-dev-base.sh
./scripts/docker/start-dev-flask.sh

# 启动生产环境
./scripts/docker/start-prod-base.sh
./scripts/docker/start-prod-flask.sh
```

## 故障排除

### 1. uv 安装失败

```bash
# 检查网络连接
curl -I https://astral.sh/uv/install.sh

# 手动安装
pip install uv
```

### 2. 依赖安装失败

```bash
# 清理缓存
uv cache clean

# 重新生成锁定文件
rm uv.lock
uv lock

# 重新安装
uv sync --frozen
```

### 3. Docker 构建失败

```bash
# 检查Dockerfile语法
docker build --no-cache -f Dockerfile.dev .

# 检查代理设置
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

## 最佳实践

1. **定期更新依赖**: 定期运行 `uv sync --upgrade` 更新依赖
2. **锁定版本**: 始终使用 `uv.lock` 文件确保版本一致性
3. **分离环境**: 开发和生产环境使用不同的Dockerfile
4. **代理配置**: 生产环境使用 `Dockerfile.prod` 支持代理
5. **缓存优化**: 利用Docker层缓存，先复制配置文件再复制代码

## 迁移指南

如果您之前使用 `pip` 和 `requirements.txt`：

1. 安装 `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. 生成 `pyproject.toml`: `uv init`
3. 添加现有依赖: `uv add $(cat requirements.txt)`
4. 生成锁定文件: `uv lock`
5. 更新Dockerfile使用 `uv sync --frozen --no-dev`

这样就完成了从 `pip` 到 `uv` 的迁移！

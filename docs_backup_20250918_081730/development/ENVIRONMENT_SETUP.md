# 开发环境设置指南

## 概述

本文档详细说明如何在不同的操作系统上设置泰摸鱼吧的开发环境，确保开发团队在不同机器上都能获得一致的开发体验。

## 系统要求

### 最低要求
- **Python**: 3.11 或 3.12
- **内存**: 4GB RAM
- **磁盘空间**: 2GB 可用空间
- **网络**: 互联网连接（用于下载依赖）

### 推荐配置
- **Python**: 3.12
- **内存**: 8GB RAM
- **磁盘空间**: 5GB 可用空间
- **操作系统**: macOS 12+, Ubuntu 20.04+, Windows 10+

## 快速开始

### 一键安装脚本

```bash
# 克隆项目
git clone <repository-url>
cd TaifishV4

# 运行一键安装脚本
chmod +x setup_dev_environment.sh
./setup_dev_environment.sh
```

## 详细安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd TaifishV4
```

### 2. Python环境设置

#### macOS
```bash
# 使用Homebrew安装Python
brew install python@3.12

# 验证安装
python3.12 --version
```

#### Ubuntu/Debian
```bash
# 更新包管理器
sudo apt update

# 安装Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-pip

# 验证安装
python3.12 --version
```

#### Windows
```bash
# 下载Python 3.12安装包
# 访问 https://www.python.org/downloads/
# 下载并安装Python 3.12

# 验证安装
python --version
```

### 3. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements-local.txt
```

### 5. Redis安装与配置

#### macOS
```bash
# 使用Homebrew安装Redis
brew install redis

# 启动Redis服务
brew services start redis

# 验证Redis运行
redis-cli ping
```

#### Ubuntu/Debian
```bash
# 安装Redis
sudo apt install redis-server

# 启动Redis服务
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 验证Redis运行
redis-cli ping
```

#### Windows
```bash
# 下载Redis for Windows
# 访问 https://github.com/microsoftarchive/redis/releases
# 下载并安装Redis

# 启动Redis服务
redis-server

# 验证Redis运行
redis-cli ping
```

### 6. 环境配置

#### 创建环境配置文件
```bash
# 复制环境配置模板
cp env.example .env
```

#### 编辑.env文件
```bash
# 基础配置
FLASK_APP=app
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# 数据库配置（使用默认SQLite）
# DATABASE_URL=sqlite:///./userdata/taifish_dev.db
# SQLALCHEMY_DATABASE_URI=sqlite:///./userdata/taifish_dev.db

# Redis配置
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0

# JWT配置
JWT_SECRET_KEY=your-jwt-secret-here
JWT_ACCESS_TOKEN_EXPIRES=3600

# 开发模式
DEVELOPMENT=True
```

### 7. 启动应用

#### 方式一：使用启动脚本（推荐）
```bash
# 启动完整开发环境
./start_dev_with_redis.sh
```

#### 方式二：手动启动
```bash
# 启动Redis（如果未启动）
./redis_manager.sh start

# 启动Flask应用
python app.py
```

#### 方式三：使用开发工作流
```bash
# 开始新功能开发
./dev_workflow.sh start '功能名称'

# 启动应用
python app.py
```

## 验证安装

### 1. 检查服务状态

```bash
# 检查Redis状态
./redis_manager.sh status

# 检查数据库连接
python test_database.py
```

### 2. 访问应用

- **应用地址**: http://localhost:5001
- **API状态**: http://localhost:5001/api/status
- **健康检查**: http://localhost:5001/api/health

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_models.py

# 生成测试覆盖率报告
pytest --cov=app --cov-report=html
```

## 开发工具配置

### 1. 代码编辑器配置

#### VS Code
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black"
}
```

#### PyCharm
- 设置Python解释器为虚拟环境中的Python
- 启用代码检查
- 配置代码格式化

### 2. Git配置

```bash
# 配置Git用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 配置Git忽略文件
echo "venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".env" >> .gitignore
```

## 故障排除

### 常见问题

#### 1. Python版本问题
```bash
# 检查Python版本
python --version

# 如果版本不正确，重新创建虚拟环境
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
```

#### 2. 依赖安装失败
```bash
# 清理pip缓存
pip cache purge

# 升级pip
pip install --upgrade pip

# 重新安装依赖
pip install -r requirements-local.txt
```

#### 3. Redis连接失败
```bash
# 检查Redis是否运行
./redis_manager.sh status

# 重启Redis
./redis_manager.sh restart

# 检查端口占用
lsof -i :6379
```

#### 4. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la userdata/taifish_dev.db

# 修复权限
chmod 666 userdata/taifish_dev.db

# 重新创建数据库
rm userdata/taifish_dev.db
python test_database.py
```

#### 5. 端口占用问题
```bash
# 检查端口占用
lsof -i :5001

# 修改端口
export FLASK_PORT=5002
python app.py
```

### 日志查看

```bash
# 查看应用日志
tail -f userdata/logs/app.log

# 查看Redis日志
./redis_manager.sh logs

# 查看错误日志
tail -f userdata/logs/error.log
```

## 开发工作流

### 1. 开始新功能开发

```bash
# 创建功能分支
git checkout -b feature/新功能名称

# 开始开发
./dev_workflow.sh start '新功能名称'
```

### 2. 数据库变更

```bash
# 修改模型文件后创建迁移
./dev_workflow.sh migrate '描述变更内容'

# 应用迁移
./dev_workflow.sh apply

# 如有问题，回滚迁移
./dev_workflow.sh rollback 1
```

### 3. 代码提交

```bash
# 添加更改
git add .

# 提交更改
git commit -m "feat: 添加新功能"

# 推送分支
git push origin feature/新功能名称
```

### 4. 测试

```bash
# 运行测试
pytest

# 检查代码质量
flake8 app/
black app/
```

## 性能优化

### 1. 开发环境优化

```bash
# 使用内存数据库（仅开发）
export SQLALCHEMY_DATABASE_URI="sqlite:///:memory:"

# 禁用调试模式（性能测试）
export FLASK_DEBUG=False
```

### 2. Redis优化

```bash
# 配置Redis内存限制
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## 团队协作

### 1. 环境同步

```bash
# 导出依赖列表
pip freeze > requirements-lock.txt

# 安装锁定版本
pip install -r requirements-lock.txt
```

### 2. 配置共享

```bash
# 创建团队配置模板
cp .env.example .env.team

# 团队成员复制并修改
cp .env.team .env
```

### 3. 代码规范

```bash
# 安装代码检查工具
pip install flake8 black isort

# 运行代码检查
flake8 app/
black app/
isort app/
```

## 维护指南

### 1. 定期更新

```bash
# 更新依赖
pip install --upgrade -r requirements-local.txt

# 更新Redis
brew upgrade redis  # macOS
sudo apt upgrade redis-server  # Ubuntu
```

### 2. 备份数据

```bash
# 备份数据库
cp userdata/taifish_dev.db userdata/backups/backup_$(date +%Y%m%d_%H%M%S).db

# 备份Redis数据
redis-cli BGSAVE
```

### 3. 清理环境

```bash
# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 清理日志文件
find userdata/logs -name "*.log" -mtime +7 -delete
```

## 联系支持

如果在设置过程中遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查项目的Issues页面
3. 联系项目维护者

---

**注意**: 本文档会定期更新，请确保使用最新版本。

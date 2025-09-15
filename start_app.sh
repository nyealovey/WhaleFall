#!/bin/bash

# 设置环境变量
export DATABASE_URL="postgresql://taifish_user:Taifish2024!@localhost:5432/taifish_dev"
export REDIS_URL="redis://:Taifish2024!@localhost:6379/0"

# 激活虚拟环境
source .venv/bin/activate

# 启动应用
python app.py
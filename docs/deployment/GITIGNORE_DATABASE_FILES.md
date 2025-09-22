# Git 忽略数据库文件配置指南

## 🎯 目标

确保定时任务数据库和其他用户数据文件不会被上传到 GitHub，避免数据泄露和版本冲突。

## 📁 已配置的忽略规则

### 1. 用户数据目录
```
userdata/
```
- 包含所有用户数据：日志、备份、上传文件、定时任务数据库等
- 完全排除在版本控制之外

### 2. 数据库文件模式
```
*.db
*.db-shm
*.db-wal
*.sqlite
*.sqlite3
```
- 排除所有 SQLite 数据库文件
- 排除数据库共享内存和 WAL 文件

### 3. 其他数据文件
```
migrations/versions/*.py
```
- 排除自动生成的数据库迁移文件

## 🔍 定时任务数据库位置

定时任务数据库存储在：
```
userdata/scheduler.db
```

这个文件包含：
- APScheduler 任务定义
- 任务执行历史
- 任务状态信息
- 调度器配置

## ✅ 验证配置

### 检查忽略状态
```bash
# 查看被忽略的文件
git status --ignored

# 检查是否有数据库文件被跟踪
git ls-files | grep -E "\.(db|sqlite|sqlite3)$"
```

### 预期结果
- `userdata/` 目录应该出现在忽略列表中
- 不应该有任何 `.db` 或 `.sqlite` 文件被 Git 跟踪

## 🚨 如果发现数据库文件被跟踪

### 1. 从 Git 中移除（保留本地文件）
```bash
git rm --cached userdata/scheduler.db
git rm --cached *.db
git rm --cached *.sqlite*
```

### 2. 提交移除操作
```bash
git add .gitignore
git commit -m "chore: 从版本控制中移除数据库文件"
```

### 3. 推送到远程
```bash
git push origin main
```

## 🔧 热更新时的注意事项

### 1. 定时任务数据库更新
- 每次热更新时，定时任务数据库可能会被更新
- 这些更新只影响本地环境，不会上传到 GitHub

### 2. 数据持久化
- 定时任务数据库存储在 `userdata/` 目录中
- 该目录已被 `.gitignore` 完全排除
- 数据在热更新后仍然保持

### 3. 环境隔离
- 开发环境、测试环境、生产环境的数据完全隔离
- 每个环境都有自己的 `userdata/` 目录

## 📋 最佳实践

### 1. 定期检查
```bash
# 定期检查是否有新的数据库文件被意外跟踪
git status --ignored | grep -E "\.(db|sqlite|sqlite3)$"
```

### 2. 提交前检查
```bash
# 提交前检查是否有数据库文件
git add .
git status
```

### 3. 团队协作
- 确保所有团队成员都了解数据库文件排除规则
- 在 README 中说明数据文件位置
- 提供环境配置指南

## 🔗 相关文件

- `.gitignore` - Git 忽略规则配置
- `app/scheduler.py` - 定时任务调度器配置
- `userdata/` - 用户数据目录（被忽略）

## 📝 更新历史

- 2025-01-22 - 初始配置，添加数据库文件忽略规则
- 2025-01-22 - 完善忽略规则，确保定时任务数据库不被跟踪

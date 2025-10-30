# 代码统计脚本

本目录包含用于统计项目代码的工具脚本。

## 文件说明

- `analyze_code.py` - Python统计脚本（功能完整）
- `quick_stats.sh` - Shell快速统计脚本
- `README.md` - 本说明文档

## 快速开始

### 1. Python脚本（推荐）

```bash
# 基础统计
python3 scripts/analyze_code.py

# 分析指定目录
python3 scripts/analyze_code.py app

# 生成完整报告
python3 scripts/analyze_code.py app \
    --json docs/reports/stats.json \
    --markdown docs/reports/code_stats.md \
    --top 30
```

### 2. Shell脚本（快速）

```bash
# 快速统计
./scripts/quick_stats.sh

# 指定目录
./scripts/quick_stats.sh app
```

## 使用示例

### 基础统计

```bash
$ python3 scripts/analyze_code.py app
正在分析目录: app
排除模式: vendor, __pycache__, .git

============================================================
代码统计摘要
============================================================
总文件数: 214
总代码行数: 57,808

按文件类型统计:
------------------------------------------------------------
.py         108 个文件    31,568 行   54.6%
.js          43 个文件    14,964 行   25.9%
.html        33 个文件     7,233 行   12.5%
.css         28 个文件     3,852 行    6.7%
.yaml         2 个文件       191 行    0.3%
```

### 导出报告

```bash
# 导出JSON
python3 scripts/analyze_code.py app --json stats.json

# 导出Markdown
python3 scripts/analyze_code.py app --markdown report.md

# 同时导出
python3 scripts/analyze_code.py app --json stats.json --markdown report.md
```

### 自定义排除目录

```bash
python3 scripts/analyze_code.py app \
    --exclude vendor __pycache__ .git node_modules migrations
```

### 显示更多最大文件

```bash
# 显示前50个最大文件
python3 scripts/analyze_code.py app --top 50
```

## 参数说明

### analyze_code.py

```
usage: analyze_code.py [-h] [--exclude EXCLUDE [EXCLUDE ...]] 
                       [--json JSON] [--markdown MARKDOWN] 
                       [--top TOP] [directory]

参数:
  directory             要分析的目录 (默认: app)
  --exclude            要排除的目录模式 (默认: vendor __pycache__ .git)
  --json JSON          导出JSON文件路径
  --markdown MARKDOWN  导出Markdown报告路径
  --top TOP            显示前N个最大文件 (默认: 20)
```

### quick_stats.sh

```bash
./scripts/quick_stats.sh [目录]

参数:
  目录    要分析的目录 (默认: app)
```

## 常见用法

### 1. 日常快速查看

```bash
./scripts/quick_stats.sh
```

### 2. 生成详细报告

```bash
python3 scripts/analyze_code.py app \
    --markdown docs/reports/code_analysis_$(date +%Y%m%d).md \
    --top 50
```

### 3. 定期统计（添加到crontab）

```bash
# 每天凌晨2点生成报告
0 2 * * * cd /path/to/project && python3 scripts/analyze_code.py app --markdown docs/reports/daily_stats.md
```

### 4. Git提交前统计

在 `.git/hooks/pre-commit` 中添加：

```bash
#!/bin/bash
python3 scripts/analyze_code.py app --markdown docs/reports/code_stats.md
git add docs/reports/code_stats.md
```

## 输出格式

### JSON格式

```json
{
  "files_by_dir": {
    "routes": [
      {
        "name": "routes/instances.py",
        "lines": 926,
        "ext": ".py"
      }
    ]
  },
  "total_files": 214,
  "total_lines": 57808,
  "stats_by_ext": {
    ".py": {
      "count": 108,
      "lines": 31568
    }
  }
}
```

### Markdown格式

生成的Markdown报告包含：
- 总体统计
- 按文件类型统计（表格）
- 按目录统计（详细列表）

## 注意事项

1. **排除目录**: 默认排除 vendor、__pycache__、.git
2. **文件类型**: 支持 .py、.js、.css、.html、.yaml、.yml
3. **编码**: 使用UTF-8编码读取文件
4. **权限**: 确保脚本有执行权限（chmod +x）

## 故障排除

### 问题：脚本无法执行

```bash
# 赋予执行权限
chmod +x scripts/analyze_code.py
chmod +x scripts/quick_stats.sh
```

### 问题：统计结果不准确

检查是否正确排除了第三方库目录：

```bash
python3 scripts/analyze_code.py app --exclude vendor node_modules __pycache__
```

### 问题：找不到某些文件

确保文件扩展名在支持列表中，或修改脚本添加新的扩展名。

## 更多信息

详细文档请参考：`docs/scripts/code_statistics_guide.md`

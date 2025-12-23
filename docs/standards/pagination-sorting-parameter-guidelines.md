# 分页与排序参数规范

## 目标
1. 列表页 URL 可分享且行为稳定: 刷新/复制链接后分页大小不漂移。
2. 前后端对分页字段达成单一约定,减少契约漂移与兼容分支。
3. 逐步淘汰历史字段,但保留兼容与可观测性(日志/事件).

## 分页参数(统一)
### 1) 统一使用的字段(新代码必须)
- `page`: 页码,从 1 开始。
- `page_size`: 每页数量。

### 2) 兼容字段(仅用于兼容旧链接/旧客户端)
- `limit`: 历史字段,语义等同 `page_size`。
- `pageSize`: 历史字段,语义等同 `page_size`。

### 3) 取值约束(建议)
- `page`: `>= 1`。
- `page_size`: 建议范围 `1 ~ 200`(按接口实际限制裁剪)。

## 前端落点
- Grid.js 统一包装器使用 `page_size` 作为请求参数: `app/static/js/common/grid-wrapper.js`。
- 如需兼容旧 URL,仅在解析阶段识别 `limit/pageSize`,并转写为 `page_size`(避免“新代码继续输出旧字段”)。

## 后端落点
- 列表接口统一通过 `app/utils/pagination_utils.py` 解析分页参数:
  - `resolve_page(...)`
  - `resolve_page_size(...)`(兼容 `limit/pageSize`)
- 当请求使用旧字段时,记录结构化日志,便于统计与清理。

## 门禁(禁止回归)
- 运行: `./scripts/code_review/pagination_param_guard.sh`
- 规则: GridWrapper 分页请求必须使用 `page_size`,禁止回退为 `limit`。


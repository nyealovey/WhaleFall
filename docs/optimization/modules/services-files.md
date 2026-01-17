# services/files

## Core Purpose

- 提供导出/模板类能力（CSV 内容 + 文件名），供 API 层下载：
  - 账户导出（AccountExportService）
  - 实例导出（InstancesExportService）
  - 实例导入模板（InstancesImportTemplateService）
  - 数据库台账导出（DatabaseLedgerExportService）

## Unnecessary Complexity Found

- （已落地）`app/services/files/account_export_service.py:22-35` / `app/services/files/instances_export_service.py:19-85` / `app/services/files/database_ledger_export_service.py`：
  - 多处重复定义同名 `CsvExportResult` dataclass。

- （已落地）`app/services/files/instances_import_template_service.py:14`：
  - 仅为了复用 `CsvExportResult` 而从 `instances_export_service` 反向 import，形成不必要的 files 内部耦合。

## Code to Remove

- 将 `CsvExportResult` 下沉为单一类型：`app/services/files/csv_export_result.py:11`（可删 LOC 估算：~20-40，来自重复 dataclass 定义与多余依赖）。

## Simplification Recommendations

1. files 域内的“共享返回类型”单点定义
   - Current: 每个导出服务各自定义 `CsvExportResult`，且模板服务为了复用而依赖导出实现文件。
   - Proposed: 抽一个最小的 `csv_export_result.py` 提供 dataclass；其余服务只 import 类型。
   - Impact: 减少重复与耦合，避免后续扩展时出现多份不一致定义。

## YAGNI Violations

- `CsvExportResult` 的多份复制（没有差异，也没有扩展点需求）。

## Final Assessment

- 可删 LOC 估算：~20-40（已落地）
- Complexity: Low -> Lower
- Recommended action: Done（仅移动/复用类型定义，不影响对外行为）。


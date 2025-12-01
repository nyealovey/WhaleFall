# WhaleFall 运行流转图索引
**版本**：v0.4｜2025-12-01｜文件已拆分为五份更聚焦的文档。  
请按需求阅读对应分类：

1. **标准 CRUD 流程** → `docs/architecture/taifish_standard_crud_flows.md`  
   包含：用户、实例、账户分类、分类规则、凭据等常规模块的增删改查链路。
2. **批量操作 CRUD** → `docs/architecture/taifish_crud_bulk_flows.md`  
   包含：标签批量分配/移除、实例批量导入/删除等高风险批量链路。
3. **数据采集 & 容量聚合** → `docs/architecture/taifish_data_sync_flows.md`  
   包含：账户/容量采集、容量聚合、数据同步计划等链路与故障排查提示。
4. **测试 & 自动分类流程** → `docs/architecture/taifish_testing_classification_flows.md`  
   包含：连接测试、批量测试、参数校验、账户自动分类等流程。
5. **前端展示数据链路** → `docs/architecture/taifish_frontend_display_flows.md`  
   包含：容量统计、分区指标等前端视图与后台 API 的映射关系。

> 所有新增流程请直接在相应文档补充；若涉及前后端参数校验，也请同步更新《前后端数据一致性手册》。

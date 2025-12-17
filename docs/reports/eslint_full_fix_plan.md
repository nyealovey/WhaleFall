# ESLint 全量修复计划（基于 2025-12-17 10:09 报告）

最新报告: `docs/reports/eslint_full_2025-12-17_100931.txt`  
诊断总数: **66**（15 errors / 51 warnings）  
受影响文件: **16**  
主要规则占比: security/detect-object-injection **45**、no-unused-vars **15**、no-undef **0**。

## 问题分组与修复策略

1) **对象注入警告（security/detect-object-injection，剩余 45 条）**  
   - 当前集中区域：history/logs/logs.js、history/logs/log-detail.js、history/sessions/{session-detail,sync-sessions}.js、instances/{list,detail,statistics}.js、admin/partitions/partition-list.js、components/charts/{manager,transformers}.js、databases/ledgers.js。  
   - 处理策略：继续使用 `UNSAFE_KEYS` + 显式白名单；map/switch 前定义允许键；表单收集用安全 assign/get helper；必要时改为固定字段解构。  

2) **未使用变量/参数（no-unused-vars，15 条）**  
   - 典型文件：components/charts/{chart-renderer,filters}.js、dashboard/overview.js、instances/{list,statistics}.js、history/logs/log-detail.js、history/sessions/session-detail.js。  
   - 处理策略：删除未用声明或改下划线占位；未来占位需中文注释说明。  

3) **未定义全局/依赖缺失（no-undef，0 条）**  
   - 当前报告无 no-undef 阻断项。  

## 优先级与执行顺序

1. **对象注入收敛优先**（按剩余集中度）：  
   - a) 历史/会话：history/logs/{logs,log-detail}.js、history/sessions/{session-detail,sync-sessions}.js。  
   - b) 实例/分区：instances/{list,detail,statistics}.js、admin/partitions/partition-list.js。  
   - c) 图表体系：components/charts/{manager,transformers}.js，顺带修复 chart-renderer/filters 的未用变量。  
   - d) 其他零散：databases/ledgers.js 等。  
   每块完成后立即 `npx eslint <files>`。  
2. **同步清理 no-unused-vars**：上述批次中涉及的未用变量随改随清。  
3. **阶段验证**：批次修完跑对应文件 eslint，全部完成后执行 `npm run lint` 或 `make quality`，目标 0 error / 0 warning。  

## 注意事项
- 禁止以全局 `eslint-disable` 兜底；若第三方调用无法改写，使用单行 `// eslint-disable-next-line` 并附中文原因。  
- 涉及用户输入的动态键需同步评估安全风险，必要时统一引入键白名单或映射层。  
- 公共组件/工具改动后，回归关键页面（instances、tags、auth、credentials、scheduler）基础交互。  
- 继续复用已落地的安全 helper（isSafeKey 等），避免在各文件重复实现；新文件优先引用已有实现或内联白名单。  

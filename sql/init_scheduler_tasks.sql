-- =============================================
-- 定时任务初始化脚本
-- 鲸落 - 数据同步管理平台
-- 基于 app/config/scheduler_tasks.yaml 配置生成
-- =============================================

-- 注意：APScheduler任务表会在应用启动时自动创建
-- 此脚本用于记录默认任务配置，实际任务由应用启动时加载

-- 默认任务配置说明
-- 1. sync_accounts - 账户同步任务（每30分钟执行一次）
-- 2. cleanup_logs - 清理旧日志任务（每天凌晨2点执行）

-- 任务配置参数说明：
-- - id: 任务唯一标识符
-- - name: 任务显示名称
-- - function: 任务函数名
-- - trigger_type: 触发器类型 (interval/cron)
-- - trigger_params: 触发器参数
-- - enabled: 是否启用
-- - description: 任务描述

-- 这些任务会在应用启动时自动从 app/config/scheduler_tasks.yaml 加载
-- 用户可以通过Web界面修改任务参数，修改后的配置会保存到数据库

-- 任务状态说明：
-- - 任务状态存储在 apscheduler_jobs 表中
-- - job_state 字段存储序列化的任务信息
-- - next_run_time 字段存储下次执行时间

-- 查看当前任务状态：
-- SELECT id, next_run_time, job_state FROM apscheduler_jobs;

-- 手动添加任务（示例）：
-- INSERT INTO apscheduler_jobs (id, next_run_time, job_state) VALUES
-- ('test_task', EXTRACT(EPOCH FROM NOW() + INTERVAL '1 minute'), 
--  E'\\x800495e2000000000000008c0c__main__\\x94\\x8c0ctest_function\\x94\\x93\\x94.');

-- 注意：手动插入任务需要正确的序列化格式，建议通过应用界面管理任务

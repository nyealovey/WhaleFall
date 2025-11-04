-- 账户同步两阶段重构 - 回填 account_permission.instance_account_id
-- 
-- 使用说明：
--  1. 确保已创建并填充 instance_accounts 表；
--  2. 执行本脚本以回填 account_permission 的外键引用；
--  3. 建议执行后运行 `SELECT COUNT(*) FROM account_permission WHERE instance_account_id IS NULL;`
--     验证结果为 0。

UPDATE account_permission AS casd
SET instance_account_id = ia.id
FROM instance_accounts AS ia
WHERE ia.instance_id = casd.instance_id
  AND ia.db_type      = LOWER(casd.db_type)
  AND ia.username     = casd.username;

-- 账户同步两阶段重构 - 完整迁移脚本（PostgreSQL）
-- 步骤：
--   1. 创建 / 补全 instance_accounts 表结构；
--   2. 从 current_account_sync_data 聚合历史记录写入 instance_accounts；
--   3. 回填 current_account_sync_data.instance_account_id 外键；
--   4. 建立约束并清理旧字段。

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. 表结构准备
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS instance_accounts (
    id            SERIAL PRIMARY KEY,
    instance_id   INTEGER      NOT NULL REFERENCES instances(id),
    username      VARCHAR(255) NOT NULL,
    db_type       VARCHAR(50)  NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    first_seen_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ,
    attributes    JSONB,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE instance_accounts
    ADD COLUMN IF NOT EXISTS attributes JSONB;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_instance_account_instance_username'
    ) THEN
        ALTER TABLE instance_accounts
            ADD CONSTRAINT uq_instance_account_instance_username
            UNIQUE (instance_id, db_type, username);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_instance_accounts_instance_id ON instance_accounts(instance_id);
CREATE INDEX IF NOT EXISTS ix_instance_accounts_username   ON instance_accounts(username);
CREATE INDEX IF NOT EXISTS ix_instance_accounts_active     ON instance_accounts(is_active);
CREATE INDEX IF NOT EXISTS ix_instance_accounts_last_seen  ON instance_accounts(last_seen_at);

COMMENT ON TABLE  instance_accounts IS '实例-账户关系表，维护账户存在状态';
COMMENT ON COLUMN instance_accounts.instance_id   IS '实例ID';
COMMENT ON COLUMN instance_accounts.username      IS '账户名（含主机信息时保留）';
COMMENT ON COLUMN instance_accounts.db_type       IS '数据库类型';
COMMENT ON COLUMN instance_accounts.is_active     IS '账户是否活跃';
COMMENT ON COLUMN instance_accounts.first_seen_at IS '首次发现时间';
COMMENT ON COLUMN instance_accounts.last_seen_at  IS '最后发现时间';
COMMENT ON COLUMN instance_accounts.deleted_at    IS '删除时间';
COMMENT ON COLUMN instance_accounts.attributes    IS '补充属性：主机、锁定状态等';

ALTER TABLE current_account_sync_data
    ADD COLUMN IF NOT EXISTS instance_account_id INTEGER;

-- ---------------------------------------------------------------------------
-- 2. 聚合 current_account_sync_data 数据写入 instance_accounts
-- ---------------------------------------------------------------------------
WITH normalized AS (
    SELECT
        id,
        instance_id,
        LOWER(db_type) AS db_type,
        username,
        type_specific,
        COALESCE(last_sync_time, sync_time, last_change_time, NOW()) AS observed_at
    FROM current_account_sync_data
),
summary AS (
    SELECT
        instance_id,
        db_type,
        username,
        MIN(observed_at) AS first_seen_at,
        MAX(observed_at) AS last_seen_at
    FROM normalized
    GROUP BY instance_id, db_type, username
),
latest AS (
    SELECT
        id,
        instance_id,
        db_type,
        username,
        type_specific,
        observed_at,
        ROW_NUMBER() OVER (
            PARTITION BY instance_id, db_type, username
            ORDER BY observed_at DESC, id DESC
        ) AS rn
    FROM normalized
)
INSERT INTO instance_accounts (
    instance_id,
    username,
    db_type,
    is_active,
    first_seen_at,
    last_seen_at,
    deleted_at,
    attributes,
    created_at,
    updated_at
)
SELECT
    s.instance_id,
    s.username,
    s.db_type,
    TRUE AS is_active,
    COALESCE(s.first_seen_at, NOW()) AS first_seen_at,
    COALESCE(s.last_seen_at,  NOW()) AS last_seen_at,
    NULL AS deleted_at,
    jsonb_strip_nulls(
        jsonb_build_object(
            'source', 'migration_current_account_sync_data',
            'last_snapshot_type_specific', l.type_specific
        )
    ) AS attributes,
    COALESCE(s.first_seen_at, NOW()) AS created_at,
    COALESCE(s.last_seen_at,  NOW()) AS updated_at
FROM summary s
JOIN latest l
  ON l.instance_id = s.instance_id
 AND l.db_type      = s.db_type
 AND l.username     = s.username
 AND l.rn = 1
ON CONFLICT (instance_id, db_type, username) DO UPDATE
SET
    is_active = EXCLUDED.is_active,
    first_seen_at = LEAST(instance_accounts.first_seen_at, EXCLUDED.first_seen_at),
    last_seen_at  = GREATEST(instance_accounts.last_seen_at, EXCLUDED.last_seen_at),
    deleted_at    = NULL,
    attributes    = COALESCE(
                        NULLIF(jsonb_strip_nulls(EXCLUDED.attributes), '{}'::jsonb),
                        instance_accounts.attributes
                    ),
    updated_at    = COALESCE(EXCLUDED.updated_at, NOW());

-- ---------------------------------------------------------------------------
-- 3. 回填 current_account_sync_data.instance_account_id
-- ---------------------------------------------------------------------------
UPDATE current_account_sync_data AS casd
SET instance_account_id = ia.id
FROM instance_accounts AS ia
WHERE ia.instance_id = casd.instance_id
  AND ia.db_type      = LOWER(casd.db_type)
  AND ia.username     = casd.username;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM current_account_sync_data
        WHERE instance_account_id IS NULL
    ) THEN
        RAISE EXCEPTION '回填 instance_account_id 失败：存在未匹配的账户记录';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 4. 约束 & 清理
-- ---------------------------------------------------------------------------
ALTER TABLE current_account_sync_data
    ALTER COLUMN instance_account_id SET NOT NULL;

ALTER TABLE current_account_sync_data
    DROP CONSTRAINT IF EXISTS fk_current_account_sync_instance_account;

ALTER TABLE current_account_sync_data
    ADD CONSTRAINT fk_current_account_sync_instance_account
        FOREIGN KEY (instance_account_id)
        REFERENCES instance_accounts(id)
        ON DELETE CASCADE;

ALTER TABLE current_account_sync_data
    DROP COLUMN IF EXISTS is_active,
    DROP COLUMN IF EXISTS is_deleted,
    DROP COLUMN IF EXISTS deleted_time,
    DROP COLUMN IF EXISTS last_classified_at,
    DROP COLUMN IF EXISTS last_classification_batch_id;

DROP INDEX IF EXISTS idx_current_account_sync_is_deleted;
DROP INDEX IF EXISTS idx_current_account_sync_deleted_time;

COMMIT;

ANALYZE instance_accounts;
ANALYZE current_account_sync_data;

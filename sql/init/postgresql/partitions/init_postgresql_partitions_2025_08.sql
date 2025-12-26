-- PostgreSQL 月分区子表初始化脚本（从 sql/init/postgresql/init_postgresql.sql 拆分）
--
-- 仅保留 2025-08 分区。
-- 执行顺序：先执行 sql/init/postgresql/init_postgresql.sql，再执行本文件。

-- ----------------------------
-- Table structure for database_size_aggregations_2025_08
-- ----------------------------
CREATE TABLE "public"."database_size_aggregations_2025_08" (
  "id" int8 NOT NULL DEFAULT nextval('database_size_aggregations_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "database_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "period_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "avg_size_mb" int8 NOT NULL,
  "max_size_mb" int8 NOT NULL,
  "min_size_mb" int8 NOT NULL,
  "data_count" int4 NOT NULL,
  "avg_data_size_mb" int8,
  "max_data_size_mb" int8,
  "min_data_size_mb" int8,
  "avg_log_size_mb" int8,
  "max_log_size_mb" int8,
  "min_log_size_mb" int8,
  "size_change_mb" int8 NOT NULL DEFAULT 0,
  "size_change_percent" numeric(10,2) NOT NULL DEFAULT 0,
  "data_size_change_mb" int8,
  "data_size_change_percent" numeric(10,2),
  "log_size_change_mb" int8,
  "log_size_change_percent" numeric(10,2),
  "growth_rate" numeric(10,2) NOT NULL DEFAULT 0,
  "calculated_at" timestamp(6) NOT NULL,
  "created_at" timestamp(6) NOT NULL
)
;
COMMENT ON TABLE "public"."database_size_aggregations_2025_08" IS '数据库聚合表分区表 - 2025-08';

-- ----------------------------
-- Table structure for database_size_stats_2025_08
-- ----------------------------
CREATE TABLE "public"."database_size_stats_2025_08" (
  "id" int8 NOT NULL DEFAULT nextval('database_size_stats_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "database_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "size_mb" int8 NOT NULL,
  "data_size_mb" int8,
  "log_size_mb" int8,
  "collected_date" date NOT NULL,
  "collected_at" timestamptz(6) NOT NULL DEFAULT now(),
  "created_at" timestamptz(6) NOT NULL DEFAULT now(),
  "updated_at" timestamptz(6) NOT NULL DEFAULT now()
)
;
COMMENT ON TABLE "public"."database_size_stats_2025_08" IS '数据库统计表分区表 - 2025-08';

-- ----------------------------
-- Table structure for instance_size_aggregations_2025_08
-- ----------------------------
CREATE TABLE "public"."instance_size_aggregations_2025_08" (
  "id" int8 NOT NULL DEFAULT nextval('instance_size_aggregations_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "period_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "total_size_mb" int8 NOT NULL,
  "avg_size_mb" int8 NOT NULL,
  "max_size_mb" int8 NOT NULL,
  "min_size_mb" int8 NOT NULL,
  "data_count" int4 NOT NULL,
  "database_count" int4 NOT NULL,
  "avg_database_count" numeric(10,2),
  "max_database_count" int4,
  "min_database_count" int4,
  "total_size_change_mb" int8,
  "total_size_change_percent" numeric(10,2),
  "database_count_change" int4,
  "database_count_change_percent" numeric(10,2),
  "growth_rate" numeric(10,2),
  "trend_direction" varchar(20) COLLATE "pg_catalog"."default",
  "calculated_at" timestamp(6) NOT NULL,
  "created_at" timestamp(6) NOT NULL
)
;
COMMENT ON TABLE "public"."instance_size_aggregations_2025_08" IS '实例聚合表分区表 - 2025-08';

-- ----------------------------
-- Table structure for instance_size_stats_2025_08
-- ----------------------------
CREATE TABLE "public"."instance_size_stats_2025_08" (
  "id" int4 NOT NULL DEFAULT nextval('instance_size_stats_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "total_size_mb" int4 NOT NULL DEFAULT 0,
  "database_count" int4 NOT NULL DEFAULT 0,
  "collected_date" date NOT NULL,
  "collected_at" timestamptz(6) NOT NULL DEFAULT now(),
  "is_deleted" bool NOT NULL DEFAULT false,
  "deleted_at" timestamptz(6),
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;
COMMENT ON TABLE "public"."instance_size_stats_2025_08" IS '实例统计表分区表 - 2025-08';
ALTER TABLE "public"."database_size_aggregations" ATTACH PARTITION "public"."database_size_aggregations_2025_08" FOR VALUES FROM (
'2025-08-01'
) TO (
'2025-09-01'
)
;
ALTER TABLE "public"."database_size_stats" ATTACH PARTITION "public"."database_size_stats_2025_08" FOR VALUES FROM (
'2025-08-01'
) TO (
'2025-09-01'
)
;
ALTER TABLE "public"."instance_size_aggregations" ATTACH PARTITION "public"."instance_size_aggregations_2025_08" FOR VALUES FROM (
'2025-08-01'
) TO (
'2025-09-01'
)
;
ALTER TABLE "public"."instance_size_stats" ATTACH PARTITION "public"."instance_size_stats_2025_08" FOR VALUES FROM (
'2025-08-01'
) TO (
'2025-09-01'
)
;

-- ----------------------------
-- Indexes structure for table database_size_aggregations_2025_08
-- ----------------------------
CREATE INDEX "database_size_aggregations_2025_08_id_idx" ON "public"."database_size_aggregations_2025_08" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_aggregations_2025_08_period_type_period_start_idx" ON "public"."database_size_aggregations_2025_08" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "database_size_aggregations_20_instance_id_database_name_pe_key3" ON "public"."database_size_aggregations_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_aggregations_20_instance_id_period_type_peri_idx3" ON "public"."database_size_aggregations_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_aggregations_2025_08_instance_db" ON "public"."database_size_aggregations_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_aggregations_2025_08_period" ON "public"."database_size_aggregations_2025_08" USING btree (
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST,
  "period_end" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_aggregations_2025_08_type" ON "public"."database_size_aggregations_2025_08" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table database_size_aggregations_2025_08
-- ----------------------------
ALTER TABLE "public"."database_size_aggregations_2025_08" ADD CONSTRAINT "database_size_aggregations_20_instance_id_database_name_pe_key3" UNIQUE ("instance_id", "database_name", "period_type", "period_start");

-- ----------------------------
-- Indexes structure for table database_size_stats_2025_08
-- ----------------------------
CREATE INDEX "database_size_stats_2025_08_collected_date_idx" ON "public"."database_size_stats_2025_08" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_stats_2025_08_instance_id_collected_date_idx" ON "public"."database_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "database_size_stats_2025_08_instance_id_database_name_colle_key" ON "public"."database_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_stats_2025_08_instance_id_database_name_idx" ON "public"."database_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_stats_2025_08_date" ON "public"."database_size_stats_2025_08" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_stats_2025_08_instance_date" ON "public"."database_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_stats_2025_08_instance_db" ON "public"."database_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table database_size_stats_2025_08
-- ----------------------------
CREATE TRIGGER "trg_update_instance_database_last_seen" AFTER INSERT ON "public"."database_size_stats_2025_08"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_instance_database_last_seen"();

-- ----------------------------
-- Uniques structure for table database_size_stats_2025_08
-- ----------------------------
ALTER TABLE "public"."database_size_stats_2025_08" ADD CONSTRAINT "database_size_stats_2025_08_instance_id_database_name_colle_key" UNIQUE ("instance_id", "database_name", "collected_date");

-- ----------------------------
-- Indexes structure for table instance_size_aggregations_2025_08
-- ----------------------------
CREATE INDEX "idx_instance_size_aggregations_2025_08_instance" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_aggregations_2025_08_period" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST,
  "period_end" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_aggregations_2025_08_type" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_aggregations_2025_08_id_idx" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_aggregations_2025_08_period_type_period_start_idx" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_aggregations_20_instance_id_period_type_peri_idx3" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "instance_size_aggregations_20_instance_id_period_type_peri_key3" ON "public"."instance_size_aggregations_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table instance_size_aggregations_2025_08
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations_2025_08" ADD CONSTRAINT "instance_size_aggregations_20_instance_id_period_type_peri_key3" UNIQUE ("instance_id", "period_type", "period_start");

-- ----------------------------
-- Primary Key structure for table instance_size_aggregations_2025_08
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations_2025_08" ADD CONSTRAINT "instance_size_aggregations_2025_08_pkey" PRIMARY KEY ("id", "period_start");

-- ----------------------------
-- Indexes structure for table instance_size_stats_2025_08
-- ----------------------------
CREATE INDEX "idx_instance_size_stats_2025_08_date" ON "public"."instance_size_stats_2025_08" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_stats_2025_08_instance" ON "public"."instance_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_stats_2025_08_instance_date" ON "public"."instance_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_08_collected_date_idx" ON "public"."instance_size_stats_2025_08" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_08_instance_id_collected_date_idx" ON "public"."instance_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "instance_size_stats_2025_08_instance_id_collected_date_idx1" ON "public"."instance_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
) WHERE is_deleted = false;
CREATE INDEX "instance_size_stats_2025_08_instance_id_idx" ON "public"."instance_size_stats_2025_08" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_08_is_deleted_idx" ON "public"."instance_size_stats_2025_08" USING btree (
  "is_deleted" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_08_total_size_mb_idx" ON "public"."instance_size_stats_2025_08" USING btree (
  "total_size_mb" "pg_catalog"."int4_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table instance_size_stats_2025_08
-- ----------------------------
CREATE TRIGGER "instance_size_stats_partition_trigger" BEFORE INSERT ON "public"."instance_size_stats_2025_08"
FOR EACH ROW
EXECUTE PROCEDURE "public"."instance_size_stats_partition_trigger"();

-- ----------------------------
-- Primary Key structure for table instance_size_stats_2025_08
-- ----------------------------
ALTER TABLE "public"."instance_size_stats_2025_08" ADD CONSTRAINT "instance_size_stats_2025_08_pkey" PRIMARY KEY ("id", "collected_date");

-- ----------------------------
-- Foreign Keys structure for table database_size_stats_2025_08
-- ----------------------------
ALTER TABLE "public"."database_size_stats_2025_08" ADD CONSTRAINT "database_size_stats_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_size_aggregations_2025_08
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations_2025_08" ADD CONSTRAINT "instance_size_aggregations_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_size_stats_2025_08
-- ----------------------------
ALTER TABLE "public"."instance_size_stats_2025_08" ADD CONSTRAINT "instance_size_stats_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

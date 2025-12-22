-- PostgreSQL 月分区子表初始化脚本（从 sql/init_postgresql.sql 拆分）
--
-- 仅保留 2025-07 分区。
-- 执行顺序：先执行 sql/init_postgresql.sql，再执行本文件。

-- ----------------------------
-- Table structure for database_size_aggregations_2025_07
-- ----------------------------
CREATE TABLE "public"."database_size_aggregations_2025_07"
PARTITION OF "public"."database_size_aggregations"
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01')
;
COMMENT ON TABLE "public"."database_size_aggregations_2025_07" IS '数据库聚合表分区表 - 2025-07';

-- ----------------------------
-- Table structure for database_size_stats_2025_07
-- ----------------------------
CREATE TABLE "public"."database_size_stats_2025_07"
PARTITION OF "public"."database_size_stats"
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01')
;
COMMENT ON TABLE "public"."database_size_stats_2025_07" IS '数据库统计表分区表 - 2025-07';

-- ----------------------------
-- Table structure for instance_size_aggregations_2025_07
-- ----------------------------
CREATE TABLE "public"."instance_size_aggregations_2025_07"
PARTITION OF "public"."instance_size_aggregations"
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01')
;
COMMENT ON TABLE "public"."instance_size_aggregations_2025_07" IS '实例聚合表分区表 - 2025-07';

-- ----------------------------
-- Table structure for instance_size_stats_2025_07
-- ----------------------------
CREATE TABLE "public"."instance_size_stats_2025_07"
PARTITION OF "public"."instance_size_stats"
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01')
;
COMMENT ON TABLE "public"."instance_size_stats_2025_07" IS '实例统计表分区表 - 2025-07';

-- ----------------------------
-- Indexes structure for table database_size_aggregations_2025_07
-- ----------------------------
CREATE INDEX "database_size_aggregations_2025_07_id_idx" ON "public"."database_size_aggregations_2025_07" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_aggregations_2025_07_period_type_period_start_idx" ON "public"."database_size_aggregations_2025_07" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "database_size_aggregations_20_instance_id_database_name_pe_key3" ON "public"."database_size_aggregations_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_aggregations_20_instance_id_period_type_peri_idx3" ON "public"."database_size_aggregations_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_aggregations_2025_07_instance_db" ON "public"."database_size_aggregations_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_aggregations_2025_07_period" ON "public"."database_size_aggregations_2025_07" USING btree (
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST,
  "period_end" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_aggregations_2025_07_type" ON "public"."database_size_aggregations_2025_07" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table database_size_aggregations_2025_07
-- ----------------------------
ALTER TABLE "public"."database_size_aggregations_2025_07" ADD CONSTRAINT "database_size_aggregations_20_instance_id_database_name_pe_key3" UNIQUE ("instance_id", "database_name", "period_type", "period_start");

-- ----------------------------
-- Indexes structure for table database_size_stats_2025_07
-- ----------------------------
CREATE INDEX "database_size_stats_2025_07_collected_date_idx" ON "public"."database_size_stats_2025_07" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_stats_2025_07_instance_id_collected_date_idx" ON "public"."database_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "database_size_stats_2025_07_instance_id_database_name_colle_key" ON "public"."database_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "database_size_stats_2025_07_instance_id_database_name_idx" ON "public"."database_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_stats_2025_07_date" ON "public"."database_size_stats_2025_07" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_stats_2025_07_instance_date" ON "public"."database_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_database_size_stats_2025_07_instance_db" ON "public"."database_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table database_size_stats_2025_07
-- ----------------------------
CREATE TRIGGER "trg_update_instance_database_last_seen" AFTER INSERT ON "public"."database_size_stats_2025_07"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_instance_database_last_seen"();

-- ----------------------------
-- Uniques structure for table database_size_stats_2025_07
-- ----------------------------
ALTER TABLE "public"."database_size_stats_2025_07" ADD CONSTRAINT "database_size_stats_2025_07_instance_id_database_name_colle_key" UNIQUE ("instance_id", "database_name", "collected_date");

-- ----------------------------
-- Indexes structure for table instance_size_aggregations_2025_07
-- ----------------------------
CREATE INDEX "idx_instance_size_aggregations_2025_07_instance" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_aggregations_2025_07_period" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST,
  "period_end" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_aggregations_2025_07_type" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_aggregations_2025_07_id_idx" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_aggregations_2025_07_period_type_period_start_idx" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_aggregations_20_instance_id_period_type_peri_idx3" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "instance_size_aggregations_20_instance_id_period_type_peri_key3" ON "public"."instance_size_aggregations_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table instance_size_aggregations_2025_07
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations_2025_07" ADD CONSTRAINT "instance_size_aggregations_20_instance_id_period_type_peri_key3" UNIQUE ("instance_id", "period_type", "period_start");

-- ----------------------------
-- Primary Key structure for table instance_size_aggregations_2025_07
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations_2025_07" ADD CONSTRAINT "instance_size_aggregations_2025_07_pkey" PRIMARY KEY ("id", "period_start");

-- ----------------------------
-- Indexes structure for table instance_size_stats_2025_07
-- ----------------------------
CREATE INDEX "idx_instance_size_stats_2025_07_date" ON "public"."instance_size_stats_2025_07" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_stats_2025_07_instance" ON "public"."instance_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_size_stats_2025_07_instance_date" ON "public"."instance_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_07_collected_date_idx" ON "public"."instance_size_stats_2025_07" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_07_instance_id_collected_date_idx" ON "public"."instance_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "instance_size_stats_2025_07_instance_id_collected_date_idx1" ON "public"."instance_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
) WHERE is_deleted = false;
CREATE INDEX "instance_size_stats_2025_07_instance_id_idx" ON "public"."instance_size_stats_2025_07" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_07_is_deleted_idx" ON "public"."instance_size_stats_2025_07" USING btree (
  "is_deleted" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "instance_size_stats_2025_07_total_size_mb_idx" ON "public"."instance_size_stats_2025_07" USING btree (
  "total_size_mb" "pg_catalog"."int4_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table instance_size_stats_2025_07
-- ----------------------------
CREATE TRIGGER "instance_size_stats_partition_trigger" BEFORE INSERT ON "public"."instance_size_stats_2025_07"
FOR EACH ROW
EXECUTE PROCEDURE "public"."instance_size_stats_partition_trigger"();

-- ----------------------------
-- Primary Key structure for table instance_size_stats_2025_07
-- ----------------------------
ALTER TABLE "public"."instance_size_stats_2025_07" ADD CONSTRAINT "instance_size_stats_2025_07_pkey" PRIMARY KEY ("id", "collected_date");

-- ----------------------------
-- Foreign Keys structure for table database_size_stats_2025_07
-- ----------------------------
ALTER TABLE "public"."database_size_stats_2025_07" ADD CONSTRAINT "database_size_stats_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_size_aggregations_2025_07
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations_2025_07" ADD CONSTRAINT "instance_size_aggregations_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_size_stats_2025_07
-- ----------------------------
ALTER TABLE "public"."instance_size_stats_2025_07" ADD CONSTRAINT "instance_size_stats_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

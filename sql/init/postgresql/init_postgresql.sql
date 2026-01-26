-- PostgreSQL 初始化脚本（基于生产库 public schema 导出生成）
--
-- 来源: docs/reports/artifacts/public.sql（Navicat 导出）
-- 说明:
-- 1) 仅包含 DDL（表/索引/约束/触发器/函数/分区等），不包含任何业务数据。
-- 2) 已移除 DROP * 与序列 setval（避免误删、避免把序列起始值对齐到生产数据）。
-- 3) 建议仅用于“全新部署”的空库初始化。

/*
 Navicat Premium Dump SQL

 Source Server         : jt-dbinfocoll-01l
 Source Server Type    : PostgreSQL
 Source Server Version : 150014 (150014)
 Source Host           : 10.10.66.45:5432
 Source Catalog        : whalefall_prod
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 150014 (150014)
 File Encoding         : 65001

 Date: 19/12/2025 16:10:48
*/


-- ----------------------------
-- Type structure for log_level
-- ----------------------------
CREATE TYPE "public"."log_level" AS ENUM (
  'DEBUG',
  'INFO',
  'WARNING',
  'ERROR',
  'CRITICAL'
);

-- ----------------------------
-- Sequence structure for account_change_log_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."account_change_log_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for account_classification_assignments_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."account_classification_assignments_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for account_classifications_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."account_classifications_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for classification_rules_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."classification_rules_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for credentials_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."credentials_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for current_account_sync_data_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."current_account_sync_data_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for database_size_aggregations_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."database_size_aggregations_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for database_size_stats_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."database_size_stats_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for database_type_configs_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."database_type_configs_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for instance_accounts_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."instance_accounts_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for instance_databases_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."instance_databases_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for instance_size_aggregations_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."instance_size_aggregations_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for instance_size_stats_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."instance_size_stats_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for instances_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."instances_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for permission_configs_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."permission_configs_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for sync_instance_records_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."sync_instance_records_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for sync_sessions_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."sync_sessions_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for tags_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."tags_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for unified_logs_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."unified_logs_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for users_id_seq
-- ----------------------------
CREATE SEQUENCE "public"."users_id_seq"
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Table structure for account_change_log
-- ----------------------------
CREATE TABLE "public"."account_change_log" (
  "id" int4 NOT NULL DEFAULT nextval('account_change_log_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "db_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "username" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "change_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "change_time" timestamptz(6) DEFAULT now(),
  "session_id" varchar(128) COLLATE "pg_catalog"."default",
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'success'::character varying,
  "message" text COLLATE "pg_catalog"."default",
  "privilege_diff" jsonb,
  "other_diff" jsonb
)
;

-- ----------------------------
-- Table structure for account_classification_assignments
-- ----------------------------
CREATE TABLE "public"."account_classification_assignments" (
  "id" int4 NOT NULL DEFAULT nextval('account_classification_assignments_id_seq'::regclass),
  "account_id" int4 NOT NULL,
  "classification_id" int4 NOT NULL,
  "assigned_by" int4,
  "assignment_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'auto'::character varying,
  "confidence_score" float4,
  "notes" text COLLATE "pg_catalog"."default",
  "batch_id" varchar(36) COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now(),
  "rule_id" int4,
  "assigned_at" timestamptz(6) NOT NULL
)
;

-- ----------------------------
-- Table structure for account_classifications
-- ----------------------------
CREATE TABLE "public"."account_classifications" (
  "id" int4 NOT NULL DEFAULT nextval('account_classifications_id_seq'::regclass),
  "name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "risk_level" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'medium'::character varying,
  "color" varchar(20) COLLATE "pg_catalog"."default",
  "icon_name" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'fa-tag'::character varying,
  "priority" int4 DEFAULT 0,
  "is_system" bool NOT NULL DEFAULT false,
  "is_active" bool NOT NULL DEFAULT true,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for account_permission
-- ----------------------------
CREATE TABLE "public"."account_permission" (
  "id" int4 NOT NULL DEFAULT nextval('current_account_sync_data_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "db_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "username" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "is_superuser" bool DEFAULT false,
  "global_privileges" jsonb,
  "database_privileges" jsonb,
  "predefined_roles" jsonb,
  "role_attributes" jsonb,
  "database_privileges_pg" jsonb,
  "tablespace_privileges" jsonb,
  "server_roles" jsonb,
  "server_permissions" jsonb,
  "database_roles" jsonb,
  "database_permissions" jsonb,
  "oracle_roles" jsonb,
  "system_privileges" jsonb,
  "tablespace_privileges_oracle" jsonb,
  "type_specific" jsonb,
  "last_sync_time" timestamptz(6) DEFAULT now(),
  "last_change_type" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'add'::character varying,
  "last_change_time" timestamptz(6) DEFAULT now(),
  "instance_account_id" int4 NOT NULL,
  "is_locked" bool NOT NULL
)
;

-- ----------------------------
-- Table structure for classification_rules
-- ----------------------------
CREATE TABLE "public"."classification_rules" (
  "id" int4 NOT NULL DEFAULT nextval('classification_rules_id_seq'::regclass),
  "classification_id" int4 NOT NULL,
  "db_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "rule_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "rule_expression" text COLLATE "pg_catalog"."default" NOT NULL,
  "is_active" bool NOT NULL DEFAULT true,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for credentials
-- ----------------------------
CREATE TABLE "public"."credentials" (
  "id" int4 NOT NULL DEFAULT nextval('credentials_id_seq'::regclass),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "credential_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "db_type" varchar(50) COLLATE "pg_catalog"."default",
  "username" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "password" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "category_id" int4,
  "is_active" bool NOT NULL DEFAULT true,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now(),
  "deleted_at" timestamptz(6)
)
;

-- ----------------------------
-- Table structure for database_type_configs
-- ----------------------------
CREATE TABLE "public"."database_type_configs" (
  "id" int4 NOT NULL DEFAULT nextval('database_type_configs_id_seq'::regclass),
  "name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "display_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "driver" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "default_port" int4 NOT NULL,
  "default_schema" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "connection_timeout" int4 DEFAULT 30,
  "description" text COLLATE "pg_catalog"."default",
  "icon" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'fa-database'::character varying,
  "color" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'primary'::character varying,
  "features" text COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "is_system" bool DEFAULT false,
  "sort_order" int4 DEFAULT 0,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for instance_accounts
-- ----------------------------
CREATE TABLE "public"."instance_accounts" (
  "id" int4 NOT NULL DEFAULT nextval('instance_accounts_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "username" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "db_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "is_active" bool NOT NULL DEFAULT true,
  "deleted_at" timestamptz(6),
  "created_at" timestamptz(6) NOT NULL DEFAULT now(),
  "updated_at" timestamptz(6) NOT NULL DEFAULT now()
)
;

-- ----------------------------
-- Table structure for instance_databases
-- ----------------------------
CREATE TABLE "public"."instance_databases" (
  "id" int4 NOT NULL DEFAULT nextval('instance_databases_id_seq'::regclass),
  "instance_id" int4 NOT NULL,
  "database_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "is_active" bool NOT NULL DEFAULT true,
  "first_seen_date" date NOT NULL DEFAULT CURRENT_DATE,
  "last_seen_date" date NOT NULL DEFAULT CURRENT_DATE,
  "deleted_at" timestamptz(6),
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;
COMMENT ON COLUMN "public"."instance_databases"."instance_id" IS '实例ID';
COMMENT ON COLUMN "public"."instance_databases"."database_name" IS '数据库名称';
COMMENT ON COLUMN "public"."instance_databases"."is_active" IS '数据库是否活跃（未删除）';
COMMENT ON COLUMN "public"."instance_databases"."first_seen_date" IS '首次发现日期';
COMMENT ON COLUMN "public"."instance_databases"."last_seen_date" IS '最后发现日期';
COMMENT ON COLUMN "public"."instance_databases"."deleted_at" IS '删除时间';
COMMENT ON TABLE "public"."instance_databases" IS '实例-数据库关系表，维护数据库的存在状态';

-- ----------------------------
-- Table structure for instance_tags
-- ----------------------------
CREATE TABLE "public"."instance_tags" (
  "instance_id" int4 NOT NULL,
  "tag_id" int4 NOT NULL,
  "created_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for instances
-- ----------------------------
CREATE TABLE "public"."instances" (
  "id" int4 NOT NULL DEFAULT nextval('instances_id_seq'::regclass),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "db_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "host" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "port" int4 NOT NULL,
  "database_name" varchar(255) COLLATE "pg_catalog"."default",
  "database_version" varchar(1000) COLLATE "pg_catalog"."default",
  "main_version" varchar(20) COLLATE "pg_catalog"."default",
  "detailed_version" varchar(50) COLLATE "pg_catalog"."default",
  "sync_count" int4 NOT NULL DEFAULT 0,
  "credential_id" int4,
  "description" text COLLATE "pg_catalog"."default",
  "is_active" bool NOT NULL DEFAULT true,
  "last_connected" timestamptz(6),
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now(),
  "deleted_at" timestamptz(6)
)
;

-- ----------------------------
-- Table structure for permission_configs
-- ----------------------------
CREATE TABLE "public"."permission_configs" (
  "id" int4 NOT NULL DEFAULT nextval('permission_configs_id_seq'::regclass),
  "db_type" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "category" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "permission_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "sort_order" int4 DEFAULT 0,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for sync_instance_records
-- ----------------------------
CREATE TABLE "public"."sync_instance_records" (
  "id" int4 NOT NULL DEFAULT nextval('sync_instance_records_id_seq'::regclass),
  "session_id" varchar(36) COLLATE "pg_catalog"."default" NOT NULL,
  "instance_id" int4 NOT NULL,
  "instance_name" varchar(255) COLLATE "pg_catalog"."default",
  "sync_category" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'account'::character varying,
  "status" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'pending'::character varying,
  "started_at" timestamptz(6),
  "completed_at" timestamptz(6),
  "items_synced" int4 DEFAULT 0,
  "items_created" int4 DEFAULT 0,
  "items_updated" int4 DEFAULT 0,
  "items_deleted" int4 DEFAULT 0,
  "error_message" text COLLATE "pg_catalog"."default",
  "sync_details" jsonb,
  "created_at" timestamptz(6) DEFAULT now()
)
;
COMMENT ON COLUMN "public"."sync_instance_records"."sync_category" IS '同步分类: account(账户同步), capacity(容量同步), config(配置同步), aggregation(聚合统计), other(其他)';
COMMENT ON COLUMN "public"."sync_instance_records"."items_synced" IS '同步的项目数量（通用字段，支持账户、容量、聚合等）';
COMMENT ON COLUMN "public"."sync_instance_records"."items_created" IS '创建的项目数量（通用字段，支持账户、容量、聚合等）';
COMMENT ON COLUMN "public"."sync_instance_records"."items_updated" IS '更新的项目数量（通用字段，支持账户、容量、聚合等）';
COMMENT ON COLUMN "public"."sync_instance_records"."items_deleted" IS '删除的项目数量（通用字段，支持账户、容量、聚合等）';

-- ----------------------------
-- Table structure for sync_sessions
-- ----------------------------
CREATE TABLE "public"."sync_sessions" (
  "id" int4 NOT NULL DEFAULT nextval('sync_sessions_id_seq'::regclass),
  "session_id" varchar(36) COLLATE "pg_catalog"."default" NOT NULL,
  "sync_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "sync_category" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'account'::character varying,
  "status" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'running'::character varying,
  "started_at" timestamptz(6) NOT NULL DEFAULT now(),
  "completed_at" timestamptz(6),
  "total_instances" int4 DEFAULT 0,
  "successful_instances" int4 DEFAULT 0,
  "failed_instances" int4 DEFAULT 0,
  "created_by" int4,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;
COMMENT ON COLUMN "public"."sync_sessions"."sync_type" IS '同步操作方式: manual_single(手动单台), manual_batch(手动批量), manual_task(手动任务), scheduled_task(定时任务)';
COMMENT ON COLUMN "public"."sync_sessions"."sync_category" IS '同步分类: account(账户同步), capacity(容量同步), config(配置同步), aggregation(聚合统计), other(其他)';

-- ----------------------------
-- Table structure for tags
-- ----------------------------
CREATE TABLE "public"."tags" (
  "id" int4 NOT NULL DEFAULT nextval('tags_id_seq'::regclass),
  "name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "display_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "category" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "color" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'primary'::character varying,
  "is_active" bool NOT NULL DEFAULT true,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for unified_logs
-- ----------------------------
CREATE TABLE "public"."unified_logs" (
  "id" int4 NOT NULL DEFAULT nextval('unified_logs_id_seq'::regclass),
  "timestamp" timestamptz(6) NOT NULL,
  "level" "public"."log_level" NOT NULL,
  "module" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "message" text COLLATE "pg_catalog"."default" NOT NULL,
  "traceback" text COLLATE "pg_catalog"."default",
  "context" jsonb,
  "created_at" timestamptz(6) NOT NULL DEFAULT now()
)
;

-- ----------------------------
-- Table structure for users
-- ----------------------------
CREATE TABLE "public"."users" (
  "id" int4 NOT NULL DEFAULT nextval('users_id_seq'::regclass),
  "username" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "password" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "role" varchar(50) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'user'::character varying,
  "created_at" timestamptz(6) NOT NULL DEFAULT now(),
  "last_login" timestamptz(6),
  "is_active" bool NOT NULL DEFAULT true
)
;

-- ----------------------------
-- Table structure for database_size_aggregations
-- ----------------------------
CREATE TABLE "public"."database_size_aggregations" (
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
  "calculated_at" timestamptz(6) NOT NULL,
  "created_at" timestamptz(6) NOT NULL
)
PARTITION BY RANGE (
  "period_start" "pg_catalog"."date_ops"
)
;
COMMENT ON TABLE "public"."database_size_aggregations" IS '数据库大小聚合统计表（按月分区）';

-- ----------------------------
-- Table structure for database_size_stats
-- ----------------------------
CREATE TABLE "public"."database_size_stats" (
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
PARTITION BY RANGE (
  "collected_date" "pg_catalog"."date_ops"
)
;
COMMENT ON TABLE "public"."database_size_stats" IS '数据库大小统计表（按月分区）';

-- ----------------------------
-- Table structure for instance_size_aggregations
-- ----------------------------
CREATE TABLE "public"."instance_size_aggregations" (
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
  "calculated_at" timestamptz(6) NOT NULL,
  "created_at" timestamptz(6) NOT NULL
)
PARTITION BY RANGE (
  "period_start" "pg_catalog"."date_ops"
)
;
COMMENT ON TABLE "public"."instance_size_aggregations" IS '实例大小聚合统计表（按月分区）';

-- ----------------------------
-- Table structure for instance_size_stats
-- ----------------------------
CREATE TABLE "public"."instance_size_stats" (
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
PARTITION BY RANGE (
  "collected_date" "pg_catalog"."date_ops"
)
;
COMMENT ON COLUMN "public"."instance_size_stats"."instance_id" IS '实例ID';
COMMENT ON COLUMN "public"."instance_size_stats"."total_size_mb" IS '实例总大小（MB）';
COMMENT ON COLUMN "public"."instance_size_stats"."database_count" IS '数据库数量';
COMMENT ON COLUMN "public"."instance_size_stats"."collected_date" IS '采集日期';
COMMENT ON COLUMN "public"."instance_size_stats"."collected_at" IS '采集时间';
COMMENT ON COLUMN "public"."instance_size_stats"."is_deleted" IS '是否已删除';
COMMENT ON COLUMN "public"."instance_size_stats"."deleted_at" IS '删除时间';
COMMENT ON TABLE "public"."instance_size_stats" IS '实例大小统计表（按月分区）';

-- ----------------------------
-- Function structure for auto_create_database_size_partition
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."auto_create_database_size_partition"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
DECLARE
    partition_date DATE;
BEGIN
    partition_date := DATE_TRUNC('month', NEW.collected_date);

    -- 尝试创建分区（如果不存在）
    PERFORM create_database_size_partition(partition_date);

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to create partition for date %: %', partition_date, SQLERRM;
        RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for cleanup_old_database_size_partitions
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."cleanup_old_database_size_partitions"("retention_months" int4=12)
  RETURNS "pg_catalog"."void" AS $BODY$
DECLARE
    cutoff_date DATE;
    partition_record RECORD;
BEGIN
    cutoff_date := CURRENT_DATE - (retention_months || ' months')::INTERVAL;

    -- 查找需要清理的分区
    FOR partition_record IN
        SELECT tablename
        FROM pg_tables
        WHERE tablename LIKE 'database_size_stats_%'
        AND tablename ~ '^\d{4}_\d{2}$'
    LOOP
        -- 从表名提取日期
        DECLARE
            year_month TEXT;
            partition_date DATE;
        BEGIN
            year_month := substring(partition_record.tablename from 'database_size_stats_(\d{4}_\d{2})$');
            partition_date := TO_DATE(year_month, 'YYYY_MM');

            -- 如果分区日期早于截止日期，则删除
            IF partition_date < cutoff_date THEN
                EXECUTE format('DROP TABLE %I', partition_record.tablename);
                RAISE NOTICE 'Cleaned up old partition: %', partition_record.tablename;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Error processing partition %: %', partition_record.tablename, SQLERRM;
        END;
    END LOOP;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for create_database_size_partition
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."create_database_size_partition"("partition_date" date)
  RETURNS "pg_catalog"."void" AS $BODY$
DECLARE
    partition_name TEXT;
    partition_start DATE;
    partition_end DATE;
BEGIN
    partition_start := DATE_TRUNC('month', partition_date);
    partition_end := partition_start + '1 month'::INTERVAL;
    partition_name := 'database_size_stats_' || TO_CHAR(partition_start, 'YYYY_MM');

    -- 检查分区是否已存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE tablename = partition_name
    ) THEN
        -- 创建分区
        EXECUTE format('
            CREATE TABLE %I
            PARTITION OF database_size_stats
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );

        -- 添加注释
        EXECUTE format('
            COMMENT ON TABLE %I IS ''数据库大小统计分区表 - %s''',
            partition_name, TO_CHAR(partition_start, 'YYYY-MM')
        );

        RAISE NOTICE 'Created partition: % for period % to %',
            partition_name, partition_start, partition_end;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for create_instance_size_aggregations_partitions
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."create_instance_size_aggregations_partitions"()
  RETURNS "pg_catalog"."void" AS $BODY$
DECLARE
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    next_year INTEGER;
    next_month INTEGER;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 当前月份分区
    partition_name := 'instance_size_aggregations_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;

    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);

    -- 计算下个月
    IF current_month = 12 THEN
        next_year := current_year + 1;
        next_month := 1;
    ELSE
        next_year := current_year;
        next_month := current_month + 1;
    END IF;

    -- 下个月分区
    partition_name := 'instance_size_aggregations_' || next_year || '_' || LPAD(next_month::TEXT, 2, '0');
    start_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE;

    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);

    RAISE NOTICE 'Created instance_size_aggregations partitions for % and %',
        (current_year || '-' || LPAD(current_month::TEXT, 2, '0')),
        (next_year || '-' || LPAD(next_month::TEXT, 2, '0'));
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for create_instance_size_stats_partitions
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."create_instance_size_stats_partitions"()
  RETURNS "pg_catalog"."void" AS $BODY$
DECLARE
    current_year INTEGER;
    current_month INTEGER;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    -- 获取当前年月
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month := EXTRACT(MONTH FROM CURRENT_DATE);

    -- 创建当前月份的分区
    partition_name := 'instance_size_stats_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := current_year || '-' || LPAD(current_month::TEXT, 2, '0') || '-01';
    end_date := CASE
        WHEN current_month = 12 THEN (current_year + 1) || '-01-01'
        ELSE current_year || '-' || LPAD((current_month + 1)::TEXT, 2, '0') || '-01'
    END;

    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date);

    -- 创建下个月份的分区
    IF current_month = 12 THEN
        current_year := current_year + 1;
        current_month := 1;
    ELSE
        current_month := current_month + 1;
    END IF;

    partition_name := 'instance_size_stats_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := current_year || '-' || LPAD(current_month::TEXT, 2, '0') || '-01';
    end_date := CASE
        WHEN current_month = 12 THEN (current_year + 1) || '-01-01'
        ELSE current_year || '-' || LPAD((current_month + 1)::TEXT, 2, '0') || '-01'
    END;

    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date);

    RAISE NOTICE 'Created instance_size_stats partitions for % and %',
        (current_year || '-' || LPAD((current_month - 1)::TEXT, 2, '0')),
        (current_year || '-' || LPAD(current_month::TEXT, 2, '0'));
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for detect_deleted_databases
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."detect_deleted_databases"("p_instance_id" int4)
  RETURNS "pg_catalog"."int4" AS $BODY$
DECLARE
    deleted_count INTEGER := 0;
    db_record RECORD;
    latest_collection_date DATE;
BEGIN
    -- 获取该实例最新的数据采集日期
    SELECT MAX(collected_date) INTO latest_collection_date
    FROM database_size_stats
    WHERE instance_id = p_instance_id;

    -- 查找在最新采集日期没有数据的活跃数据库
    FOR db_record IN
        SELECT database_name
        FROM instance_databases
        WHERE instance_id = p_instance_id
        AND is_active = TRUE
        AND database_name NOT IN (
            SELECT DISTINCT database_name
            FROM database_size_stats
            WHERE instance_id = p_instance_id
            AND collected_date = latest_collection_date
        )
    LOOP
        -- 标记为已删除
        PERFORM mark_database_as_deleted(p_instance_id, db_record.database_name);
        deleted_count := deleted_count + 1;
    END LOOP;

    RETURN deleted_count;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for drop_database_size_partition
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."drop_database_size_partition"("partition_date" date)
  RETURNS "pg_catalog"."void" AS $BODY$
DECLARE
    partition_name TEXT;
    partition_start DATE;
BEGIN
    partition_start := DATE_TRUNC('month', partition_date);
    partition_name := 'database_size_stats_' || TO_CHAR(partition_start, 'YYYY_MM');

    -- 检查分区是否存在
    IF EXISTS (
        SELECT 1 FROM pg_tables
        WHERE tablename = partition_name
    ) THEN
        -- 删除分区
        EXECUTE format('DROP TABLE %I', partition_name);
        RAISE NOTICE 'Dropped partition: %', partition_name;
    ELSE
        RAISE NOTICE 'Partition % does not exist', partition_name;
    END IF;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for instance_size_stats_partition_trigger
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."instance_size_stats_partition_trigger"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
DECLARE
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
    year_val INTEGER;
    month_val INTEGER;
BEGIN
    -- 从 collected_date 提取年月
    year_val := EXTRACT(YEAR FROM NEW.collected_date);
    month_val := EXTRACT(MONTH FROM NEW.collected_date);

    -- 构建分区名称
    partition_name := 'instance_size_stats_' || year_val || '_' || LPAD(month_val::TEXT, 2, '0');

    -- 检查分区是否存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE tablename = partition_name
    ) THEN
        -- 创建分区
        start_date := year_val || '-' || LPAD(month_val::TEXT, 2, '0') || '-01';
        end_date := CASE
            WHEN month_val = 12 THEN (year_val + 1) || '-01-01'
            ELSE year_val || '-' || LPAD((month_val + 1)::TEXT, 2, '0') || '-01'
        END;

        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date);

        RAISE NOTICE 'Created partition % for date %', partition_name, NEW.collected_date;
    END IF;

    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for mark_database_as_deleted
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."mark_database_as_deleted"("p_instance_id" int4, "p_database_name" varchar)
  RETURNS "pg_catalog"."void" AS $BODY$
BEGIN
    UPDATE instance_databases
    SET is_active = FALSE,
        deleted_at = NOW(),
        updated_at = NOW()
    WHERE instance_id = p_instance_id
    AND database_name = p_database_name;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for mysql_decode_db_name
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."mysql_decode_db_name"("raw_name" text)
  RETURNS "pg_catalog"."text" AS $BODY$
  DECLARE
      matched text[];
      chunk   text;
      replacement text;
      result  text := raw_name;
  BEGIN
      LOOP
          matched := regexp_match(result, '@([0-9A-Fa-f]{4})');
          EXIT WHEN matched IS NULL;

          chunk := upper(matched[1]);
          BEGIN
              IF chunk = '0000' THEN
                  replacement := '';
              ELSE
                  replacement := convert_from(decode(chunk, 'hex'), 'UTF8');
              END IF;
          EXCEPTION WHEN others THEN
              -- 出问题就原样保留
              replacement := '@' || chunk;
          END;

          result := regexp_replace(result, '@' || chunk, replacement, 'g');
      END LOOP;

      RETURN result;
  END;
  $BODY$
  LANGUAGE plpgsql IMMUTABLE
  COST 100;

-- ----------------------------
-- Function structure for update_instance_database_last_seen
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."update_instance_database_last_seen"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
BEGIN
    UPDATE instance_databases
    SET last_seen_date = NEW.collected_date,
        updated_at = NOW(),
        is_active = TRUE,
        deleted_at = NULL
    WHERE instance_id = NEW.instance_id
      AND database_name = NEW.database_name;

    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for update_updated_at_column
-- ----------------------------
CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."account_change_log_id_seq"
OWNED BY "public"."account_change_log"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."account_classification_assignments_id_seq"
OWNED BY "public"."account_classification_assignments"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."account_classifications_id_seq"
OWNED BY "public"."account_classifications"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."classification_rules_id_seq"
OWNED BY "public"."classification_rules"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."credentials_id_seq"
OWNED BY "public"."credentials"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."current_account_sync_data_id_seq"
OWNED BY "public"."account_permission"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."database_size_aggregations_id_seq"
OWNED BY "public"."database_size_aggregations"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."database_size_stats_id_seq"
OWNED BY "public"."database_size_stats"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."database_type_configs_id_seq"
OWNED BY "public"."database_type_configs"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."instance_accounts_id_seq"
OWNED BY "public"."instance_accounts"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."instance_databases_id_seq"
OWNED BY "public"."instance_databases"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."instance_size_aggregations_id_seq"
OWNED BY "public"."instance_size_aggregations"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."instance_size_stats_id_seq"
OWNED BY "public"."instance_size_stats"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."instances_id_seq"
OWNED BY "public"."instances"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."permission_configs_id_seq"
OWNED BY "public"."permission_configs"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."sync_instance_records_id_seq"
OWNED BY "public"."sync_instance_records"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."sync_sessions_id_seq"
OWNED BY "public"."sync_sessions"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."tags_id_seq"
OWNED BY "public"."tags"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."unified_logs_id_seq"
OWNED BY "public"."unified_logs"."id";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."users_id_seq"
OWNED BY "public"."users"."id";

-- ----------------------------
-- Indexes structure for table account_change_log
-- ----------------------------
CREATE INDEX "idx_account_change_log_change_time" ON "public"."account_change_log" USING btree (
  "change_time" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_account_change_log_db_type" ON "public"."account_change_log" USING btree (
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_account_change_log_instance_id" ON "public"."account_change_log" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_account_change_log_username" ON "public"."account_change_log" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_change_type_time" ON "public"."account_change_log" USING btree (
  "change_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "change_time" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_instance_dbtype_username_time" ON "public"."account_change_log" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "change_time" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_username_time" ON "public"."account_change_log" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "change_time" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table account_change_log
-- ----------------------------
ALTER TABLE "public"."account_change_log" ADD CONSTRAINT "account_change_log_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table account_classification_assignments
-- ----------------------------
CREATE INDEX "idx_account_classification_assignments_account_id" ON "public"."account_classification_assignments" USING btree (
  "account_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_account_classification_assignments_classification_id" ON "public"."account_classification_assignments" USING btree (
  "classification_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_account_classification_assignments_is_active" ON "public"."account_classification_assignments" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table account_classification_assignments
-- ----------------------------
CREATE TRIGGER "update_account_classification_assignments_updated_at" BEFORE UPDATE ON "public"."account_classification_assignments"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table account_classification_assignments
-- ----------------------------
ALTER TABLE "public"."account_classification_assignments" ADD CONSTRAINT "unique_account_classification_batch" UNIQUE ("account_id", "classification_id", "batch_id");

-- ----------------------------
-- Primary Key structure for table account_classification_assignments
-- ----------------------------
ALTER TABLE "public"."account_classification_assignments" ADD CONSTRAINT "account_classification_assignments_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Triggers structure for table account_classifications
-- ----------------------------
CREATE TRIGGER "update_account_classifications_updated_at" BEFORE UPDATE ON "public"."account_classifications"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table account_classifications
-- ----------------------------
ALTER TABLE "public"."account_classifications" ADD CONSTRAINT "account_classifications_name_key" UNIQUE ("name");

-- ----------------------------
-- Primary Key structure for table account_classifications
-- ----------------------------
ALTER TABLE "public"."account_classifications" ADD CONSTRAINT "account_classifications_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table account_permission
-- ----------------------------
CREATE INDEX "idx_instance_dbtype" ON "public"."account_permission" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_last_change_time" ON "public"."account_permission" USING btree (
  "last_change_time" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_last_sync_time" ON "public"."account_permission" USING btree (
  "last_sync_time" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_username" ON "public"."account_permission" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "ix_account_permission_is_locked" ON "public"."account_permission" USING btree (
  "is_locked" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "uq_current_account_sync" ON "public"."account_permission" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table account_permission
-- ----------------------------
ALTER TABLE "public"."account_permission" ADD CONSTRAINT "account_permission_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Triggers structure for table classification_rules
-- ----------------------------
CREATE TRIGGER "update_classification_rules_updated_at" BEFORE UPDATE ON "public"."classification_rules"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table classification_rules
-- ----------------------------
ALTER TABLE "public"."classification_rules" ADD CONSTRAINT "classification_rules_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table credentials
-- ----------------------------
CREATE INDEX "ix_credentials_credential_type" ON "public"."credentials" USING btree (
  "credential_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "ix_credentials_db_type" ON "public"."credentials" USING btree (
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "ix_credentials_name" ON "public"."credentials" USING btree (
  "name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table credentials
-- ----------------------------
CREATE TRIGGER "update_credentials_updated_at" BEFORE UPDATE ON "public"."credentials"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table credentials
-- ----------------------------
ALTER TABLE "public"."credentials" ADD CONSTRAINT "credentials_name_key" UNIQUE ("name");

-- ----------------------------
-- Primary Key structure for table credentials
-- ----------------------------
ALTER TABLE "public"."credentials" ADD CONSTRAINT "credentials_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Triggers structure for table database_type_configs
-- ----------------------------
CREATE TRIGGER "update_database_type_configs_updated_at" BEFORE UPDATE ON "public"."database_type_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table database_type_configs
-- ----------------------------
ALTER TABLE "public"."database_type_configs" ADD CONSTRAINT "database_type_configs_name_key" UNIQUE ("name");

-- ----------------------------
-- Primary Key structure for table database_type_configs
-- ----------------------------
ALTER TABLE "public"."database_type_configs" ADD CONSTRAINT "database_type_configs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table instance_accounts
-- ----------------------------
CREATE INDEX "ix_instance_accounts_active" ON "public"."instance_accounts" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_accounts_username" ON "public"."instance_accounts" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table instance_accounts
-- ----------------------------
ALTER TABLE "public"."instance_accounts" ADD CONSTRAINT "uq_instance_account_instance_username" UNIQUE ("instance_id", "db_type", "username");

-- ----------------------------
-- Primary Key structure for table instance_accounts
-- ----------------------------
ALTER TABLE "public"."instance_accounts" ADD CONSTRAINT "instance_accounts_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table instance_databases
-- ----------------------------
CREATE INDEX "ix_instance_databases_active" ON "public"."instance_databases" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_databases_database_name" ON "public"."instance_databases" USING btree (
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_databases_instance_id" ON "public"."instance_databases" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_databases_last_seen" ON "public"."instance_databases" USING btree (
  "last_seen_date" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table instance_databases
-- ----------------------------
ALTER TABLE "public"."instance_databases" ADD CONSTRAINT "instance_databases_instance_id_database_name_key" UNIQUE ("instance_id", "database_name");

-- ----------------------------
-- Primary Key structure for table instance_databases
-- ----------------------------
ALTER TABLE "public"."instance_databases" ADD CONSTRAINT "instance_databases_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Primary Key structure for table instance_tags
-- ----------------------------
ALTER TABLE "public"."instance_tags" ADD CONSTRAINT "instance_tags_pkey" PRIMARY KEY ("instance_id", "tag_id");

-- ----------------------------
-- Indexes structure for table instances
-- ----------------------------
CREATE INDEX "ix_instances_db_type" ON "public"."instances" USING btree (
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "ix_instances_name" ON "public"."instances" USING btree (
  "name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table instances
-- ----------------------------
CREATE TRIGGER "update_instances_updated_at" BEFORE UPDATE ON "public"."instances"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table instances
-- ----------------------------
ALTER TABLE "public"."instances" ADD CONSTRAINT "instances_name_key" UNIQUE ("name");

-- ----------------------------
-- Primary Key structure for table instances
-- ----------------------------
ALTER TABLE "public"."instances" ADD CONSTRAINT "instances_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table permission_configs
-- ----------------------------
CREATE INDEX "idx_permission_config_category" ON "public"."permission_configs" USING btree (
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_permission_config_db_type" ON "public"."permission_configs" USING btree (
  "db_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table permission_configs
-- ----------------------------
CREATE TRIGGER "update_permission_configs_updated_at" BEFORE UPDATE ON "public"."permission_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table permission_configs
-- ----------------------------
ALTER TABLE "public"."permission_configs" ADD CONSTRAINT "uq_permission_config" UNIQUE ("db_type", "category", "permission_name");

-- ----------------------------
-- Primary Key structure for table permission_configs
-- ----------------------------
ALTER TABLE "public"."permission_configs" ADD CONSTRAINT "permission_configs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table sync_instance_records
-- ----------------------------
CREATE INDEX "idx_sync_instance_records_created_at" ON "public"."sync_instance_records" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_instance_records_instance_id" ON "public"."sync_instance_records" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_instance_records_session_id" ON "public"."sync_instance_records" USING btree (
  "session_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_instance_records_status" ON "public"."sync_instance_records" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_instance_records_sync_category" ON "public"."sync_instance_records" USING btree (
  "sync_category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Checks structure for table sync_instance_records
-- ----------------------------
ALTER TABLE "public"."sync_instance_records" ADD CONSTRAINT "sync_instance_records_status_check" CHECK (status::text = ANY (ARRAY['pending'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying]::text[]));
ALTER TABLE "public"."sync_instance_records" ADD CONSTRAINT "sync_instance_records_sync_category_check" CHECK (sync_category::text = ANY (ARRAY['account'::character varying, 'capacity'::character varying, 'config'::character varying, 'aggregation'::character varying, 'other'::character varying]::text[]));

-- ----------------------------
-- Primary Key structure for table sync_instance_records
-- ----------------------------
ALTER TABLE "public"."sync_instance_records" ADD CONSTRAINT "sync_instance_records_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table sync_sessions
-- ----------------------------
CREATE INDEX "idx_sync_sessions_created_at" ON "public"."sync_sessions" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_sessions_session_id" ON "public"."sync_sessions" USING btree (
  "session_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_sessions_status" ON "public"."sync_sessions" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_sessions_sync_category" ON "public"."sync_sessions" USING btree (
  "sync_category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sync_sessions_sync_type" ON "public"."sync_sessions" USING btree (
  "sync_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table sync_sessions
-- ----------------------------
CREATE TRIGGER "update_sync_sessions_updated_at" BEFORE UPDATE ON "public"."sync_sessions"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table sync_sessions
-- ----------------------------
ALTER TABLE "public"."sync_sessions" ADD CONSTRAINT "sync_sessions_session_id_key" UNIQUE ("session_id");

-- ----------------------------
-- Checks structure for table sync_sessions
-- ----------------------------
ALTER TABLE "public"."sync_sessions" ADD CONSTRAINT "sync_sessions_status_check" CHECK (status::text = ANY (ARRAY['running'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying]::text[]));
ALTER TABLE "public"."sync_sessions" ADD CONSTRAINT "sync_sessions_sync_type_check" CHECK (sync_type::text = ANY (ARRAY['manual_single'::character varying, 'manual_batch'::character varying, 'manual_task'::character varying, 'scheduled_task'::character varying]::text[]));
ALTER TABLE "public"."sync_sessions" ADD CONSTRAINT "sync_sessions_sync_category_check" CHECK (sync_category::text = ANY (ARRAY['account'::character varying, 'capacity'::character varying, 'config'::character varying, 'aggregation'::character varying, 'other'::character varying]::text[]));

-- ----------------------------
-- Primary Key structure for table sync_sessions
-- ----------------------------
ALTER TABLE "public"."sync_sessions" ADD CONSTRAINT "sync_sessions_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table tags
-- ----------------------------
CREATE INDEX "ix_tags_category" ON "public"."tags" USING btree (
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "ix_tags_name" ON "public"."tags" USING btree (
  "name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table tags
-- ----------------------------
CREATE TRIGGER "update_tags_updated_at" BEFORE UPDATE ON "public"."tags"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table tags
-- ----------------------------
ALTER TABLE "public"."tags" ADD CONSTRAINT "tags_name_key" UNIQUE ("name");

-- ----------------------------
-- Primary Key structure for table tags
-- ----------------------------
ALTER TABLE "public"."tags" ADD CONSTRAINT "tags_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table unified_logs
-- ----------------------------
CREATE INDEX "idx_level_timestamp" ON "public"."unified_logs" USING btree (
  "level" "pg_catalog"."enum_ops" ASC NULLS LAST,
  "timestamp" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_timestamp_level_module" ON "public"."unified_logs" USING btree (
  "timestamp" "pg_catalog"."timestamptz_ops" ASC NULLS LAST,
  "level" "pg_catalog"."enum_ops" ASC NULLS LAST,
  "module" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_timestamp_module" ON "public"."unified_logs" USING btree (
  "timestamp" "pg_catalog"."timestamptz_ops" ASC NULLS LAST,
  "module" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_unified_logs_created_at" ON "public"."unified_logs" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_unified_logs_level" ON "public"."unified_logs" USING btree (
  "level" "pg_catalog"."enum_ops" ASC NULLS LAST
);
CREATE INDEX "idx_unified_logs_module" ON "public"."unified_logs" USING btree (
  "module" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_unified_logs_timestamp" ON "public"."unified_logs" USING btree (
  "timestamp" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);

-- ----------------------------
-- Checks structure for table unified_logs
-- ----------------------------
ALTER TABLE "public"."unified_logs" ADD CONSTRAINT "unified_logs_level_check" CHECK (level::text = ANY (ARRAY['DEBUG'::character varying::text, 'INFO'::character varying::text, 'WARNING'::character varying::text, 'ERROR'::character varying::text, 'CRITICAL'::character varying::text]));

-- ----------------------------
-- Primary Key structure for table unified_logs
-- ----------------------------
ALTER TABLE "public"."unified_logs" ADD CONSTRAINT "unified_logs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table users
-- ----------------------------
CREATE INDEX "ix_users_username" ON "public"."users" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_username_key" UNIQUE ("username");

-- ----------------------------
-- Primary Key structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table database_size_aggregations
-- ----------------------------
CREATE INDEX "ix_database_size_aggregations_id" ON "public"."database_size_aggregations" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "ix_database_size_aggregations_instance_period" ON "public"."database_size_aggregations" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "ix_database_size_aggregations_period_type" ON "public"."database_size_aggregations" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table database_size_aggregations
-- ----------------------------
ALTER TABLE "public"."database_size_aggregations" ADD CONSTRAINT "uq_database_size_aggregation" UNIQUE ("instance_id", "database_name", "period_type", "period_start");

-- ----------------------------
-- Indexes structure for table database_size_stats
-- ----------------------------
CREATE INDEX "ix_database_size_stats_collected_date" ON "public"."database_size_stats" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "ix_database_size_stats_instance_date" ON "public"."database_size_stats" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "ix_database_size_stats_instance_db" ON "public"."database_size_stats" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "database_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table database_size_stats
-- ----------------------------
CREATE TRIGGER "trg_update_instance_database_last_seen" AFTER INSERT ON "public"."database_size_stats"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_instance_database_last_seen"();

-- ----------------------------
-- Uniques structure for table database_size_stats
-- ----------------------------
ALTER TABLE "public"."database_size_stats" ADD CONSTRAINT "uq_daily_database_size" UNIQUE ("instance_id", "database_name", "collected_date");

-- ----------------------------
-- Indexes structure for table instance_size_aggregations
-- ----------------------------
CREATE INDEX "ix_instance_size_aggregations_id" ON "public"."instance_size_aggregations" USING btree (
  "id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_size_aggregations_instance_period" ON "public"."instance_size_aggregations" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_size_aggregations_period_type" ON "public"."instance_size_aggregations" USING btree (
  "period_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "period_start" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table instance_size_aggregations
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations" ADD CONSTRAINT "uq_instance_size_aggregation" UNIQUE ("instance_id", "period_type", "period_start");

-- ----------------------------
-- Primary Key structure for table instance_size_aggregations
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations" ADD CONSTRAINT "instance_size_aggregations_pkey" PRIMARY KEY ("id", "period_start");

-- ----------------------------
-- Indexes structure for table instance_size_stats
-- ----------------------------
CREATE INDEX "ix_instance_size_stats_collected_date" ON "public"."instance_size_stats" USING btree (
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_size_stats_deleted" ON "public"."instance_size_stats" USING btree (
  "is_deleted" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_size_stats_instance_date" ON "public"."instance_size_stats" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_size_stats_instance_id" ON "public"."instance_size_stats" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "ix_instance_size_stats_total_size" ON "public"."instance_size_stats" USING btree (
  "total_size_mb" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "uq_instance_size_stats_instance_date" ON "public"."instance_size_stats" USING btree (
  "instance_id" "pg_catalog"."int4_ops" ASC NULLS LAST,
  "collected_date" "pg_catalog"."date_ops" ASC NULLS LAST
) WHERE is_deleted = false;

-- ----------------------------
-- Triggers structure for table instance_size_stats
-- ----------------------------
CREATE TRIGGER "instance_size_stats_partition_trigger" BEFORE INSERT ON "public"."instance_size_stats"
FOR EACH ROW
EXECUTE PROCEDURE "public"."instance_size_stats_partition_trigger"();

-- ----------------------------
-- Primary Key structure for table instance_size_stats
-- ----------------------------
ALTER TABLE "public"."instance_size_stats" ADD CONSTRAINT "instance_size_stats_pkey" PRIMARY KEY ("id", "collected_date");

-- ----------------------------
-- Foreign Keys structure for table account_change_log
-- ----------------------------
ALTER TABLE "public"."account_change_log" ADD CONSTRAINT "account_change_log_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table account_classification_assignments
-- ----------------------------
ALTER TABLE "public"."account_classification_assignments" ADD CONSTRAINT "account_classification_assignments_account_id_fkey" FOREIGN KEY ("account_id") REFERENCES "public"."account_permission" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."account_classification_assignments" ADD CONSTRAINT "account_classification_assignments_assigned_by_fkey" FOREIGN KEY ("assigned_by") REFERENCES "public"."users" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."account_classification_assignments" ADD CONSTRAINT "account_classification_assignments_classification_id_fkey" FOREIGN KEY ("classification_id") REFERENCES "public"."account_classifications" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."account_classification_assignments" ADD CONSTRAINT "fk_account_classification_assignments_rule_id" FOREIGN KEY ("rule_id") REFERENCES "public"."classification_rules" ("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table account_permission
-- ----------------------------
ALTER TABLE "public"."account_permission" ADD CONSTRAINT "fk_account_permission_instance" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."account_permission" ADD CONSTRAINT "fk_account_permission_instance_account" FOREIGN KEY ("instance_account_id") REFERENCES "public"."instance_accounts" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table classification_rules
-- ----------------------------
ALTER TABLE "public"."classification_rules" ADD CONSTRAINT "classification_rules_classification_id_fkey" FOREIGN KEY ("classification_id") REFERENCES "public"."account_classifications" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_accounts
-- ----------------------------
ALTER TABLE "public"."instance_accounts" ADD CONSTRAINT "instance_accounts_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_databases
-- ----------------------------
ALTER TABLE "public"."instance_databases" ADD CONSTRAINT "instance_databases_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_tags
-- ----------------------------
ALTER TABLE "public"."instance_tags" ADD CONSTRAINT "instance_tags_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
ALTER TABLE "public"."instance_tags" ADD CONSTRAINT "instance_tags_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "public"."tags" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instances
-- ----------------------------
ALTER TABLE "public"."instances" ADD CONSTRAINT "instances_credential_id_fkey" FOREIGN KEY ("credential_id") REFERENCES "public"."credentials" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table sync_instance_records
-- ----------------------------
ALTER TABLE "public"."sync_instance_records" ADD CONSTRAINT "sync_instance_records_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
ALTER TABLE "public"."sync_instance_records" ADD CONSTRAINT "sync_instance_records_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."sync_sessions" ("session_id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table database_size_stats
-- ----------------------------
ALTER TABLE "public"."database_size_stats" ADD CONSTRAINT "database_size_stats_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_size_aggregations
-- ----------------------------
ALTER TABLE "public"."instance_size_aggregations" ADD CONSTRAINT "instance_size_aggregations_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table instance_size_stats
-- ----------------------------
ALTER TABLE "public"."instance_size_stats" ADD CONSTRAINT "instance_size_stats_instance_id_fkey" FOREIGN KEY ("instance_id") REFERENCES "public"."instances" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

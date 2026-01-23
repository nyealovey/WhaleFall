(function (global) {
  "use strict";

  function resolveActiveStatusText(isActive) {
    return isActive ? "启用" : "停用";
  }

  function resolveDeletionStatusText(isDeleted) {
    return isDeleted ? "已删除" : "正常";
  }

  function resolveLockStatusText(isLocked) {
    return isLocked ? "已锁定" : "正常";
  }

  function resolveRunStatusText(status) {
    switch (status) {
      case "pending":
        return "等待中";
      case "running":
        return "运行中";
      case "paused":
        return "已暂停";
      case "completed":
        return "已完成";
      case "failed":
        return "失败";
      case "cancelled":
        return "已取消";
      default:
        return status || "-";
    }
  }

  function resolveTaskStatusText(status) {
    switch (status) {
      case "success":
        return "成功";
      case "error":
        return "错误";
      case "warning":
        return "告警";
      case "info":
        return "信息";
      case "pending":
      case "running":
      case "paused":
      case "completed":
      case "failed":
      case "cancelled":
        return resolveRunStatusText(status);
      default:
        return status || "-";
    }
  }

  function resolvePeriodTypeText(periodType) {
    const normalized = (periodType || "").toString().trim().toLowerCase();
    switch (normalized) {
      case "daily":
        return "日";
      case "weekly":
        return "周";
      case "monthly":
        return "月";
      case "quarterly":
        return "季";
      case "yearly":
        return "年";
      case "all":
        return "全部";
      default:
        return normalized ? "未知" : "-";
    }
  }

  function resolveCapacitySourceText(source) {
    const normalized = (source || "").toString().trim().toLowerCase();
    switch (normalized) {
      case "instance_size_stats":
      case "database_size_stats":
        return "采集";
      case "capacity_aggregation":
      case "aggregation":
        return "聚合";
      default:
        return normalized ? "未知" : "-";
    }
  }

  global.UI = global.UI || {};
  global.UI.Terms = global.UI.Terms || {};
  global.UI.Terms.resolveActiveStatusText = resolveActiveStatusText;
  global.UI.Terms.resolveDeletionStatusText = resolveDeletionStatusText;
  global.UI.Terms.resolveLockStatusText = resolveLockStatusText;
  global.UI.Terms.resolveRunStatusText = resolveRunStatusText;
  global.UI.Terms.resolveTaskStatusText = resolveTaskStatusText;
  global.UI.Terms.resolvePeriodTypeText = resolvePeriodTypeText;
  global.UI.Terms.resolveCapacitySourceText = resolveCapacitySourceText;
})(window);

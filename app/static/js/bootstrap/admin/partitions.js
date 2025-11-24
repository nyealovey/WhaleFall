// 管理端分区页入口：顺序初始化 AdminPartitionsPage 与聚合图表挂载点
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (global.AdminPartitionsPage && typeof global.AdminPartitionsPage.mount === "function") {
      global.AdminPartitionsPage.mount();
    } else {
      console.error("AdminPartitionsPage 未注册，无法初始化分区管理");
    }

    if (global.PartitionsListGrid && typeof global.PartitionsListGrid.mount === "function") {
      global.PartitionsListGrid.mount();
    } else {
      console.error("PartitionsListGrid 未注册，无法初始化分区列表");
    }

    if (global.AggregationsChartPage && typeof global.AggregationsChartPage.mount === "function") {
      global.AggregationsChartPage.mount();
    } else {
      console.error("AggregationsChartPage 未注册，无法初始化聚合图表");
    }
  });
})(window);

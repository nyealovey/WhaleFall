(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (global.AdminPartitionsPage && typeof global.AdminPartitionsPage.mount === "function") {
      global.AdminPartitionsPage.mount();
    } else {
      console.error("AdminPartitionsPage 未注册，无法初始化分区管理");
    }

    if (global.AggregationsChartPage && typeof global.AggregationsChartPage.mount === "function") {
      global.AggregationsChartPage.mount();
    } else {
      console.error("AggregationsChartPage 未注册，无法初始化聚合图表");
    }
  });
})(window);

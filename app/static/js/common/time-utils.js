(function (window) {
  "use strict";

  const TIMEZONE = "Asia/Shanghai";
  const LOCALE = "zh-cn";
  const PARSE_FORMATS = [
    "YYYY-MM-DD HH:mm:ss",
    "YYYY-MM-DDTHH:mm:ss",
    "YYYY/MM/DD HH:mm:ss",
    "YYYY-MM-DD",
    "YYYY/MM/DD",
    "YYYY-MM-DD HH:mm",
    "YYYY-MM-DDTHH:mm:ss.SSSZ",
    "YYYY-MM-DDTHH:mm:ss[Z]",
    "YYYY-MM-DDTHH:mm:ss.SSS",
  ];

  const TimeFormats = {
    DATETIME_FORMAT: "%Y-%m-%d %H:%M:%S",
    DATE_FORMAT: "%Y-%m-%d",
    TIME_FORMAT: "%H:%M:%S",
    DATETIME_MS_FORMAT: "%Y-%m-%d %H:%M:%S.%f",
    ISO_FORMAT: "%Y-%m-%dT%H:%M:%S.%fZ",
    CHINESE_DATETIME_FORMAT: "%Y年%m月%d日 %H:%M:%S",
    CHINESE_DATE_FORMAT: "%Y年%m月%d日",
  };

  const CUSTOM_PARSE_ENABLED = Boolean(window.dayjs_plugin_customParseFormat);

  /**
   * 注入 zh-cn locale 配置，确保 dayjs 可显示中文。
   */
  function registerZhCnLocale(dayjs) {
    const localeConfig = {
      name: LOCALE,
      weekdays: "星期日_星期一_星期二_星期三_星期四_星期五_星期六".split("_"),
      weekdaysShort: "周日_周一_周二_周三_周四_周五_周六".split("_"),
      weekdaysMin: "日_一_二_三_四_五_六".split("_"),
      months: "一月_二月_三月_四月_五月_六月_七月_八月_九月_十月_十一月_十二月".split("_"),
      monthsShort: "1月_2月_3月_4月_5月_6月_7月_8月_9月_10月_11月_12月".split("_"),
      weekStart: 1,
      formats: {
        LT: "HH:mm",
        LTS: "HH:mm:ss",
        L: "YYYY/MM/DD",
        LL: "YYYY年M月D日",
        LLL: "YYYY年M月D日 HH:mm",
        LLLL: "YYYY年M月D日dddd HH:mm",
        l: "YYYY/M/D",
        ll: "YYYY年M月D日",
        lll: "YYYY年M月D日 HH:mm",
        llll: "YYYY年M月D日dddd HH:mm",
      },
      relativeTime: {
        future: "%s后",
        past: "%s前",
        s: "几秒",
        m: "1 分钟",
        mm: "%d 分钟",
        h: "1 小时",
        hh: "%d 小时",
        d: "1 天",
        dd: "%d 天",
        M: "1 个月",
        MM: "%d 个月",
        y: "1 年",
        yy: "%d 年",
      },
    };
    dayjs.locale(localeConfig, null, true);
  }

  /**
   * 注册所有 dayjs 插件并设置默认时区。
   */
  function setupDayjs() {
    if (typeof window.dayjs !== "function") {
      throw new Error("Day.js 未加载，无法初始化 TimeUtils");
    }

    const dayjs = window.dayjs;
    const pluginMap = [
      window.dayjs_plugin_utc,
      window.dayjs_plugin_timezone,
      window.dayjs_plugin_relativeTime,
      window.dayjs_plugin_duration,
      window.dayjs_plugin_customParseFormat,
      window.dayjs_plugin_localizedFormat,
    ];

    pluginMap.forEach((plugin) => {
      if (typeof plugin === "function") {
        dayjs.extend(plugin);
      }
    });

    if (!dayjs.Ls || !dayjs.Ls[LOCALE]) {
      registerZhCnLocale(dayjs);
    }
    dayjs.locale(LOCALE);

    if (dayjs.tz && typeof dayjs.tz.setDefault === "function") {
      dayjs.tz.setDefault(TIMEZONE);
    }

    return dayjs;
  }

  const dayjsLib = setupDayjs();

  /**
   * 将 dayjs 实例转换到默认时区。
   */
  function applyTimezone(instance) {
    if (!instance) {
      return null;
    }
    if (dayjsLib.tz && typeof instance.tz === "function") {
      return instance.tz(TIMEZONE);
    }
    return instance;
  }

  /**
   * 尝试使用自定义格式解析字符串。
   */
  function tryCustomFormats(value) {
    if (!CUSTOM_PARSE_ENABLED) {
      return null;
    }
    for (let i = 0; i < PARSE_FORMATS.length; i += 1) {
      const parsed = dayjsLib(value, PARSE_FORMATS[i], true);
      if (parsed.isValid()) {
        return parsed;
      }
    }
    return null;
  }

  /**
   * 将多种输入类型转换成 dayjs 实例。
   */
  function toDayjs(value) {
    if (value === undefined || value === null || value === "") {
      return null;
    }

    if (dayjsLib.isDayjs && dayjsLib.isDayjs(value)) {
      return applyTimezone(value);
    }

    let instance = null;

    if (value instanceof Date) {
      instance = dayjsLib(value);
    } else if (typeof value === "number") {
      instance = dayjsLib(value);
    } else if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed) {
        return null;
      }
      if (/^\d+$/.test(trimmed)) {
        instance = dayjsLib(Number(trimmed));
      } else {
        instance = tryCustomFormats(trimmed);
        if (!instance || !instance.isValid()) {
          instance = dayjsLib(trimmed);
        }
        if ((!instance || !instance.isValid()) && dayjsLib.tz) {
          instance = dayjsLib.tz(trimmed, TIMEZONE);
        }
      }
    } else {
      return null;
    }

    if (!instance || !instance.isValid()) {
      return null;
    }

    return applyTimezone(instance);
  }

  /**
   * 统一的格式化工具，接受任意值并确保返回字符串/回退值。
   */
  function formatWithPattern(value, pattern, fallback = "-") {
    const instance = toDayjs(value);
    if (!instance) {
      return fallback;
    }
    return instance.format(pattern);
  }

  /**
   * 输出“YYYY年MM月DD日 HH:mm:ss”格式。
   */
  function formatChineseDateTimeString(value) {
    const instance = toDayjs(value);
    if (instance) {
      return `${instance.year()}年${instance.month() + 1}月${instance.date()}日 ${instance.format(
        "HH:mm:ss",
      )}`;
    }
    return "-";
  }

  /**
   * 与当前时间对比的秒级差值。
   */
  function diffInSeconds(timestamp) {
    const instance = toDayjs(timestamp);
    if (!instance) {
      return null;
    }
    return Math.round(dayjsLib().diff(instance, "second"));
  }

  /**
   * 判断是否与指定日期同一天，默认与今日对比。
   */
  function isSameDay(value, comparator = "today") {
    const instance = toDayjs(value);
    if (!instance) {
      return false;
    }
    const reference = comparator === "yesterday" ? dayjsLib().subtract(1, "day") : dayjsLib();
    return instance.isSame(reference, "day");
  }

  function buildTimeRange(hours = 24) {
    const now = dayjsLib();
    let start;
    if (hours < 24) {
      start = now.subtract(hours, "hour");
    } else {
      start = now.startOf("day");
      if (hours > 24) {
        start = start.subtract(hours - 24, "hour");
      }
    }
    return {
      start: start.toISOString(),
      end: now.toISOString(),
      startFormatted: start.format("YYYY-MM-DD HH:mm:ss"),
      endFormatted: now.format("YYYY-MM-DD HH:mm:ss"),
      startDate: start.format("YYYY-MM-DD"),
      endDate: now.format("YYYY-MM-DD"),
    };
  }

  const TimeUtils = {
    formatTime(timestamp, type = "datetime") {
      switch (type) {
        case "date":
          return this.formatDate(timestamp);
        case "time":
          return this.formatTimeOnly(timestamp);
        case "chinese":
          return this.formatChineseDateTime(timestamp);
        default:
          return this.formatDateTime(timestamp);
      }
    },

    formatDateTime(timestamp) {
      return formatWithPattern(timestamp, "YYYY-MM-DD HH:mm:ss");
    },

    formatDate(timestamp) {
      return formatWithPattern(timestamp, "YYYY-MM-DD");
    },

    formatTimeOnly(timestamp) {
      return formatWithPattern(timestamp, "HH:mm:ss");
    },

    formatChineseDateTime(timestamp) {
      return formatChineseDateTimeString(timestamp);
    },

    formatRelativeTime(timestamp) {
      const diffSeconds = diffInSeconds(timestamp);
      if (diffSeconds === null) {
        return "-";
      }
      if (diffSeconds < 60) {
        return "刚刚";
      }
      if (diffSeconds < 3600) {
        const minutes = Math.floor(diffSeconds / 60);
        return `${minutes}分钟前`;
      }
      if (diffSeconds < 86400) {
        const hours = Math.floor(diffSeconds / 3600);
        return `${hours}小时前`;
      }
      if (diffSeconds < 604800) {
        const days = Math.floor(diffSeconds / 86400);
        return `${days}天前`;
      }
      return this.formatDateTime(timestamp);
    },

    isToday(timestamp) {
      return isSameDay(timestamp, "today");
    },

    isYesterday(timestamp) {
      return isSameDay(timestamp, "yesterday");
    },

    getTimeRange(hours = 24) {
      return buildTimeRange(hours);
    },

    formatSmartTime(timestamp) {
      if (!timestamp) {
        return "-";
      }
      if (this.isToday(timestamp)) {
        return this.formatTimeOnly(timestamp);
      }
      return this.formatDateTime(timestamp);
    },

    isValidTime(timeString) {
      return Boolean(toDayjs(timeString));
    },

    getChinaTime() {
      return dayjsLib().toDate();
    },

    toChina(timeString) {
      const instance = toDayjs(timeString);
      if (instance) {
        return instance.toDate();
      }
      return null;
    },

    parseTime(timeString) {
      return this.toChina(timeString);
    },
  };

  window.timeUtils = TimeUtils;
  window.TimeFormats = TimeFormats;

  window.formatTime = TimeUtils.formatTime.bind(TimeUtils);
  window.formatDateTime = TimeUtils.formatDateTime.bind(TimeUtils);
  window.formatDate = TimeUtils.formatDate.bind(TimeUtils);
  window.formatTimeOnly = TimeUtils.formatTimeOnly.bind(TimeUtils);
  window.formatRelativeTime = TimeUtils.formatRelativeTime.bind(TimeUtils);
  window.isToday = TimeUtils.isToday.bind(TimeUtils);
  window.isYesterday = TimeUtils.isYesterday.bind(TimeUtils);
  window.getTimeRange = TimeUtils.getTimeRange.bind(TimeUtils);
  window.formatSmartTime = TimeUtils.formatSmartTime.bind(TimeUtils);
  window.isValidTime = TimeUtils.isValidTime.bind(TimeUtils);
  window.getChinaTime = TimeUtils.getChinaTime.bind(TimeUtils);
  window.parseTime = TimeUtils.parseTime.bind(TimeUtils);
})(window);

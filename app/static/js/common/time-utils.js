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

  function setupDayjs() {
    if (typeof window.dayjs !== "function") {
      console.warn("Day.js 未加载，timeUtils 将回退至原生 Date 实现");
      return null;
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
  const hasDayjs = Boolean(dayjsLib);

  function applyTimezone(instance) {
    if (!instance) {
      return null;
    }
    if (dayjsLib && dayjsLib.tz && typeof instance.tz === "function") {
      return instance.tz(TIMEZONE);
    }
    return instance;
  }

  function tryCustomFormats(value) {
    if (!hasDayjs || !CUSTOM_PARSE_ENABLED) {
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

  function toDayjs(value) {
    if (!hasDayjs || value === undefined || value === null || value === "") {
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

  function toNativeDate(value) {
    if (value === undefined || value === null || value === "") {
      return null;
    }
    if (value instanceof Date) {
      return isNaN(value.getTime()) ? null : value;
    }
    if (typeof value === "number") {
      const date = new Date(value);
      return isNaN(date.getTime()) ? null : date;
    }
    if (typeof value === "string") {
      let normalized = value.trim();
      if (!normalized) {
        return null;
      }
      if (normalized.endsWith("Z")) {
        normalized = normalized;
      } else if (!/[+-]\d{2}:?\d{2}$/.test(normalized) && normalized.length === 19) {
        normalized = normalized.replace(" ", "T");
      }
      const date = new Date(normalized);
      return isNaN(date.getTime()) ? null : date;
    }
    return null;
  }

  function formatWithPattern(value, pattern, fallback = "-") {
    const instance = toDayjs(value);
    if (!instance) {
      const nativeDate = toNativeDate(value);
      if (!nativeDate) {
        return fallback;
      }
      return formatWithNativePattern(nativeDate, pattern, fallback);
    }
    return instance.format(pattern);
  }

  function formatWithNativePattern(date, pattern, fallback = "-") {
    if (!(date instanceof Date) || isNaN(date.getTime())) {
      return fallback;
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const seconds = String(date.getSeconds()).padStart(2, "0");

    switch (pattern) {
      case "YYYY-MM-DD HH:mm:ss":
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
      case "YYYY-MM-DD":
        return `${year}-${month}-${day}`;
      case "HH:mm:ss":
        return `${hours}:${minutes}:${seconds}`;
      case "YYYY年MM月DD日 HH:mm:ss":
        return `${year}年${date.getMonth() + 1}月${date.getDate()}日 ${hours}:${minutes}:${seconds}`;
      default:
        return date.toISOString();
    }
  }

  function formatChineseDateTimeString(value) {
    const instance = toDayjs(value);
    if (instance) {
      return `${instance.year()}年${instance.month() + 1}月${instance.date()}日 ${instance.format(
        "HH:mm:ss",
      )}`;
    }
    const nativeDate = toNativeDate(value);
    if (!nativeDate) {
      return "-";
    }
    return formatWithNativePattern(nativeDate, "YYYY年MM月DD日 HH:mm:ss");
  }

  function diffInSeconds(timestamp) {
    if (hasDayjs) {
      const instance = toDayjs(timestamp);
      if (!instance) {
        return null;
      }
      return Math.round(dayjsLib().diff(instance, "second"));
    }
    const native = toNativeDate(timestamp);
    if (!native) {
      return null;
    }
    return Math.round((Date.now() - native.getTime()) / 1000);
  }

  function isSameDay(value, comparator = "today") {
    if (hasDayjs) {
      const instance = toDayjs(value);
      if (!instance) {
        return false;
      }
      const reference = comparator === "yesterday" ? dayjsLib().subtract(1, "day") : dayjsLib();
      return instance.isSame(reference, "day");
    }
    const native = toNativeDate(value);
    if (!native) {
      return false;
    }
    const reference = new Date();
    if (comparator === "yesterday") {
      reference.setDate(reference.getDate() - 1);
    }
    return (
      native.getFullYear() === reference.getFullYear() &&
      native.getMonth() === reference.getMonth() &&
      native.getDate() === reference.getDate()
    );
  }

  function buildTimeRange(hours = 24) {
    if (hasDayjs) {
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

    const now = new Date();
    let start;
    if (hours < 24) {
      start = new Date(now.getTime() - hours * 60 * 60 * 1000);
    } else {
      start = new Date(now);
      start.setHours(0, 0, 0, 0);
      if (hours > 24) {
        start = new Date(start.getTime() - (hours - 24) * 60 * 60 * 1000);
      }
    }
    return {
      start: start.toISOString(),
      end: now.toISOString(),
      startFormatted: formatWithNativePattern(start, "YYYY-MM-DD HH:mm:ss"),
      endFormatted: formatWithNativePattern(now, "YYYY-MM-DD HH:mm:ss"),
      startDate: formatWithNativePattern(start, "YYYY-MM-DD"),
      endDate: formatWithNativePattern(now, "YYYY-MM-DD"),
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
      if (toDayjs(timeString)) {
        return true;
      }
      return Boolean(toNativeDate(timeString));
    },

    getChinaTime() {
      if (hasDayjs) {
        return dayjsLib().toDate();
      }
      return new Date();
    },

    toChina(timeString) {
      const instance = toDayjs(timeString);
      if (instance) {
        return instance.toDate();
      }
      return toNativeDate(timeString);
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

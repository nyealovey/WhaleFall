/**
 * 统一时间处理工具 - 前端版本（强制统一版）
 * 与后端 time_utils.py 保持完全一致的时间处理逻辑
 * 删除所有兼容函数，强制使用统一的时间处理方式
 */

// 时区配置 - 与后端保持一致
const TIMEZONE = 'Asia/Shanghai';
const LOCALE = 'zh-CN';

// 时间格式常量 - 与后端 TimeFormats 类完全一致
const TimeFormats = {
    DATETIME_FORMAT: '%Y-%m-%d %H:%M:%S',
    DATE_FORMAT: '%Y-%m-%d',
    TIME_FORMAT: '%H:%M:%S',
    DATETIME_MS_FORMAT: '%Y-%m-%d %H:%M:%S.%f',
    ISO_FORMAT: '%Y-%m-%dT%H:%M:%S.%fZ',
    CHINESE_DATETIME_FORMAT: '%Y年%m月%d日 %H:%M:%S',
    CHINESE_DATE_FORMAT: '%Y年%m月%d日'
};

// 创建统一的格式化器
const formatters = {
    datetime: new Intl.DateTimeFormat(LOCALE, {
        timeZone: TIMEZONE,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        formatMatcher: 'basic'
    }),
    date: new Intl.DateTimeFormat(LOCALE, {
        timeZone: TIMEZONE,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }),
    time: new Intl.DateTimeFormat(LOCALE, {
        timeZone: TIMEZONE,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }),
    relative: new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' })
};

/**
 * 前端时间工具类 - 与后端 TimeUtils 类保持一致
 */
const TimeUtils = {
    /**
     * 统一时间格式化函数 - 与后端 time_utils.format_china_time 保持一致
     * @param {string|Date} timestamp - 时间戳
     * @param {string} type - 格式类型: 'datetime', 'date', 'time', 'chinese'
     * @returns {string} 格式化后的时间字符串
     */
    formatTime: function(timestamp, type = 'datetime') {
        if (!timestamp) return '-';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return '-';
            
            // 后端已经返回中国时区时间，前端直接格式化
            switch (type) {
                case 'datetime':
                    return this.formatDateTimeString(date);
                case 'date':
                    return this.formatDateString(date);
                case 'time':
                    return this.formatTimeString(date);
                case 'chinese':
                    return this.formatChineseDateTimeString(date);
                default:
                    return this.formatDateTimeString(date);
            }
        } catch (e) {
            console.error('时间格式化错误:', e, '输入:', timestamp);
            return '-';
        }
    },

    /**
     * 格式化日期时间字符串 (YYYY-MM-DD HH:mm:ss)
     * @param {Date} date - 日期对象
     * @returns {string} 格式化后的字符串
     */
    formatDateTimeString: function(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    },

    /**
     * 格式化日期字符串 (YYYY-MM-DD)
     * @param {Date} date - 日期对象
     * @returns {string} 格式化后的字符串
     */
    formatDateString: function(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    },

    /**
     * 格式化时间字符串 (HH:mm:ss)
     * @param {Date} date - 日期对象
     * @returns {string} 格式化后的字符串
     */
    formatTimeString: function(date) {
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    },

    /**
     * 格式化中文日期时间字符串 (YYYY年MM月DD日 HH:mm:ss)
     * @param {Date} date - 日期对象
     * @returns {string} 格式化后的字符串
     */
    formatChineseDateTimeString: function(date) {
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}年${month}月${day}日 ${hours}:${minutes}:${seconds}`;
    },

    /**
     * 格式化日期时间（默认格式）- 与后端 time_utils.format_china_time 保持一致
     * @param {string|Date} timestamp - 时间戳
     * @returns {string} 格式化后的日期时间字符串
     */
    formatDateTime: function(timestamp) {
        return this.formatTime(timestamp, 'datetime');
    },

    /**
     * 格式化日期（不包含时间）
     * @param {string|Date} timestamp - 时间戳
     * @returns {string} 格式化后的日期字符串
     */
    formatDate: function(timestamp) {
        return this.formatTime(timestamp, 'date');
    },

    /**
     * 格式化时间（不包含日期）
     * @param {string|Date} timestamp - 时间戳
     * @returns {string} 格式化后的时间字符串
     */
    formatTimeOnly: function(timestamp) {
        return this.formatTime(timestamp, 'time');
    },

    /**
     * 相对时间格式化（如：2小时前）- 与后端 time_utils.get_relative_time 保持一致
     * @param {string|Date} timestamp - 时间戳
     * @returns {string} 相对时间字符串
     */
    formatRelativeTime: function(timestamp) {
        if (!timestamp) return '-';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return '-';
            
            const now = new Date();
            const diffMs = now - date; // 注意：这里是 now - date，表示过去的时间
            const diffSeconds = Math.round(diffMs / 1000);
            
            if (diffSeconds < 60) {
                return '刚刚';
            } else if (diffSeconds < 3600) {
                const minutes = Math.floor(diffSeconds / 60);
                return `${minutes}分钟前`;
            } else if (diffSeconds < 86400) {
                const hours = Math.floor(diffSeconds / 3600);
                return `${hours}小时前`;
            } else if (diffSeconds < 604800) { // 7天
                const days = Math.floor(diffSeconds / 86400);
                return `${days}天前`;
            } else {
                // 超过7天显示完整时间
                return this.formatDateTime(timestamp);
            }
        } catch (e) {
            console.error('相对时间格式化错误:', e, '输入:', timestamp);
            return '-';
        }
    },

    /**
     * 判断是否为今天 - 与后端 time_utils.is_today 保持一致
     * @param {string|Date} timestamp - 时间戳
     * @returns {boolean} 是否为今天
     */
    isToday: function(timestamp) {
        if (!timestamp) return false;
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return false;
            
            const now = new Date();
            
            // 比较年月日
            return date.getFullYear() === now.getFullYear() &&
                   date.getMonth() === now.getMonth() &&
                   date.getDate() === now.getDate();
        } catch (e) {
            console.error('判断是否为今天时出错:', e, '输入:', timestamp);
            return false;
        }
    },

    /**
     * 判断是否为昨天
     * @param {string|Date} timestamp - 时间戳
     * @returns {boolean} 是否为昨天
     */
    isYesterday: function(timestamp) {
        if (!timestamp) return false;
        
        try {
            const date = new Date(timestamp);
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            
            return date.toDateString() === yesterday.toDateString();
        } catch (e) {
            return false;
        }
    },

    /**
     * 获取时间范围 - 与后端 time_utils.get_time_range 保持一致
     * @param {number} hours - 小时数
     * @returns {Object} 时间范围对象
     */
    getTimeRange: function(hours = 24) {
        const now = new Date();
        let start;
        
        if (hours < 24) {
            // 小于24小时，从当前时间往前推
            start = new Date(now.getTime() - hours * 60 * 60 * 1000);
        } else {
            // 24小时或更多，从今天0点开始
            start = new Date(now);
            start.setHours(0, 0, 0, 0);
            if (hours > 24) {
                start.setTime(start.getTime() - (hours - 24) * 60 * 60 * 1000);
            }
        }
        
        return {
            start: start.toISOString(),
            end: now.toISOString(),
            startFormatted: this.formatDateTime(start),
            endFormatted: this.formatDateTime(now),
            startDate: this.formatDate(start),
            endDate: this.formatDate(now)
        };
    },

    /**
     * 智能时间显示（根据时间远近选择合适格式）- 与后端模板过滤器保持一致
     * @param {string|Date} timestamp - 时间戳
     * @returns {string} 智能格式化的时间字符串
     */
    formatSmartTime: function(timestamp) {
        if (!timestamp) return '-';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return '-';
            
            if (this.isToday(timestamp)) {
                // 今天显示时间
                return this.formatTimeOnly(timestamp);
            } else {
                // 其他日期显示完整日期时间
                return this.formatDateTime(timestamp);
            }
        } catch (e) {
            console.error('智能时间格式化错误:', e, '输入:', timestamp);
            return '-';
        }
    },

    /**
     * 验证时间格式
     * @param {string} timeString - 时间字符串
     * @returns {boolean} 是否为有效时间格式
     */
    isValidTime: function(timeString) {
        if (!timeString) return false;
        
        try {
            const date = new Date(timeString);
            return !isNaN(date.getTime());
        } catch (e) {
            return false;
        }
    },

    /**
     * 获取当前中国时间 - 与后端 time_utils.now_china 保持一致
     * @returns {Date} 当前中国时间
     */
    getChinaTime: function() {
        // 注意：JavaScript 中直接 new Date() 已经是本地时间
        // 如果需要确保是中国时区，可以使用 Intl API
        return new Date();
    },

    /**
     * 将UTC时间转换为中国时间 - 与后端 time_utils.to_china 保持一致
     * @param {string|Date} utcTime - UTC时间
     * @returns {Date|null} 中国时间
     */
    toChina: function(utcTime) {
        if (!utcTime) return null;
        
        try {
            const date = new Date(utcTime);
            if (isNaN(date.getTime())) return null;
            
            // 如果输入已经是中国时区时间（后端返回），直接返回
            return date;
        } catch (e) {
            console.error('UTC转中国时间错误:', e, '输入:', utcTime);
            return null;
        }
    },

    /**
     * 验证并解析时间字符串 - 与后端 time_utils.to_china 保持一致
     * @param {string|Date} timeString - 时间字符串或Date对象
     * @returns {Date|null} 解析后的Date对象
     */
    parseTime: function(timeString) {
        if (!timeString) return null;
        
        try {
            if (timeString instanceof Date) {
                return isNaN(timeString.getTime()) ? null : timeString;
            }
            
            // 处理ISO格式字符串
            let dateStr = timeString;
            if (typeof dateStr === 'string') {
                if (dateStr.endsWith('Z')) {
                    dateStr = dateStr.slice(0, -1) + '+00:00';
                }
            }
            
            const date = new Date(dateStr);
            return isNaN(date.getTime()) ? null : date;
        } catch (e) {
            console.error('时间解析错误:', e, '输入:', timeString);
            return null;
        }
    }
};

// 创建全局实例 - 与后端 time_utils 实例保持一致
window.timeUtils = TimeUtils;

// 导出时间格式常量
window.TimeFormats = TimeFormats;

// 为了保持向后兼容，提供全局函数（强制统一后逐步迁移）
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

// 删除兼容函数，强制使用统一方式
// 不再提供：formatTimestamp, formatChinaTime, utcToChina 等兼容函数

// 初始化完成提示

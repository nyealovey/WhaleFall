/**
 * 统一时间处理工具 - 前端版本
 * 基于原生JavaScript和Intl API，无需额外依赖
 * 确保整个应用的时间显示一致性
 */

// 时区配置
const TIMEZONE = 'Asia/Shanghai';
const LOCALE = 'zh-CN';

// 时间格式常量
const TIME_FORMATS = {
    DATETIME: 'YYYY-MM-DD HH:mm:ss',
    DATE: 'YYYY-MM-DD',
    TIME: 'HH:mm:ss',
    DATETIME_MS: 'YYYY-MM-DD HH:mm:ss.SSS',
    DISPLAY: 'YYYY年MM月DD日 HH:mm:ss'
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
 * 统一时间格式化函数
 * @param {string|Date} timestamp - 时间戳
 * @param {string} type - 格式类型: 'datetime', 'date', 'time'
 * @returns {string} 格式化后的时间字符串
 */
window.formatTime = function(timestamp, type = 'datetime') {
    if (!timestamp) return '-';
    
    try {
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return '-';
        
        // 使用自定义格式化确保使用 - 分隔符，并正确转换到东八区
        if (type === 'datetime') {
            // 转换为东八区时间
            const chinaTime = new Date(date.toLocaleString("en-US", {timeZone: TIMEZONE}));
            const year = chinaTime.getFullYear();
            const month = String(chinaTime.getMonth() + 1).padStart(2, '0');
            const day = String(chinaTime.getDate()).padStart(2, '0');
            const hours = String(chinaTime.getHours()).padStart(2, '0');
            const minutes = String(chinaTime.getMinutes()).padStart(2, '0');
            const seconds = String(chinaTime.getSeconds()).padStart(2, '0');
            return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        } else if (type === 'date') {
            const chinaTime = new Date(date.toLocaleString("en-US", {timeZone: TIMEZONE}));
            const year = chinaTime.getFullYear();
            const month = String(chinaTime.getMonth() + 1).padStart(2, '0');
            const day = String(chinaTime.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        } else if (type === 'time') {
            const chinaTime = new Date(date.toLocaleString("en-US", {timeZone: TIMEZONE}));
            const hours = String(chinaTime.getHours()).padStart(2, '0');
            const minutes = String(chinaTime.getMinutes()).padStart(2, '0');
            const seconds = String(chinaTime.getSeconds()).padStart(2, '0');
            return `${hours}:${minutes}:${seconds}`;
        }
        
        return formatters[type].format(date);
    } catch (e) {
        console.error('时间格式化错误:', e);
        return '-';
    }
};

/**
 * 格式化日期时间（默认格式）
 * @param {string|Date} timestamp - 时间戳
 * @returns {string} 格式化后的日期时间字符串
 */
window.formatDateTime = function(timestamp) {
    return window.formatTime(timestamp, 'datetime');
};

/**
 * 格式化日期（不包含时间）
 * @param {string|Date} timestamp - 时间戳
 * @returns {string} 格式化后的日期字符串
 */
window.formatDate = function(timestamp) {
    return window.formatTime(timestamp, 'date');
};

/**
 * 格式化时间（不包含日期）
 * @param {string|Date} timestamp - 时间戳
 * @returns {string} 格式化后的时间字符串
 */
window.formatTimeOnly = function(timestamp) {
    return window.formatTime(timestamp, 'time');
};

/**
 * 相对时间格式化（如：2小时前）
 * @param {string|Date} timestamp - 时间戳
 * @returns {string} 相对时间字符串
 */
window.formatRelativeTime = function(timestamp) {
    if (!timestamp) return '-';
    
    try {
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return '-';
        
        const now = new Date();
        const diffMs = date - now;
        const diffSeconds = Math.round(diffMs / 1000);
        const diffMinutes = Math.round(diffSeconds / 60);
        const diffHours = Math.round(diffMinutes / 60);
        const diffDays = Math.round(diffHours / 24);
        
        if (Math.abs(diffSeconds) < 60) {
            return diffSeconds === 0 ? '刚刚' : `${Math.abs(diffSeconds)}秒${diffSeconds > 0 ? '后' : '前'}`;
        } else if (Math.abs(diffMinutes) < 60) {
            return `${Math.abs(diffMinutes)}分钟${diffMinutes > 0 ? '后' : '前'}`;
        } else if (Math.abs(diffHours) < 24) {
            return `${Math.abs(diffHours)}小时${diffHours > 0 ? '后' : '前'}`;
        } else if (Math.abs(diffDays) < 7) {
            return `${Math.abs(diffDays)}天${diffDays > 0 ? '后' : '前'}`;
        } else {
            return window.formatDateTime(timestamp);
        }
    } catch (e) {
        console.error('相对时间格式化错误:', e);
        return '-';
    }
};

/**
 * 判断是否为今天
 * @param {string|Date} timestamp - 时间戳
 * @returns {boolean} 是否为今天
 */
window.isToday = function(timestamp) {
    if (!timestamp) return false;
    
    try {
        const date = new Date(timestamp);
        const now = new Date();
        
        return date.toDateString() === now.toDateString();
    } catch (e) {
        return false;
    }
};

/**
 * 判断是否为昨天
 * @param {string|Date} timestamp - 时间戳
 * @returns {boolean} 是否为昨天
 */
window.isYesterday = function(timestamp) {
    if (!timestamp) return false;
    
    try {
        const date = new Date(timestamp);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        
        return date.toDateString() === yesterday.toDateString();
    } catch (e) {
        return false;
    }
};

/**
 * 获取时间范围
 * @param {number} hours - 小时数
 * @returns {Object} 时间范围对象
 */
window.getTimeRange = function(hours = 24) {
    const now = new Date();
    const start = new Date(now.getTime() - hours * 60 * 60 * 1000);
    
    return {
        start: start.toISOString(),
        end: now.toISOString(),
        startFormatted: window.formatDateTime(start),
        endFormatted: window.formatDateTime(now)
    };
};

/**
 * 智能时间显示（根据时间远近选择合适格式）
 * @param {string|Date} timestamp - 时间戳
 * @returns {string} 智能格式化的时间字符串
 */
window.formatSmartTime = function(timestamp) {
    if (!timestamp) return '-';
    
    try {
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return '-';
        
        const now = new Date();
        const diffMs = now - date;
        const diffHours = diffMs / (1000 * 60 * 60);
        
        if (diffHours < 1) {
            // 1小时内显示相对时间
            return window.formatRelativeTime(timestamp);
        } else if (diffHours < 24) {
            // 24小时内显示时间
            return window.formatTimeOnly(timestamp);
        } else if (diffHours < 24 * 7) {
            // 一周内显示日期+时间
            return window.formatDateTime(timestamp);
        } else {
            // 超过一周显示完整日期时间
            return window.formatDateTime(timestamp);
        }
    } catch (e) {
        console.error('智能时间格式化错误:', e);
        return '-';
    }
};

/**
 * 验证时间格式
 * @param {string} timeString - 时间字符串
 * @returns {boolean} 是否为有效时间格式
 */
window.isValidTime = function(timeString) {
    if (!timeString) return false;
    
    try {
        const date = new Date(timeString);
        return !isNaN(date.getTime());
    } catch (e) {
        return false;
    }
};

/**
 * 获取当前中国时间
 * @returns {Date} 当前中国时间
 */
window.getChinaTime = function() {
    return new Date().toLocaleString('en-US', { timeZone: TIMEZONE });
};

/**
 * 将UTC时间转换为中国时间
 * @param {string|Date} utcTime - UTC时间
 * @returns {Date} 中国时间
 */
window.utcToChina = function(utcTime) {
    if (!utcTime) return null;
    
    try {
        const date = new Date(utcTime);
        return new Date(date.toLocaleString('en-US', { timeZone: TIMEZONE }));
    } catch (e) {
        return null;
    }
};

// 向后兼容：保留旧函数名
window.formatTimestamp = window.formatDateTime;
window.formatChinaTime = window.formatDateTime;

// 初始化完成提示
console.log('时间工具库已加载 - 基于zoneinfo和Intl API');

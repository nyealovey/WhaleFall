/**
 * Frontend unified time processing 示例脚本
 * 
 * 使用方式：
 *   在浏览器控制台中运行，或在 HTML 页面中引入
 * 
 * 示例展示了如何在前端使用统一的时间处理工具，包括：
 * 1. 统一的时间格式化和显示
 * 2. 时间解析和验证
 * 3. 相对时间计算
 * 4. 时间范围处理
 * 5. 与后端 API 的时间数据交互
 * 6. 错误处理和性能优化
 */

// 确保 timeUtils 已加载
if (typeof timeUtils === 'undefined') {
    console.error('❌ timeUtils 未加载，请先引入 time-utils.js');
} else {
    console.log('✅ timeUtils 已加载，开始演示');
}

/**
 * 演示基础时间格式化
 */
function demonstrateBasicFormatting() {
    console.log('=' .repeat(60));
    console.log('1. 基础时间格式化演示');
    console.log('=' .repeat(60));
    
    const now = new Date();
    const isoString = now.toISOString();
    
    console.log('原始时间:', now);
    console.log('ISO 字符串:', isoString);
    console.log();
    
    // 使用不同格式格式化
    const formats = [
        ['标准日期时间', 'datetime'],
        ['仅日期', 'date'],
        ['仅时间', 'time'],
        ['中文格式', 'chinese']
    ];
    
    formats.forEach(([name, type]) => {
        const formatted = timeUtils.formatTime(isoString, type);
        console.log(`${name.padEnd(12)}: ${formatted}`);
    });
    
    console.log();
}

/**
 * 演示时间解析和验证
 */
function demonstrateTimeParsing() {
    console.log('=' .repeat(60));
    console.log('2. 时间解析和验证演示');
    console.log('=' .repeat(60));
    
    const testInputs = [
        '2025-01-17T10:30:00Z',
        '2025-01-17T18:30:00+08:00',
        '2025-01-17 18:30:00',
        'invalid-date',
        null,
        undefined,
        ''
    ];
    
    testInputs.forEach(input => {
        console.log(`输入: ${input}`);
        
        const isValid = timeUtils.isValidTime(input);
        console.log(`  有效性: ${isValid}`);
        
        if (isValid) {
            const parsed = timeUtils.parseTime(input);
            const formatted = timeUtils.formatDateTime(parsed);
            console.log(`  解析结果: ${parsed}`);
            console.log(`  格式化: ${formatted}`);
        }
        
        console.log();
    });
}

/**
 * 演示相对时间计算
 */
function demonstrateRelativeTime() {
    console.log('=' .repeat(60));
    console.log('3. 相对时间计算演示');
    console.log('=' .repeat(60));
    
    const now = new Date();
    
    // 创建不同时间点
    const timePoints = [
        ['刚刚', new Date(now.getTime() - 30 * 1000)],
        ['5分钟前', new Date(now.getTime() - 5 * 60 * 1000)],
        ['2小时前', new Date(now.getTime() - 2 * 60 * 60 * 1000)],
        ['3天前', new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000)],
        ['1周前', new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)],
        ['1个月前', new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)]
    ];
    
    timePoints.forEach(([description, timePoint]) => {
        const relative = timeUtils.formatRelativeTime(timePoint);
        const formatted = timeUtils.formatDateTime(timePoint);
        console.log(`${description.padEnd(8)} (${formatted}) -> ${relative}`);
    });
    
    console.log();
}

/**
 * 演示今天判断和智能时间显示
 */
function demonstrateTodayCheck() {
    console.log('=' .repeat(60));
    console.log('4. 今天判断和智能时间显示演示');
    console.log('=' .repeat(60));
    
    const now = new Date();
    
    const testDates = [
        ['今天', now],
        ['昨天', new Date(now.getTime() - 24 * 60 * 60 * 1000)],
        ['明天', new Date(now.getTime() + 24 * 60 * 60 * 1000)],
        ['一周前', new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)]
    ];
    
    testDates.forEach(([description, testDate]) => {
        const isToday = timeUtils.isToday(testDate);
        const isYesterday = timeUtils.isYesterday(testDate);
        const smartTime = timeUtils.formatSmartTime(testDate);
        const formatted = timeUtils.formatDate(testDate);
        
        console.log(`${description.padEnd(6)} (${formatted}):`);
        console.log(`  是否今天: ${isToday}`);
        console.log(`  是否昨天: ${isYesterday}`);
        console.log(`  智能显示: ${smartTime}`);
        console.log();
    });
}

/**
 * 演示时间范围处理
 */
function demonstrateTimeRange() {
    console.log('=' .repeat(60));
    console.log('5. 时间范围处理演示');
    console.log('=' .repeat(60));
    
    const ranges = [
        ['最近1小时', 1],
        ['最近6小时', 6],
        ['最近24小时', 24],
        ['最近3天', 72],
        ['最近7天', 168]
    ];
    
    ranges.forEach(([description, hours]) => {
        const timeRange = timeUtils.getTimeRange(hours);
        console.log(`${description}:`);
        console.log(`  开始时间: ${timeRange.startFormatted}`);
        console.log(`  结束时间: ${timeRange.endFormatted}`);
        console.log(`  开始日期: ${timeRange.startDate}`);
        console.log(`  结束日期: ${timeRange.endDate}`);
        console.log();
    });
}

/**
 * 模拟与后端 API 的时间数据交互
 */
function simulateApiInteraction() {
    console.log('=' .repeat(60));
    console.log('6. 与后端 API 时间数据交互演示');
    console.log('=' .repeat(60));
    
    // 模拟后端返回的数据
    const mockApiResponse = {
        success: true,
        data: [
            {
                id: 1,
                name: '测试实例1',
                created_at: '2025-01-12T10:30:00.000Z',
                updated_at: '2025-01-17T08:30:00.000Z',
                last_connected: '2025-01-17T09:45:00.000Z'
            },
            {
                id: 2,
                name: '测试实例2',
                created_at: '2025-01-07T15:20:00.000Z',
                updated_at: '2025-01-17T09:15:00.000Z',
                last_connected: null
            }
        ],
        timestamp: '2025-01-17T10:00:00.000Z'
    };
    
    console.log('原始 API 响应:');
    console.log(JSON.stringify(mockApiResponse, null, 2));
    console.log();
    
    // 处理时间数据
    const processedData = mockApiResponse.data.map(item => ({
        ...item,
        // 格式化时间用于显示
        created_at_formatted: timeUtils.formatDateTime(item.created_at),
        updated_at_formatted: timeUtils.formatDateTime(item.updated_at),
        last_connected_formatted: item.last_connected 
            ? timeUtils.formatDateTime(item.last_connected)
            : '从未连接',
        // 相对时间
        created_at_relative: timeUtils.formatRelativeTime(item.created_at),
        updated_at_relative: timeUtils.formatRelativeTime(item.updated_at),
        last_connected_relative: item.last_connected
            ? timeUtils.formatRelativeTime(item.last_connected)
            : '从未连接',
        // 智能时间显示
        last_connected_smart: item.last_connected
            ? timeUtils.formatSmartTime(item.last_connected)
            : '从未连接'
    }));
    
    console.log('处理后的数据:');
    processedData.forEach(item => {
        console.log(`实例 ${item.id}: ${item.name}`);
        console.log(`  创建时间: ${item.created_at_formatted} (${item.created_at_relative})`);
        console.log(`  更新时间: ${item.updated_at_formatted} (${item.updated_at_relative})`);
        console.log(`  最后连接: ${item.last_connected_smart}`);
        console.log();
    });
}

/**
 * 演示 DOM 操作中的时间处理
 */
function demonstrateDomTimeHandling() {
    console.log('=' .repeat(60));
    console.log('7. DOM 操作中的时间处理演示');
    console.log('=' .repeat(60));
    
    // 创建示例 DOM 元素
    const container = document.createElement('div');
    container.innerHTML = `
        <div class="time-demo">
            <h3>时间显示示例</h3>
            <p>当前时间: <span id="current-time"></span></p>
            <p>相对时间: <span id="relative-time"></span></p>
            <p>智能时间: <span id="smart-time"></span></p>
            <ul id="time-list"></ul>
        </div>
    `;
    
    // 更新时间显示
    function updateTimeDisplay() {
        const now = new Date();
        const testTime = new Date(now.getTime() - 2 * 60 * 60 * 1000); // 2小时前
        
        const currentTimeEl = container.querySelector('#current-time');
        const relativeTimeEl = container.querySelector('#relative-time');
        const smartTimeEl = container.querySelector('#smart-time');
        
        if (currentTimeEl) currentTimeEl.textContent = timeUtils.formatDateTime(now);
        if (relativeTimeEl) relativeTimeEl.textContent = timeUtils.formatRelativeTime(testTime);
        if (smartTimeEl) smartTimeEl.textContent = timeUtils.formatSmartTime(testTime);
    }
    
    // 创建时间列表
    function createTimeList() {
        const listEl = container.querySelector('#time-list');
        if (!listEl) return;
        
        const times = [
            new Date(),
            new Date(Date.now() - 30 * 60 * 1000), // 30分钟前
            new Date(Date.now() - 2 * 60 * 60 * 1000), // 2小时前
            new Date(Date.now() - 24 * 60 * 60 * 1000), // 1天前
        ];
        
        listEl.innerHTML = times.map((time, index) => `
            <li>
                时间点 ${index + 1}: 
                ${timeUtils.formatDateTime(time)} 
                (${timeUtils.formatRelativeTime(time)})
            </li>
        `).join('');
    }
    
    updateTimeDisplay();
    createTimeList();
    
    console.log('DOM 示例已创建:');
    console.log(container.innerHTML);
    console.log();
    
    // 如果在浏览器环境中，可以将元素添加到页面
    if (typeof document !== 'undefined' && document.body) {
        document.body.appendChild(container);
        console.log('✅ DOM 元素已添加到页面');
    }
}

/**
 * 演示错误处理
 */
function demonstrateErrorHandling() {
    console.log('=' .repeat(60));
    console.log('8. 错误处理演示');
    console.log('=' .repeat(60));
    
    const invalidInputs = [
        null,
        undefined,
        '',
        'invalid-date',
        '2025-13-45',
        123456,
        {},
        []
    ];
    
    invalidInputs.forEach(input => {
        console.log(`输入: ${input} (${typeof input})`);
        
        try {
            const formatted = timeUtils.formatDateTime(input);
            const relative = timeUtils.formatRelativeTime(input);
            const isValid = timeUtils.isValidTime(input);
            
            console.log(`  格式化结果: ${formatted}`);
            console.log(`  相对时间: ${relative}`);
            console.log(`  有效性: ${isValid}`);
        } catch (error) {
            console.log(`  错误: ${error.message}`);
        }
        
        console.log();
    });
}

/**
 * 演示性能优化技巧
 */
function demonstratePerformanceOptimization() {
    console.log('=' .repeat(60));
    console.log('9. 性能优化技巧演示');
    console.log('=' .repeat(60));
    
    // 批量时间处理
    const testTimes = Array.from({ length: 1000 }, (_, i) => 
        new Date(Date.now() - i * 60 * 1000).toISOString()
    );
    
    console.log(`测试数据: ${testTimes.length} 个时间戳`);
    
    // 测试格式化性能
    console.time('批量格式化');
    const formatted = testTimes.map(time => timeUtils.formatDateTime(time));
    console.timeEnd('批量格式化');
    
    // 测试相对时间计算性能
    console.time('批量相对时间计算');
    const relatives = testTimes.map(time => timeUtils.formatRelativeTime(time));
    console.timeEnd('批量相对时间计算');
    
    console.log(`格式化结果示例: ${formatted.slice(0, 3).join(', ')}...`);
    console.log(`相对时间示例: ${relatives.slice(0, 3).join(', ')}...`);
    console.log();
    
    // 性能优化建议
    console.log('性能优化建议:');
    console.log('1. 缓存格式化结果，避免重复计算');
    console.log('2. 使用 requestAnimationFrame 进行批量 DOM 更新');
    console.log('3. 对于大量数据，考虑虚拟滚动或分页');
    console.log('4. 使用 Web Workers 处理大量时间计算');
    console.log();
}

/**
 * 演示实际应用场景
 */
function demonstrateRealWorldUsage() {
    console.log('=' .repeat(60));
    console.log('10. 实际应用场景演示');
    console.log('=' .repeat(60));
    
    // 场景1: 数据表格时间列
    console.log('场景1: 数据表格时间列');
    const tableData = [
        { id: 1, name: '任务1', created_at: '2025-01-17T08:30:00Z', status: '完成' },
        { id: 2, name: '任务2', created_at: '2025-01-17T09:15:00Z', status: '进行中' },
        { id: 3, name: '任务3', created_at: '2025-01-16T14:20:00Z', status: '待开始' }
    ];
    
    tableData.forEach(row => {
        const formatted = timeUtils.formatDateTime(row.created_at);
        const relative = timeUtils.formatRelativeTime(row.created_at);
        console.log(`${row.name}: ${formatted} (${relative})`);
    });
    console.log();
    
    // 场景2: 实时更新的时间显示
    console.log('场景2: 实时更新的时间显示');
    let updateCount = 0;
    const startTime = new Date(Date.now() - 5 * 60 * 1000); // 5分钟前开始
    
    const updateInterval = setInterval(() => {
        updateCount++;
        const currentRelative = timeUtils.formatRelativeTime(startTime);
        console.log(`更新 ${updateCount}: 开始时间 ${currentRelative}`);
        
        if (updateCount >= 3) {
            clearInterval(updateInterval);
            console.log('实时更新演示结束');
            console.log();
        }
    }, 1000);
    
    // 场景3: 时间范围筛选
    setTimeout(() => {
        console.log('场景3: 时间范围筛选');
        const range = timeUtils.getTimeRange(24); // 最近24小时
        console.log(`筛选范围: ${range.startFormatted} 到 ${range.endFormatted}`);
        
        // 模拟筛选数据
        const allData = [
            { name: '数据1', timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000) },
            { name: '数据2', timestamp: new Date(Date.now() - 25 * 60 * 60 * 1000) },
            { name: '数据3', timestamp: new Date(Date.now() - 30 * 60 * 1000) }
        ];
        
        const rangeStart = new Date(range.start);
        const rangeEnd = new Date(range.end);
        
        const filteredData = allData.filter(item => 
            item.timestamp >= rangeStart && item.timestamp <= rangeEnd
        );
        
        console.log(`筛选结果: ${filteredData.length}/${allData.length} 条数据`);
        filteredData.forEach(item => {
            console.log(`  ${item.name}: ${timeUtils.formatDateTime(item.timestamp)}`);
        });
        console.log();
    }, 4000);
}

/**
 * 主函数：运行所有演示
 */
function main() {
    console.log('🕒 前端统一时间处理工具演示');
    console.log('基于 timezone_and_loglevel_unification.md 强制统一策略');
    console.log();
    
    // 检查 timeUtils 是否可用
    if (typeof timeUtils === 'undefined') {
        console.error('❌ timeUtils 未定义，请确保已加载 time-utils.js');
        return;
    }
    
    // 运行所有演示
    demonstrateBasicFormatting();
    demonstrateTimeParsing();
    demonstrateRelativeTime();
    demonstrateTodayCheck();
    demonstrateTimeRange();
    simulateApiInteraction();
    demonstrateDomTimeHandling();
    demonstrateErrorHandling();
    demonstratePerformanceOptimization();
    demonstrateRealWorldUsage();
    
    // 延迟显示总结，等待异步演示完成
    setTimeout(() => {
        console.log('=' .repeat(60));
        console.log('✅ 前端统一时间处理演示完成');
        console.log('=' .repeat(60));
        console.log();
        console.log('核心原则:');
        console.log('1. 统一使用 timeUtils.method() 方式');
        console.log('2. 删除所有兼容函数和条件判断');
        console.log('3. 统一错误处理，返回 "-" 或合理默认值');
        console.log('4. 与后端时间格式保持完全一致');
        console.log('5. 优化性能，避免重复计算');
        console.log();
        console.log('最佳实践:');
        console.log('- 使用 timeUtils.formatDateTime() 进行标准格式化');
        console.log('- 使用 timeUtils.formatRelativeTime() 显示相对时间');
        console.log('- 使用 timeUtils.formatSmartTime() 进行智能显示');
        console.log('- 使用 timeUtils.parseTime() 进行时间解析');
        console.log('- 使用 timeUtils.isValidTime() 进行时间验证');
    }, 6000);
}

// 如果在浏览器环境中，自动运行演示
if (typeof window !== 'undefined') {
    // 等待 DOM 加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', main);
    } else {
        main();
    }
} else {
    // 在 Node.js 环境中，需要手动调用
    console.log('在 Node.js 环境中运行，请在浏览器中使用此示例');
}

// 导出函数供外部调用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        demonstrateBasicFormatting,
        demonstrateTimeParsing,
        demonstrateRelativeTime,
        demonstrateTodayCheck,
        demonstrateTimeRange,
        simulateApiInteraction,
        demonstrateDomTimeHandling,
        demonstrateErrorHandling,
        demonstratePerformanceOptimization,
        demonstrateRealWorldUsage,
        main
    };
}
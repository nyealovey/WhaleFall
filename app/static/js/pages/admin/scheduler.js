/**
 * 定时任务管理页面JavaScript
 * 处理任务加载、状态切换、执行控制、配置管理等功能
 */

// 全局变量
let currentJobs = [];

// 全局函数
/**
 * 更新“编辑任务”表单中的 Cron 预览。
 * 支持 5/6/7 段 Cron 表达式，顺序为：
 *   7段: second minute hour day month day_of_week year
 *   6段: second minute hour day month day_of_week（无year）
 *   5段: minute hour day month day_of_week（默认second=0，无year）
 * 该函数会根据当前输入生成 cron_expression 预览字符串。
 */
function updateEditCronPreview() {
    const second = $('#editCronSecond').val() || '0';
    const minute = $('#editCronMinute').val() || '0';
    const hour = $('#editCronHour').val() || '0';
    const day = $('#editCronDay').val() || '*';
    const month = $('#editCronMonth').val() || '*';
    const weekday = $('#editCronWeekday').val() || '*';
    const year = $('#editCronYear').val() || '';
    const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
    const cronExpression = year && year.trim() !== '' ? `${base} ${year}` : base;
    $('#editCronPreview').val(cronExpression);
}

// 页面加载完成后初始化
$(document).ready(function() {
    initializeSchedulerPage();
});

// 初始化定时任务管理页面（移除自动刷新）
function initializeSchedulerPage() {
    loadJobs();
    loadHealthStatus();
    initializeEventHandlers();
    console.log('定时任务管理页面已加载');
}

// 初始化事件处理器（移除立即执行绑定）
function initializeEventHandlers() {
    // 触发器类型固定为cron，无需切换逻辑

    // 设置默认日期时间
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    $('#runDate').val(now.toISOString().slice(0, 16));

    // Cron表达式生成和预览
    function updateCronPreview() {
        const second = $('#cronSecond').val() || '0';
        const minute = $('#cronMinute').val() || '0';
        const hour = $('#cronHour').val() || '0';
        const day = $('#cronDay').val() || '*';
        const month = $('#cronMonth').val() || '*';
        const weekday = $('#cronWeekday').val() || '*';
        const year = $('#cronYear').val() || '';
        const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
        const cronExpression = year && year.trim() !== '' ? `${base} ${year}` : base;
        $('#cronPreview').val(cronExpression);
    }

    // 监听cron输入框变化（新增 second 与 year）
    $('#cronSecond, #cronMinute, #cronHour, #cronDay, #cronMonth, #cronWeekday, #cronYear').on('input', updateCronPreview);
    $('#editCronSecond, #editCronMinute, #editCronHour, #editCronDay, #editCronMonth, #editCronWeekday, #editCronYear').on('input', updateEditCronPreview);

    // 初始化预览
    updateCronPreview();

    // 恢复任务操作按钮事件
    $(document).on('click', '.btn-enable-job', function() {
        const jobId = $(this).data('job-id');
        enableJob(jobId);
    });
    $(document).on('click', '.btn-disable-job', function() {
        const jobId = $(this).data('job-id');
        disableJob(jobId);
    });
    $(document).on('click', '.btn-run-job', function() {
        const jobId = $(this).data('job-id');
        runJobNow(jobId);
    });
    $(document).on('click', '.btn-edit-job', function() {
        const jobId = $(this).data('job-id');
        editJob(jobId);
    });

    // 新增：重新初始化任务按钮事件
    /**
     * 重新初始化所有任务按钮事件处理。
     * - 向后端 /scheduler/api/jobs/reload 发送 POST 请求
     * - 删除所有现有任务，重新从配置文件加载任务
     * - 确保任务名称和配置都是最新的
     * - 成功后刷新任务列表并给出提示
     */
     $(document).on('click', '#purgeKeepBuiltinBtn', function() {
         // 二次确认
        const confirmMsg = '此操作将删除所有现有任务，重新从配置文件加载任务。\n这将确保任务名称和配置都是最新的。\n确定继续吗？';
        if (!window.confirm(confirmMsg)) {
             return;
         }
    // 显示加载态
    const $btn = $(this);
    const original = $btn.html();
    $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>重新初始化中...');

    $.ajax({
        url: '/scheduler/api/jobs/reload',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({}),
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(resp) {
            if (resp && resp.success) {
                const deletedCount = (resp.data && resp.data.deleted_count) ? resp.data.deleted_count : 0;
                const reloadedCount = (resp.data && resp.data.reloaded_count) ? resp.data.reloaded_count : 0;
                showAlert(`重新初始化完成：删除了 ${deletedCount} 个任务，重新加载了 ${reloadedCount} 个任务`, 'success');
                loadJobs();
            } else {
                showAlert('重新初始化失败: ' + (resp ? resp.message : '未知错误'), 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('重新初始化失败: ' + (error ? error.message : '网络或服务器错误'), 'danger');
        },
        complete: function() {
            $btn.prop('disabled', false).html(original);
        }
    });
});

    // 恢复表单提交事件
    $('#addJobForm').on('submit', function(e) {
        e.preventDefault();
        addJob();
    });
    $('#editJobForm').on('submit', function(e) {
        e.preventDefault();
        updateJob();
    });
}

// 加载任务列表（移除统计更新）
function loadJobs() {
    $('#loadingRow').show();
    $('#activeJobsContainer').empty();
    $('#pausedJobsContainer').empty();
    $('#emptyRow').hide();

    $.ajax({
        url: '/scheduler/api/jobs',
        method: 'GET',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            $('#loadingRow').hide();
            if (response.success === true) {
                console.log('Received jobs:', response.data);
                currentJobs = response.data;
                displayJobs(response.data);
                // 移除: updateStats(response.data);
            } else {
                showAlert('加载任务失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            $('#loadingRow').hide();
            if (xhr.status === 401 || xhr.status === 403 || xhr.status === 302) {
                showAlert('请先登录或检查管理员权限', 'warning');
                window.location.href = '/auth/login';
            } else {
                const error = xhr.responseJSON;
                showAlert('加载任务失败: ' + (error ? error.message : '未知错误'), 'danger');
            }
        }
    });
}

// 显示任务列表
function displayJobs(jobs) {
    if (jobs.length === 0) {
        $('#emptyRow').show();
        return;
    }

    // 清空所有容器
    $('#activeJobsContainer').empty();
    $('#pausedJobsContainer').empty();
    
    // 分离进行中和已暂停的任务
    const activeJobs = [];
    const pausedJobs = [];
    
    jobs.forEach(function(job) {
        if (job.state === 'STATE_RUNNING' || job.state === 'STATE_EXECUTING') {
            activeJobs.push(job);
        } else {
            pausedJobs.push(job);
        }
    });
    
    // 显示进行中的任务
    activeJobs.forEach(function(job) {
        const jobCard = createJobCard(job);
        $('#activeJobsContainer').append(jobCard);
    });
    
    // 显示已暂停的任务
    pausedJobs.forEach(function(job) {
        const jobCard = createJobCard(job);
        $('#pausedJobsContainer').append(jobCard);
    });
    
    // 更新计数
    $('#activeJobsCount').text(activeJobs.length);
    $('#pausedJobsCount').text(pausedJobs.length);
    
    // 如果没有进行中的任务，显示提示
    if (activeJobs.length === 0) {
        $('#activeJobsContainer').html(`
            <div class="col-12">
                <div class="text-center text-muted py-4">
                    <i class="fas fa-play-circle fa-2x mb-2"></i>
                    <p>暂无进行中的任务</p>
                </div>
            </div>
        `);
    }
    
    // 如果没有已暂停的任务，显示提示
    if (pausedJobs.length === 0) {
        $('#pausedJobsContainer').html(`
            <div class="col-12">
                <div class="text-center text-muted py-4">
                    <i class="fas fa-pause-circle fa-2x mb-2"></i>
                    <p>暂无已暂停的任务</p>
                </div>
            </div>
        `);
    }
}

// 创建任务卡片
function createJobCard(job) {
    const statusClass = getStatusClass(job.state);
    const statusText = getStatusText(job.state);
    const nextRunTime = job.next_run_time ? formatTime(job.next_run_time) : '未计划';
    const lastRunTime = job.last_run_time ? formatTime(job.last_run_time) : '从未运行';
    
    return $(`
        <div class="col-md-6 col-lg-4">
            <div class="job-card ${statusClass}">
                <div class="job-info">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="job-title">${job.name}</h5>
                        <span class="job-status status-${statusClass}">${statusText}</span>
                    </div>
                    
                    <p class="job-description">${job.description || '无描述'}</p>
                    
                    <div class="job-meta">
                        <div class="job-meta-item">
                            <i class="fas fa-clock"></i>
                            <span>下次运行: ${nextRunTime}</span>
                        </div>
                        <div class="job-meta-item">
                            <i class="fas fa-history"></i>
                            <span>上次运行: ${lastRunTime}</span>
                        </div>
                        <div class="job-meta-item">
                            <i class="fas fa-tag"></i>
                            <span>触发器: ${job.trigger_type}</span>
                        </div>
                    </div>
                    
                    <div class="trigger-info">
                        <strong>触发器配置:</strong><br>
                        ${formatTriggerInfo(job.trigger_args)}
                    </div>
                    
                    <div class="job-actions">
                        ${getActionButtons(job)}
                    </div>
                </div>
            </div>
        </div>
    `);
}

// 获取状态样式类
function getStatusClass(state) {
    switch (state) {
        case 'STATE_RUNNING':
        case 'STATE_EXECUTING':
            return 'active';
        case 'STATE_PAUSED':
            return 'paused';
        case 'STATE_ERROR':
            return 'error';
        default:
            return 'paused';
    }
}

// 获取状态文本
function getStatusText(state) {
    switch (state) {
        case 'STATE_RUNNING':
        case 'STATE_EXECUTING':
            return '运行中';
        case 'STATE_PAUSED':
            return '已暂停';
        case 'STATE_ERROR':
            return '错误';
        default:
            return '未知';
    }
}

// 格式化触发器信息
function formatTriggerInfo(triggerArgs) {
    if (!triggerArgs) return '无配置';
    
    try {
        const args = typeof triggerArgs === 'string' ? JSON.parse(triggerArgs) : triggerArgs;
        
        // 按时间顺序定义字段顺序：秒、分、时、日、月、周、年
        const fieldOrder = ['second', 'minute', 'hour', 'day', 'month', 'day_of_week', 'year'];
        
        // 按指定顺序显示字段
        const orderedFields = [];
        fieldOrder.forEach(field => {
            if (args.hasOwnProperty(field)) {
                orderedFields.push(`${field}: ${args[field]}`);
            }
        });
        
        // 显示其他未在顺序中的字段
        Object.entries(args).forEach(([key, value]) => {
            if (!fieldOrder.includes(key) && key !== 'description') {
                orderedFields.push(`${key}: ${value}`);
            }
        });
        
        return orderedFields.join('<br>');
    } catch (e) {
        return triggerArgs.toString();
    }
}

// 获取操作按钮
function getActionButtons(job) {
    let buttons = '';

    switch (job.state) {
        case 'STATE_RUNNING':
        case 'STATE_EXECUTING':
            buttons += `<button class="btn btn-warning btn-sm btn-disable-job" data-job-id="${job.id}">
                <i class="fas fa-pause"></i> 禁用
            </button>`;
            break;
        case 'STATE_PAUSED':
            buttons += `<button class="btn btn-success btn-sm btn-enable-job" data-job-id="${job.id}">
                <i class="fas fa-play"></i> 启用
            </button>`;
            break;
        case 'STATE_ERROR':
        default:
            buttons += `<button class="btn btn-success btn-sm btn-enable-job" data-job-id="${job.id}">
                <i class="fas fa-play"></i> 启用
            </button>`;
            break;
    }

    // 总是显示“执行”按钮
    buttons += `<button class="btn btn-info btn-sm btn-run-job" data-job-id="${job.id}">
        <i class="fas fa-play-circle"></i> 执行
    </button>`;

    buttons += `<button class="btn btn-primary btn-sm btn-edit-job" data-job-id="${job.id}">
        <i class="fas fa-edit"></i> 编辑
    </button>`;

    return buttons;
}



// 启用任务
function enableJob(jobId) {
    showLoadingState($(`[data-job-id="${jobId}"].btn-enable-job`), '启用中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/resume`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已启用', 'success');
                loadJobs();
            } else {
                showAlert('启用失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('启用失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-enable-job`), '启用');
        }
    });
}

// 禁用任务
function disableJob(jobId) {
    showLoadingState($(`[data-job-id="${jobId}"].btn-disable-job`), '禁用中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/pause`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已禁用', 'success');
                loadJobs();
            } else {
                showAlert('禁用失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('禁用失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-disable-job`), '禁用');
        }
    });
}

// 立即执行任务
function runJobNow(jobId) {
    showLoadingState($(`[data-job-id="${jobId}"].btn-run-job`), '执行中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/run`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已开始执行', 'success');
                loadJobs();
            } else {
                showAlert('执行失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('执行失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-run-job`), '执行');
        }
    });
}

// 编辑任务
function editJob(jobId) {
    const job = currentJobs.find(j => j.id === jobId);
    if (!job) {
        showAlert('任务不存在', 'danger');
        return;
    }
    
    // 填充编辑表单
    $('#editJobId').val(job.id);
    $('#editJobName').val(job.name);
    $('#editJobDescription').val(job.description || '');
    
    // 设置执行函数，确保与下拉框选项匹配
    const functionValue = job.func || job.name;
    $('#editJobFunction').val(functionValue);
    
    // 将执行函数字段设为只读
    $('#editJobFunction').prop('disabled', true).addClass('form-control-plaintext');
    
    // 触发器类型固定为cron
    const triggerType = 'cron';
    $('.edit-trigger-config').hide();
    $('#editCronConfig').show();
    
    // 填充触发器参数
    try {
        const triggerArgs = typeof job.trigger_args === 'string' ? JSON.parse(job.trigger_args) : (job.trigger_args || {});
        if (triggerArgs && typeof triggerArgs === 'object') {
            if (triggerType === 'cron') {
                if (triggerArgs.cron_expression) {
                    const cronParts = (triggerArgs.cron_expression || '').trim().split(/\s+/);
                    // 支持 5/6/7 段
                    if (cronParts.length >= 5) {
                        if (cronParts.length === 5) {
                            // m h d M dow
                            $('#editCronSecond').val('0');
                            $('#editCronMinute').val(cronParts[0] || '0');
                            $('#editCronHour').val(cronParts[1] || '0');
                            $('#editCronDay').val(cronParts[2] || '*');
                            $('#editCronMonth').val(cronParts[3] || '*');
                            $('#editCronWeekday').val(cronParts[4] || '*');
                            $('#editCronYear').val('');
                        } else if (cronParts.length === 6) {
                            // s m h d M dow
                            $('#editCronSecond').val(cronParts[0] || '0');
                            $('#editCronMinute').val(cronParts[1] || '0');
                            $('#editCronHour').val(cronParts[2] || '0');
                            $('#editCronDay').val(cronParts[3] || '*');
                            $('#editCronMonth').val(cronParts[4] || '*');
                            $('#editCronWeekday').val(cronParts[5] || '*');
                            $('#editCronYear').val('');
                        } else {
                            // 7 段: s m h d M dow y
                            $('#editCronSecond').val(cronParts[0] || '0');
                            $('#editCronMinute').val(cronParts[1] || '0');
                            $('#editCronHour').val(cronParts[2] || '0');
                            $('#editCronDay').val(cronParts[3] || '*');
                            $('#editCronMonth').val(cronParts[4] || '*');
                            $('#editCronWeekday').val(cronParts[5] || '*');
                            $('#editCronYear').val(cronParts[6] || '');
                        }
                        updateEditCronPreview();
                    }
                } else {
                    // 使用字段名填充
                    $('#editCronSecond').val(triggerArgs.second ?? '0');
                    $('#editCronMinute').val(triggerArgs.minute ?? '0');
                    $('#editCronHour').val(triggerArgs.hour ?? '0');
                    $('#editCronDay').val(triggerArgs.day ?? '*');
                    $('#editCronMonth').val(triggerArgs.month ?? '*');
                    $('#editCronWeekday').val(triggerArgs.day_of_week ?? '*');
                    $('#editCronYear').val(triggerArgs.year ?? '');
                    updateEditCronPreview();
                }
            } else if (triggerType === 'interval') {
                // 间隔触发器：预填分钟与秒
                const minutes = triggerArgs.minutes ?? 0;
                const seconds = triggerArgs.seconds ?? 0;
                $('#editIntervalMinutes').val(Number(minutes) || 0);
                $('#editIntervalSeconds').val(Number(seconds) || 0);
            } else if (triggerType === 'date') {
                // 日期触发器：预填运行时间（转换为 datetime-local 格式）
                const runDateIso = triggerArgs.run_date;
                if (runDateIso) {
                    try {
                        const dt = new Date(runDateIso);
                        // 调整时区偏移，生成本地时间格式的字符串
                        dt.setMinutes(dt.getMinutes() - dt.getTimezoneOffset());
                        $('#editRunDate').val(dt.toISOString().slice(0, 16));
                    } catch (_err) {
                        console.warn('解析 run_date 失败:', _err);
                        $('#editRunDate').val('');
                    }
                } else {
                    $('#editRunDate').val('');
                }
            }
        }
    } catch (e) {
        console.error('解析触发器参数失败:', e);
    }
    
    // 显示编辑模态框
    $('#editJobModal').modal('show');
}

// 更新任务
function updateJob() {
    const formData = new FormData($('#editJobForm')[0]);
    const jobId = formData.get('job_id');
    const originalJob = currentJobs.find(j => j.id === jobId);

    if (!originalJob) {
        showAlert('任务不存在', 'danger');
        return;
    }

    const isBuiltInJob = [
        'sync_accounts', 
        'cleanup_logs', 
        'monitor_partition_health', 
        'collect_database_sizes', 
        'calculate_database_size_aggregations'
    ].includes(originalJob.id);

    let data = Object.fromEntries(formData.entries());
    data.trigger_type = 'cron';  // 固定为cron触发器

    if (data.trigger_type === 'cron') {
        const second = $('#editCronSecond').val() || '0';
        const minute = data.cron_minute || '0';
        const hour = data.cron_hour || '0';
        const day = data.cron_day || '*';
        const month = data.cron_month || '*';
        const weekday = data.cron_weekday || '*';
        const year = $('#editCronYear').val() || '';
        const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
        data.cron_expression = year && year.trim() !== '' ? `${base} ${year}` : base;
        // 同时附带单字段，便于后端直接取用
        data.cron_second = second;
        if (year && year.trim() !== '') data.year = year;
        // 清理 interval/date 字段，避免污染
        delete data.interval_minutes;
        delete data.interval_seconds;
        delete data.minutes;
        delete data.seconds;
        delete data.run_date;
    } else if (data.trigger_type === 'interval') {
        // 仅发送 interval 所需字段（按后端字段名 minutes/seconds）
        data = {
            trigger_type: 'interval',
            minutes: $('#editIntervalMinutes').val(),
            seconds: $('#editIntervalSeconds').val()
        };
    } else if (data.trigger_type === 'date') {
        // 仅发送 date 所需字段
        data = {
            trigger_type: 'date',
            run_date: $('#editRunDate').val()
        };
    }

    let payload;
    if (isBuiltInJob) {
        payload = {
            trigger_type: data.trigger_type
        };
        if (data.trigger_type === 'cron') {
            payload.cron_expression = data.cron_expression;
        } else if (data.trigger_type === 'interval') {
            // 后端识别的字段名：minutes、seconds
            payload.minutes = data.minutes;
            payload.seconds = data.seconds;
        } else if (data.trigger_type === 'date') {
            payload.run_date = data.run_date;
        }
    } else {
        payload = data;
        if (!$('#editJobFunction').is(':disabled')) {
            payload.func = $('#editJobFunction').val();
        }
    }

    showLoadingState($('#editJobForm button[type="submit"]'), '保存中...');

    $.ajax({
        url: `/scheduler/api/jobs/${jobId}`,
        method: 'PUT',
        data: JSON.stringify(payload),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务更新成功', 'success');
                $('#editJobModal').modal('hide');
                loadJobs();
            } else {
                showAlert('更新失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('更新失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($('#editJobForm button[type="submit"]'), '保存更改');
        }
    });
}

// 删除任务
function deleteJob(jobId) {
    const job = currentJobs.find(j => j.id === jobId);
    if (!job) {
        showAlert('任务不存在', 'danger');
        return;
    }
    
    if (!confirm(`确定要删除任务 "${job.name}" 吗？此操作不可撤销。`)) {
        return;
    }
    
    showLoadingState($(`[data-job-id="${jobId}"].btn-delete-job`), '删除中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}`,
        method: 'DELETE',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已删除', 'success');
                loadJobs();
            } else {
                showAlert('删除失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('删除失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-delete-job`), '删除');
        }
    });
}

// 查看任务日志
function viewJobLogs(jobId) {
    const job = currentJobs.find(j => j.id === jobId);
    if (!job) {
        showAlert('任务不存在', 'danger');
        return;
    }
    
    // 这里可以实现查看日志的功能
    showAlert('日志查看功能待实现', 'info');
}

// 添加任务
function addJob() {
    /**
     * 新增任务提交逻辑（基于后端 “按函数创建任务” 接口）
     * 1. 读取表单数据
     * 2. 将前端的 triggerType 转换为后端识别的 trigger_type
     * 3. 若为 cron 触发器则生成 cron_expression 并附带单字段
     * 4. 调用后端 /scheduler/api/jobs/by-func 接口进行创建
     */
    const form = $('#addJobForm')[0];
    const formData = new FormData(form);

    // 前端单选名称为 triggerType，这里转换为后端所需的 trigger_type
    const triggerType = formData.get('triggerType') || 'cron';

    // 基础载荷：按函数创建任务只需要 name/func/description/trigger_type
    const payload = {
        name: formData.get('name') || '',
        func: formData.get('func') || '',
        description: formData.get('description') || '',
        trigger_type: triggerType
    };

    // Cron 触发器：生成 cron_expression，并附带单字段（便于后端直接取值）
    if (triggerType === 'cron') {
        const second = formData.get('cron_second') || '0';
        const minute = formData.get('cron_minute') || '0';
        const hour = formData.get('cron_hour') || '0';
        const day = formData.get('cron_day') || '*';
        const month = formData.get('cron_month') || '*';
        const weekday = formData.get('cron_weekday') || '*';
        const year = (formData.get('year') || '').toString();
        const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
        const cronExpression = year && year.trim() !== '' ? `${base} ${year}` : base;
        payload.cron_expression = cronExpression;
        payload.cron_second = second;
        payload.cron_minute = minute;
        payload.cron_hour = hour;
        payload.cron_day = day;
        payload.cron_month = month;
        payload.cron_weekday = weekday;
        if (year && year.trim() !== '') payload.year = year;
    }

    // 加载中态
    showLoadingState($('#addJobForm button[type="submit"]'), '添加中...');

    $.ajax({
        url: '/scheduler/api/jobs/by-func',
        method: 'POST',
        data: JSON.stringify(payload),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务添加成功', 'success');
                $('#addJobModal').modal('hide');
                form.reset();
                loadJobs();
            } else {
                showAlert('添加失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('添加失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($('#addJobForm button[type="submit"]'), '添加任务');
        }
    });
}





// 显示加载状态
function showLoadingState(element, text) {
    if (typeof element === 'string') {
        element = $(element);
    }
    
    if (element.length) {
        element.data('original-text', element.text());
        element.html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
        element.prop('disabled', true);
    }
}

// 隐藏加载状态
function hideLoadingState(element, originalText) {
    if (typeof element === 'string') {
        element = $(element);
    }
    
    if (element.length) {
        const text = originalText || element.data('original-text');
        element.html(text);
        element.prop('disabled', false);
    }
}

// 显示提示信息
function showAlert(message, type) {
    const alertDiv = $(`
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('.container-fluid').prepend(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 获取提示图标
function getAlertIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-triangle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

// 格式化时间
function formatTime(timeString) {
    if (!timeString) return '-';
    
    try {
        const date = new Date(timeString);
        if (isNaN(date.getTime())) return '-';
        
        // 后端已经返回东八区时间，前端直接格式化，不进行时区转换
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
    } catch (e) {
        console.error('时间格式化错误:', e);
        return '-';
    }
}



// 健康状态检查功能
function loadHealthStatus() {
    $.ajax({
        url: '/scheduler/api/health',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                updateHealthDisplay(response.data);
            } else {
                console.error('获取健康状态失败:', response.error);
                updateHealthDisplay({
                    status: 'error',
                    status_text: '检查失败',
                    status_color: 'danger',
                    health_score: 0
                });
            }
        },
        error: function(xhr, status, error) {
            console.error('健康状态检查请求失败:', error);
            updateHealthDisplay({
                status: 'error',
                status_text: '请求失败',
                status_color: 'danger',
                health_score: 0
            });
        }
    });
}

function updateHealthDisplay(healthData) {
    // 更新整体状态
    const overallStatus = $(`#overallStatus .badge`);
    overallStatus.removeClass('bg-success bg-warning bg-danger bg-secondary');
    overallStatus.addClass(`bg-${healthData.status_color}`);
    overallStatus.text(healthData.status_text);

    // 更新健康分数
    $('#healthScore .badge').text(`${healthData.health_score}/100`);

    // 更新调度器运行状态
    const schedulerStatus = healthData.scheduler_running ? '运行中' : '已停止';
    const schedulerColor = healthData.scheduler_running ? 'success' : 'danger';
    $('#schedulerRunning .badge').removeClass('bg-success bg-danger bg-secondary').addClass(`bg-${schedulerColor}`).text(schedulerStatus);

    // 更新任务数量
    $('#totalJobs .badge').text(`${healthData.total_jobs || 0}`);

    // 更新详细信息
    $('#threadStatus').text(healthData.thread_alive ? '正常' : '异常').removeClass('text-success text-danger').addClass(healthData.thread_alive ? 'text-success' : 'text-danger');
    $('#jobstoreStatus').text(healthData.jobstore_accessible ? '正常' : '异常').removeClass('text-success text-danger').addClass(healthData.jobstore_accessible ? 'text-success' : 'text-danger');
    $('#executorStatus').text(healthData.executor_working ? '正常' : '异常').removeClass('text-success text-danger').addClass(healthData.executor_working ? 'text-success' : 'text-danger');
    $('#lastCheck').text(healthData.last_check ? new Date(healthData.last_check).toLocaleString() : '--');
}

// 添加刷新健康状态按钮事件
$(document).on('click', '#refreshHealthBtn', function() {
    loadHealthStatus();
});

// 导出函数供全局使用
window.loadJobs = loadJobs;
window.enableJob = enableJob;
window.disableJob = disableJob;
window.runJobNow = runJobNow;
window.editJob = editJob;
window.deleteJob = deleteJob;
window.viewJobLogs = viewJobLogs;
window.addJob = addJob;
window.showAlert = showAlert;
window.formatTime = formatTime;
window.loadHealthStatus = loadHealthStatus;

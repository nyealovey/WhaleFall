/**
 * 定时任务管理页面JavaScript
 * 处理任务加载、状态切换、执行控制、配置管理等功能
 */

// 全局变量
let currentJobs = [];


// 页面加载完成后初始化
$(document).ready(function() {
    initializeSchedulerPage();
});

// 初始化定时任务管理页面（移除自动刷新）
function initializeSchedulerPage() {
    loadJobs();
    initializeEventHandlers();
    console.log('定时任务管理页面已加载');
}

// 初始化事件处理器（移除立即执行绑定）
function initializeEventHandlers() {
    // 触发器类型切换
    $('input[name="triggerType"]').change(function() {
        $('.trigger-config').hide();
        $('#' + $(this).val() + 'Config').show();
    });

    // 编辑模态框触发器类型切换
    $('input[name="editTriggerType"]').change(function() {
        $('.edit-trigger-config').hide();
        const triggerType = $(this).val();
        if (triggerType && typeof triggerType === 'string') {
            $('#edit' + triggerType.charAt(0).toUpperCase() + triggerType.slice(1) + 'Config').show();
        }
    });

    // 设置默认日期时间
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    $('#runDate').val(now.toISOString().slice(0, 16));

    // Cron表达式生成和预览
    function updateCronPreview() {
        const minute = $('#cronMinute').val() || '0';
        const hour = $('#cronHour').val() || '0';
        const day = $('#cronDay').val() || '*';
        const month = $('#cronMonth').val() || '*';
        const weekday = $('#cronWeekday').val() || '*';
        const cronExpression = `${minute} ${hour} ${day} ${month} ${weekday}`;
        $('#cronPreview').val(cronExpression);
    }

    function updateEditCronPreview() {
        const minute = $('#editCronMinute').val() || '0';
        const hour = $('#editCronHour').val() || '0';
        const day = $('#editCronDay').val() || '*';
        const month = $('#editCronMonth').val() || '*';
        const weekday = $('#editCronWeekday').val() || '*';
        const cronExpression = `${minute} ${hour} ${day} ${month} ${weekday}`;
        $('#editCronPreview').val(cronExpression);
    }

    // 监听cron输入框变化
    $('#cronMinute, #cronHour, #cronDay, #cronMonth, #cronWeekday').on('input', updateCronPreview);
    $('#editCronMinute, #editCronHour, #editCronDay, #editCronMonth, #editCronWeekday').on('input', updateEditCronPreview);

    // 初始化预览
    updateCronPreview();

    // 任务操作按钮事件
    $(document).on('click', '.btn-start-job', function() {
        const jobId = $(this).data('job-id');
        startJob(jobId);
    });
    $(document).on('click', '.btn-pause-job', function() {
        const jobId = $(this).data('job-id');
        pauseJob(jobId);
    });
    $(document).on('click', '.btn-resume-job', function() {
        const jobId = $(this).data('job-id');
        resumeJob(jobId);
    });
    $(document).on('click', '.btn-stop-job', function() {
        const jobId = $(this).data('job-id');
        stopJob(jobId);
    });
    $(document).on('click', '.btn-edit-job', function() {
        const jobId = $(this).data('job-id');
        editJob(jobId);
    });
    $(document).on('click', '.btn-delete-job', function() {
        const jobId = $(this).data('job-id');
        deleteJob(jobId);
    });
    $(document).on('click', '.btn-view-logs', function() {
        const jobId = $(this).data('job-id');
        viewJobLogs(jobId);
    });

    // 表单提交事件
    $('#addJobForm').on('submit', function(e) {
        e.preventDefault();
        addJob();
    });

    $('#editJobForm').on('submit', function(e) {
        e.preventDefault();
        updateJob();
    });

    // 移除: 立即执行任务事件绑定
    // （原绑定：#runJobBtn -> runJobNow）
}

// 加载任务列表（移除统计更新）
function loadJobs() {
    $('#loadingRow').show();
    $('#jobsContainer').empty();
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

    const container = $('#jobsContainer');
    
    jobs.forEach(function(job) {
        const jobCard = createJobCard(job);
        container.append(jobCard);
    });
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
        return Object.entries(args)
            .map(([key, value]) => `${key}: ${value}`)
            .join('<br>');
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
            buttons += `<button class="btn btn-warning btn-sm btn-pause-job" data-job-id="${job.id}">
                <i class="fas fa-pause"></i> 暂停
            </button>`;
            buttons += `<button class="btn btn-danger btn-sm btn-stop-job" data-job-id="${job.id}">
                <i class="fas fa-stop"></i> 停止
            </button>`;
            break;
        case 'STATE_PAUSED':
            buttons += `<button class="btn btn-success btn-sm btn-resume-job" data-job-id="${job.id}">
                <i class="fas fa-play"></i> 恢复
            </button>`;
            buttons += `<button class="btn btn-danger btn-sm btn-stop-job" data-job-id="${job.id}">
                <i class="fas fa-stop"></i> 停止
            </button>`;
            break;
        case 'STATE_ERROR':
            buttons += `<button class="btn btn-success btn-sm btn-start-job" data-job-id="${job.id}">
                <i class="fas fa-play"></i> 启动
            </button>`;
            break;
        default:
            buttons += `<button class="btn btn-success btn-sm btn-start-job" data-job-id="${job.id}">
                <i class="fas fa-play"></i> 启动
            </button>`;
    }
    
    buttons += `<button class="btn btn-primary btn-sm btn-edit-job" data-job-id="${job.id}">
        <i class="fas fa-edit"></i> 编辑
    </button>`;
    
    buttons += `<button class="btn btn-info btn-sm btn-view-logs" data-job-id="${job.id}">
        <i class="fas fa-file-alt"></i> 日志
    </button>`;
    
    buttons += `<button class="btn btn-danger btn-sm btn-delete-job" data-job-id="${job.id}">
        <i class="fas fa-trash"></i> 删除
    </button>`;
    
    return buttons;
}



// 启动任务
function startJob(jobId) {
    showLoadingState($(`[data-job-id="${jobId}"].btn-start-job`), '启动中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/enable`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务启动成功', 'success');
                loadJobs();
            } else {
                showAlert('启动失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('启动失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-start-job`), '启动');
        }
    });
}

// 暂停任务
function pauseJob(jobId) {
    showLoadingState($(`[data-job-id="${jobId}"].btn-pause-job`), '暂停中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/pause`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已暂停', 'success');
                loadJobs();
            } else {
                showAlert('暂停失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('暂停失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-pause-job`), '暂停');
        }
    });
}

// 恢复任务
function resumeJob(jobId) {
    showLoadingState($(`[data-job-id="${jobId}"].btn-resume-job`), '恢复中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/resume`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已恢复', 'success');
                loadJobs();
            } else {
                showAlert('恢复失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('恢复失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-resume-job`), '恢复');
        }
    });
}

// 停止任务
function stopJob(jobId) {
    if (!confirm('确定要停止这个任务吗？')) {
        return;
    }
    
    showLoadingState($(`[data-job-id="${jobId}"].btn-stop-job`), '停止中...');
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/disable`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已停止', 'success');
                loadJobs();
            } else {
                showAlert('停止失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('停止失败: ' + (error ? error.message : '未知错误'), 'danger');
        },
        complete: function() {
            hideLoadingState($(`[data-job-id="${jobId}"].btn-stop-job`), '停止');
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
    
    // 如果是内置任务，禁用执行函数选择
    const isBuiltInJob = ['sync_all_accounts', 'sync_all_instances', 'cleanup_logs'].includes(functionValue);
    if (isBuiltInJob) {
        $('#editJobFunction').prop('disabled', true);
        $('#editJobFunction').addClass('form-control-plaintext');
    } else {
        $('#editJobFunction').prop('disabled', false);
        $('#editJobFunction').removeClass('form-control-plaintext');
    }
    
    // 设置触发器类型
    const triggerType = job.trigger_type || 'cron';
    $(`input[name="editTriggerType"][value="${triggerType}"]`).prop('checked', true);
    $('.edit-trigger-config').hide();
    $('#edit' + triggerType.charAt(0).toUpperCase() + triggerType.slice(1) + 'Config').show();
    
    // 填充触发器参数
    try {
        const triggerArgs = typeof job.trigger_args === 'string' ? JSON.parse(job.trigger_args) : (job.trigger_args || {});
        if (triggerArgs && typeof triggerArgs === 'object') {
            // 如果是cron触发器，解析cron表达式
            if (triggerType === 'cron' && triggerArgs.cron_expression) {
                const cronParts = triggerArgs.cron_expression.split(' ');
                if (cronParts.length >= 5) {
                    $('#editCronMinute').val(cronParts[0] || '0');
                    $('#editCronHour').val(cronParts[1] || '0');
                    $('#editCronDay').val(cronParts[2] || '*');
                    $('#editCronMonth').val(cronParts[3] || '*');
                    $('#editCronWeekday').val(cronParts[4] || '*');
                    updateEditCronPreview();
                }
            } else {
                // 其他触发器类型的参数处理
                Object.entries(triggerArgs).forEach(([key, value]) => {
                    if (key && typeof key === 'string') {
                        $(`#edit${key.charAt(0).toUpperCase() + key.slice(1)}`).val(value || '');
                    }
                });
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

    const isBuiltInJob = ['sync_all_accounts', 'sync_all_instances', 'cleanup_logs'].includes(originalJob.id);

    const data = Object.fromEntries(formData.entries());
    const triggerType = data.editTriggerType;
    delete data.editTriggerType;
    data.trigger_type = triggerType;

    if (data.trigger_type === 'cron') {
        const minute = data.cron_minute || '0';
        const hour = data.cron_hour || '0';
        const day = data.cron_day || '*';
        const month = data.cron_month || '*';
        const weekday = data.cron_weekday || '*';
        data.cron_expression = `${minute} ${hour} ${day} ${month} ${weekday}`;
    }

    let payload;
    if (isBuiltInJob) {
        payload = {
            trigger_type: data.trigger_type
        };
        if (data.trigger_type === 'cron') {
            payload.cron_expression = data.cron_expression;
        } else if (data.trigger_type === 'interval') {
            payload.seconds = data.interval_seconds;
            payload.minutes = data.interval_minutes;
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
    const formData = new FormData($('#addJobForm')[0]);
    
    // 如果是cron触发器，生成cron表达式
    const triggerType = formData.get('trigger_type');
    if (triggerType === 'cron') {
        const minute = formData.get('cron_minute') || '0';
        const hour = formData.get('cron_hour') || '0';
        const day = formData.get('cron_day') || '*';
        const month = formData.get('cron_month') || '*';
        const weekday = formData.get('cron_weekday') || '*';
        const cronExpression = `${minute} ${hour} ${day} ${month} ${weekday}`;
        formData.set('cron_expression', cronExpression);
    }
    
    showLoadingState($('#addJobForm button[type="submit"]'), '添加中...');
    
    $.ajax({
        url: '/scheduler/api/jobs',
        method: 'POST',
        data: JSON.stringify(Object.fromEntries(formData)),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务添加成功', 'success');
                $('#addJobModal').modal('hide');
                $('#addJobForm')[0].reset();
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
        
        return date.toLocaleString('zh-CN', {
            timeZone: 'Asia/Shanghai',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        console.error('时间格式化错误:', e);
        return '-';
    }
}



// 导出函数供全局使用
window.loadJobs = loadJobs;
window.startJob = startJob;
window.pauseJob = pauseJob;
window.resumeJob = resumeJob;
window.stopJob = stopJob;
window.editJob = editJob;
window.deleteJob = deleteJob;
window.viewJobLogs = viewJobLogs;
window.addJob = addJob;
// 已移除: window.runJobNow = runJobNow;
window.showAlert = showAlert;
window.formatTime = formatTime;

/**
 * 定时任务管理页面JavaScript
 * 处理任务加载、状态切换、执行控制、配置管理等功能
 */

var schedulerService = null;
var schedulerStore = null;
var addJobValidator = null;
var schedulerModalsController = null;
var schedulerExports = {};

// 校验 SchedulerService 是否已初始化
function ensureSchedulerService() {
    if (schedulerService) {
        return true;
    }
    if (window.toast?.error) {
        window.toast.error('定时任务服务未初始化');
    } else {
        console.error('定时任务服务未初始化');
    }
    return false;
}

// 校验 SchedulerStore 是否已初始化
function ensureSchedulerStore() {
    if (schedulerStore) {
        return true;
    }
    if (window.toast?.error) {
        window.toast.error('SchedulerStore 未初始化');
    } else {
        console.error('SchedulerStore 未初始化');
    }
    return false;
}

// 页面入口：初始化服务、store 与模态
function mountSchedulerPage() {

const SchedulerService = window.SchedulerService;
try {
    if (!SchedulerService) {
        throw new Error('SchedulerService 未加载');
    }
    schedulerService = new SchedulerService(window.httpU);
    if (window.createSchedulerStore) {
        schedulerStore = window.createSchedulerStore({
            service: schedulerService,
            emitter: window.mitt ? window.mitt() : null,
        });
        bindSchedulerStoreEvents();
    }
    if (window.SchedulerModals?.createController) {
        schedulerModalsController = window.SchedulerModals.createController({
            FormValidator: window.FormValidator,
            ValidationRules: window.ValidationRules,
            toast: window.toast,
            getJob: getSchedulerJob,
            ensureStore: ensureSchedulerStore,
            getStore: function () {
                return schedulerStore;
            },
            showLoadingState: showLoadingState,
            hideLoadingState: hideLoadingState,
        });
    } else {
        console.warn('SchedulerModals 未加载，编辑模态将无法使用');
    }
} catch (error) {
    console.error('初始化 SchedulerService/SchedulerStore 失败:', error);
}

// 页面加载完成后初始化
$(document).ready(function () {
    initializeSchedulerPage();
});

}

window.SchedulerPage = {
    mount: mountSchedulerPage,
};

// 初始化定时任务管理页面（移除自动刷新）
function initializeSchedulerPage() {
    if (!schedulerService || !schedulerStore) {
        console.error('SchedulerService/SchedulerStore 未初始化，无法加载任务页面');
        return;
    }
    schedulerStore.init();
    schedulerModalsController?.init();
    initializeEventHandlers();
    initializeSchedulerValidators();
}

// 初始化事件处理器（移除立即执行绑定）
function initializeEventHandlers() {
    // 设置默认日期时间 - 使用统一的时间处理
    const now = timeUtils.getChinaTime();
    // 转换为本地时间输入格式
    const localTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    $('#runDate').val(localTime.toISOString().slice(0, 16));

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

    // 初始化预览
    updateCronPreview();

    // 恢复任务操作按钮事件
    $(document).on('click', '.btn-enable-job', function () {
        const jobId = $(this).data('job-id');
        enableJob(jobId);
    });
    $(document).on('click', '.btn-disable-job', function () {
        const jobId = $(this).data('job-id');
        disableJob(jobId);
    });
    $(document).on('click', '.btn-run-job', function () {
        const jobId = $(this).data('job-id');
        runJobNow(jobId);
    });
    $(document).on('click', '.btn-edit-job', function () {
        const jobId = $(this).data('job-id');
        schedulerModalsController?.openEdit(jobId);
    });

    // 新增：重新初始化任务按钮事件
    /**
     * 重新初始化所有任务按钮事件处理。
     * - 向后端 /scheduler/api/jobs/reload 发送 POST 请求
     * - 删除所有现有任务，重新从配置文件加载任务
     * - 确保任务名称和配置都是最新的
     * - 成功后刷新任务列表并给出提示
     */
    $(document).on('click', '#purgeKeepBuiltinBtn', function () {
        // 二次确认
        const confirmMsg = '此操作将删除所有现有任务，重新从配置文件加载任务。\n这将确保任务名称和配置都是最新的。\n确定继续吗？';
        if (!window.confirm(confirmMsg)) {
            return;
        }
        // 显示加载态
        const $btn = $(this);
        const original = $btn.html();
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>重新初始化中...');

        if (!ensureSchedulerStore()) {
            $btn.prop('disabled', false).html(original);
            return;
        }

    schedulerStore.actions.reloadJobs()
        .then(function (resp) {
            const deletedCount = resp?.data?.deleted_count || 0;
            const reloadedCount = resp?.data?.reloaded_count || 0;
            toast.success(`重新初始化完成：删除了 ${deletedCount} 个任务，重新加载了 ${reloadedCount} 个任务`);
        })
        .catch(function (error) {
            console.error('重新初始化失败:', error);
            const message = error?.response?.message || error?.message || '网络或服务器错误';
            toast.error('重新初始化失败: ' + message);
        })
        .finally(function () {
            $btn.prop('disabled', false).html(original);
        });
    });

    // 恢复表单提交事件（交给 FormValidator 控制）
    $('#addJobForm').on('submit', function (e) {
        e.preventDefault();
        if (addJobValidator && addJobValidator.instance && typeof addJobValidator.instance.revalidate === 'function') {
            addJobValidator.instance.revalidate();
        } else {
            addJob(e.target);
        }
    });
}

function initializeSchedulerValidators() {
    if (typeof FormValidator === 'undefined' || typeof ValidationRules === 'undefined') {
        console.warn('FormValidator 或 ValidationRules 未加载，跳过定时任务表单校验初始化');
        return;
    }

    const addForm = document.getElementById('addJobForm');
    if (addForm) {
        addJobValidator = FormValidator.create('#addJobForm');
        addJobValidator
            .useRules('#jobName', ValidationRules.scheduler.jobName)
            .useRules('#jobFunction', ValidationRules.scheduler.jobFunction)
            .useRules('#cronSecond', ValidationRules.scheduler.cronField)
            .useRules('#cronMinute', ValidationRules.scheduler.cronField)
            .useRules('#cronHour', ValidationRules.scheduler.cronField)
            .useRules('#cronDay', ValidationRules.scheduler.cronField)
            .useRules('#cronMonth', ValidationRules.scheduler.cronField)
            .useRules('#cronWeekday', ValidationRules.scheduler.cronField)
            .useRules('#cronYear', ValidationRules.scheduler.cronYear)
            .onSuccess(function (event) {
                if (event && event.preventDefault) {
                    event.preventDefault();
                    addJob(event.target);
                } else {
                    addJob(addForm);
                }
            })
            .onFail(function () {
                toast.error('请检查任务信息填写');
            });

        ['#jobName', '#jobFunction', '#cronSecond', '#cronMinute', '#cronHour', '#cronDay', '#cronMonth', '#cronWeekday', '#cronYear'].forEach(function (selector) {
            const field = addForm.querySelector(selector);
            if (!field) {
                return;
            }
            const eventType = selector === '#jobFunction' ? 'change' : 'input';
            field.addEventListener(eventType, function () {
                addJobValidator.revalidateField(selector);
            });
        });
    }

}

// 加载任务列表
function loadJobs() {
    if (!ensureSchedulerStore()) {
        return;
    }
    $('#activeJobsContainer').empty();
    $('#pausedJobsContainer').empty();
    $('#emptyRow').hide();
    schedulerStore.actions.loadJobs();
}

// 显示任务列表
function displayJobs(jobs) {
    const list = Array.isArray(jobs) ? jobs : [];
    if (list.length === 0) {
        $('#emptyRow').show();
        return;
    }

    // 清空所有容器
    $('#activeJobsContainer').empty();
    $('#pausedJobsContainer').empty();

    // 分离进行中和已暂停的任务
    const activeJobs = [];
    const pausedJobs = [];

    list.forEach(function (job) {
        if (job.state === 'STATE_RUNNING' || job.state === 'STATE_EXECUTING') {
            activeJobs.push(job);
        } else {
            pausedJobs.push(job);
        }
    });

    // 显示进行中的任务
    activeJobs.forEach(function (job) {
        const jobCard = createJobCard(job);
        $('#activeJobsContainer').append(jobCard);
    });

    // 显示已暂停的任务
    pausedJobs.forEach(function (job) {
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
        <div class="col-4">
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
    if (!ensureSchedulerStore()) {
        return;
    }
    const button = $(`[data-job-id="${jobId}"].btn-enable-job`);
    showLoadingState(button, '启用中...');

    schedulerStore.actions.resumeJob(jobId)
        .then(function () {
            toast.success('任务已启用');
        })
        .catch(function (error) {
            const message = error?.response?.message || error?.message || '未知错误';
            toast.error('启用失败: ' + message);
        })
        .finally(function () {
            hideLoadingState(button, '启用');
        });
}

// 禁用任务
function disableJob(jobId) {
    if (!ensureSchedulerStore()) {
        return;
    }
    const button = $(`[data-job-id="${jobId}"].btn-disable-job`);
    showLoadingState(button, '禁用中...');

    schedulerStore.actions.pauseJob(jobId)
        .then(function () {
            toast.success('任务已禁用');
        })
        .catch(function (error) {
            const message = error?.response?.message || error?.message || '未知错误';
            toast.error('禁用失败: ' + message);
        })
        .finally(function () {
            hideLoadingState(button, '禁用');
        });
}

// 立即执行任务
function runJobNow(jobId) {
    if (!ensureSchedulerStore()) {
        return;
    }
    const button = $(`[data-job-id="${jobId}"].btn-run-job`);
    showLoadingState(button, '执行中...');

    schedulerStore.actions.runJob(jobId)
        .then(function () {
            toast.success('任务已开始执行');
        })
        .catch(function (error) {
            const message = error?.response?.message || error?.message || '未知错误';
            toast.error('执行失败: ' + message);
        })
        .finally(function () {
            hideLoadingState(button, '执行');
        });
}

// 删除任务
function deleteJob(jobId) {
    if (!ensureSchedulerStore()) {
        return;
    }
    const job = getSchedulerJob(jobId);
    if (!job) {
        toast.error('任务不存在');
        return;
    }

    if (!confirm(`确定要删除任务 "${job.name}" 吗？此操作不可撤销。`)) {
        return;
    }

    const button = $(`[data-job-id="${jobId}"].btn-delete-job`);
    showLoadingState(button, '删除中...');

    schedulerStore.actions.deleteJob(jobId)
        .then(function () {
            toast.success('任务已删除');
        })
        .catch(function (error) {
            const message = error?.response?.message || error?.message || '未知错误';
            toast.error('删除失败: ' + message);
        })
        .finally(function () {
            hideLoadingState(button, '删除');
        });
}

// 查看任务日志
function viewJobLogs(jobId) {
    const job = getSchedulerJob(jobId);
    if (!job) {
        toast.error('任务不存在');
        return;
    }

    // 这里可以实现查看日志的功能
    toast.info('日志查看功能待实现');
}

// 添加任务
function addJob(form) {
    if (!ensureSchedulerStore()) {
        return;
    }
    /**
     * 新增任务提交逻辑（基于后端 “按函数创建任务” 接口）
     * 1. 读取表单数据
     * 2. 将前端的 triggerType 转换为后端识别的 trigger_type
     * 3. 若为 cron 触发器则生成 cron_expression 并附带单字段
     * 4. 调用后端 /scheduler/api/jobs/by-func 接口进行创建
     */
    const formElement = form instanceof HTMLFormElement ? form : $('#addJobForm')[0];
    if (!formElement) {
        return;
    }

    const formData = new FormData(formElement);

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
    const submitButton = $(formElement).find('button[type="submit"]');
    showLoadingState(submitButton, '添加中...');

    schedulerStore.actions.createJob(payload)
        .then(function () {
            toast.success('任务添加成功');
            $('#addJobModal').modal('hide');
            formElement.reset();
            if (addJobValidator && addJobValidator.instance) {
                addJobValidator.instance.refresh();
            }
        })
        .catch(function (error) {
            const message = error?.response?.message || error?.message || '未知错误';
            toast.error('添加失败: ' + message);
        })
        .finally(function () {
            hideLoadingState(submitButton, '添加任务');
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


// 格式化时间 - 使用统一的时间工具
function formatTime(timeString) {
    // 强制使用统一的时间工具
    return timeUtils.formatTime(timeString, 'datetime');
}

function bindSchedulerStoreEvents() {
    if (!schedulerStore) {
        return;
    }
    schedulerStore.subscribe('scheduler:loading', function (payload) {
        if (payload?.target === 'jobs') {
            $('#loadingRow').show();
            $('#emptyRow').hide();
        }
    });
    schedulerStore.subscribe('scheduler:updated', function (payload) {
        $('#loadingRow').hide();
        const jobs = payload?.jobs || schedulerStore.getState().jobs || [];
        displayJobs(jobs);
    });
    schedulerStore.subscribe('scheduler:error', function (payload) {
        $('#loadingRow').hide();
        const message = payload?.error?.message || '定时任务操作失败';
        toast.error(message);
    });
}

function getSchedulerJob(jobId) {
    if (!schedulerStore) {
        return null;
    }
    const state = schedulerStore.getState();
    return (state.jobs || []).find(function (job) {
        return job.id === jobId;
    }) || null;
}



// 导出函数供全局使用
window.loadJobs = loadJobs;
window.enableJob = enableJob;
window.disableJob = disableJob;
window.runJobNow = runJobNow;
window.deleteJob = deleteJob;
window.viewJobLogs = viewJobLogs;
window.addJob = addJob;
window.formatTime = formatTime;
window.getSchedulerJob = getSchedulerJob;

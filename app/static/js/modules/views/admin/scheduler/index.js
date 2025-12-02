/**
 * 定时任务管理页面JavaScript
 * 处理任务加载、状态切换、执行控制、配置管理等功能
 */

const DOMHelpers = window.DOMHelpers;
if (!DOMHelpers) {
    throw new Error('DOMHelpers 未初始化');
}
const { ready, select, selectOne, value, from } = DOMHelpers;

var schedulerService = null;
var schedulerStore = null;
var addJobValidator = null;
var schedulerModalsController = null;
var schedulerExports = {};

function setSchedulerStatCard(key, payload) {
    const card = document.querySelector(`[data-stat="${key}"]`);
    if (!card) {
        return;
    }
    const valueNode = card.querySelector('[data-stat-value]');
    if (valueNode && payload?.value !== undefined) {
        valueNode.textContent = payload.value;
    }
    const metaNode = card.querySelector('[data-stat-meta]');
    if (metaNode) {
        if (payload?.metaHtml) {
            metaNode.innerHTML = payload.metaHtml;
        } else if (payload?.meta) {
            metaNode.textContent = payload.meta;
        } else {
            metaNode.textContent = '';
        }
    }
}

function renderStatusPill(label, tone, icon) {
    const iconHtml = icon ? `<i class="fas ${icon}"></i>` : '';
    return `<span class="status-pill status-pill--${tone}">${iconHtml}${label}</span>`;
}

function formatNumber(value) {
    return new Intl.NumberFormat('zh-CN').format(Number(value) || 0);
}

function getStatusMeta(state) {
    switch (state) {
        case 'STATE_RUNNING':
        case 'STATE_EXECUTING':
            return { text: '运行中', tone: 'success', icon: 'fa-play' };
        case 'STATE_PAUSED':
            return { text: '已暂停', tone: 'muted', icon: 'fa-pause' };
        case 'STATE_ERROR':
            return { text: '失败', tone: 'danger', icon: 'fa-exclamation-triangle' };
        default:
            return { text: '未知', tone: 'muted', icon: 'fa-question-circle' };
    }
}

function updateSchedulerStats(allJobs, activeJobs, pausedJobs) {
    const total = allJobs.length;
    const builtin = allJobs.filter(job => job.is_builtin).length;
    setSchedulerStatCard('total_jobs', { value: formatNumber(total) });
    setSchedulerStatCard('running_jobs', {
        value: formatNumber(activeJobs.length),
        metaHtml: renderStatusPill('运行中', 'success', 'fa-play'),
    });
    setSchedulerStatCard('paused_jobs', {
        value: formatNumber(pausedJobs.length),
        metaHtml: renderStatusPill('已暂停', 'muted', 'fa-pause'),
    });
    setSchedulerStatCard('builtin_jobs', {
        value: formatNumber(builtin),
        metaHtml: builtin ? renderStatusPill('内置任务', 'info', 'fa-shield-alt') : '',
    });
}

/**
 * 校验 SchedulerService 是否已初始化。
 *
 * @param {void} 无参数。函数直接读取模块作用域的 schedulerService。
 * @returns {boolean} 若实例可用返回 true，否则提示错误并返回 false。
 */
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

/**
 * 校验 SchedulerStore 是否已初始化。
 *
 * @param {void} 无参数。依赖模块作用域的 schedulerStore。
 * @returns {boolean} 若 store 已就绪返回 true，否则弹出错误提示。
 */
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

/**
 * 挂载调度器管理页面。
 *
 * 初始化调度器管理页面的所有组件，包括 SchedulerService、SchedulerStore、
 * 模态框控制器和事件绑定。提供定时任务的查看、暂停、恢复、执行等管理功能。
 *
 * @param {void} 无参数。函数在页面加载后直接执行。
 * @returns {void}
 *
 * @example
 * // 在页面加载时调用
 * mountSchedulerPage();
 */
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
ready(initializeSchedulerPage);

}

window.SchedulerPage = {
    mount: mountSchedulerPage,
};

// 初始化定时任务管理页面（移除自动刷新）
/**
 * 初始化调度器页面：加载 store、模态和校验器。
 *
 * @param {void} 无参数。依赖已创建的 schedulerService 与 schedulerStore。
 * @returns {void}
 */
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
/**
 * 绑定页面内的交互事件与按钮。
 *
 * @param {void} 无参数。直接绑定页面 DOM 事件。
 * @returns {void}
 */
function initializeEventHandlers() {
    // 设置默认日期时间 - 使用统一的时间处理
    const now = timeUtils.getChinaTime();
    // 转换为本地时间输入格式
    const localTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    value('#runDate', localTime.toISOString().slice(0, 16));

    // Cron表达式生成和预览
    /**
     * 根据输入控件实时生成 cron 表达式。
     *
     * @param {void} 无参数。直接读取 cron 字段的当前值。
     * @returns {void}
     */
    function updateCronPreview() {
        const second = value('#cronSecond') || '0';
        const minute = value('#cronMinute') || '0';
        const hour = value('#cronHour') || '0';
        const day = value('#cronDay') || '*';
        const month = value('#cronMonth') || '*';
        const weekday = value('#cronWeekday') || '*';
        const year = value('#cronYear') || '';
        const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
        const cronExpression = year && year.trim() !== '' ? `${base} ${year}` : base;
        value('#cronPreview', cronExpression);
    }

    // 监听cron输入框变化（新增 second 与 year）
    select('#cronSecond, #cronMinute, #cronHour, #cronDay, #cronMonth, #cronWeekday, #cronYear').on('input', updateCronPreview);

    // 初始化预览
    updateCronPreview();

    // 恢复任务操作按钮事件
    document.addEventListener('click', function (event) {
        const enableButton = event.target.closest('.btn-enable-job');
        if (enableButton) {
            enableJob(enableButton.dataset.jobId);
            return;
        }
        const disableButton = event.target.closest('.btn-disable-job');
        if (disableButton) {
            disableJob(disableButton.dataset.jobId);
            return;
        }
        const runButton = event.target.closest('.btn-run-job');
        if (runButton) {
            runJobNow(runButton.dataset.jobId);
            return;
        }
        const editButton = event.target.closest('.btn-edit-job');
        if (editButton) {
            schedulerModalsController?.openEdit(editButton.dataset.jobId);
        }
    });

    // 新增：重新初始化任务按钮事件
    /**
     * 重新初始化所有任务按钮事件处理。
     * - 向后端 /scheduler/api/jobs/reload 发送 POST 请求
     * - 删除所有现有任务，重新从配置文件加载任务
     * - 确保任务名称和配置都是最新的
     * - 成功后刷新任务列表并给出提示
     */
    const purgeButton = selectOne('#purgeKeepBuiltinBtn').first();
    if (purgeButton) {
        purgeButton.addEventListener('click', function () {
        // 二次确认
        const confirmMsg = '此操作将删除所有现有任务，重新从配置文件加载任务。\n这将确保任务名称和配置都是最新的。\n确定继续吗？';
        if (!window.confirm(confirmMsg)) {
            return;
        }
        // 显示加载态
        const original = purgeButton.innerHTML;
        purgeButton.disabled = true;
        purgeButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>重新初始化中...';

        if (!ensureSchedulerStore()) {
            purgeButton.disabled = false;
            purgeButton.innerHTML = original;
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
                purgeButton.disabled = false;
                purgeButton.innerHTML = original;
            });
        });
    }

    // 恢复表单提交事件（交给 FormValidator 控制）
    const addJobForm = selectOne('#addJobForm').first();
    if (addJobForm) {
        addJobForm.addEventListener('submit', function (event) {
            event.preventDefault();
            if (addJobValidator && addJobValidator.instance && typeof addJobValidator.instance.revalidate === 'function') {
                addJobValidator.instance.revalidate();
            } else {
                addJob(event.target);
            }
        });
    }
}

/**
 * 初始化新增任务表单的校验规则。
 *
 * @param {void} 无参数。该过程自动查找 #addJobForm 并配置校验。
 * @returns {void}
 */
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

/**
 * 从 store 拉取任务列表并清理占位容器。
 *
 * @param {void} 无参数。直接使用 schedulerStore 加载任务。
 * @returns {void}
 */
function loadJobs() {
    if (!ensureSchedulerStore()) {
        return;
    }
    clearContainer('#activeJobsContainer');
    clearContainer('#pausedJobsContainer');
    hideElement('#emptyRow');
    schedulerStore.actions.loadJobs();
}

/**
 * 将任务数据渲染为卡片并统计数量。
 *
 * @param {Array<Object>} jobs 任务数据数组，若为空则回退为 []。
 * @returns {void}
 */
function displayJobs(jobs) {
    const list = Array.isArray(jobs) ? jobs : [];
    if (list.length === 0) {
        showElement('#emptyRow');
        return;
    }

    // 清空所有容器
    clearContainer('#activeJobsContainer');
    clearContainer('#pausedJobsContainer');

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

    const activeContainer = document.getElementById('activeJobsContainer');
    const pausedContainer = document.getElementById('pausedJobsContainer');
    /**
     * 创建列容器包装任务卡片。
     *
     * @param {void} 无参数。仅生成用于布局的列容器。
     * @returns {HTMLDivElement} 新建的列元素。
     */
    const createColumn = () => {
        const wrapper = document.createElement('div');
        wrapper.className = 'col-4';
        return wrapper;
    };

    updateSchedulerStats(list, activeJobs, pausedJobs);

    // 显示进行中的任务
    activeJobs.forEach(function (job) {
        const jobCard = createJobCard(job);
        if (activeContainer) {
            const column = createColumn();
            column.appendChild(jobCard);
            activeContainer.appendChild(column);
        }
    });

    // 显示已暂停的任务
    pausedJobs.forEach(function (job) {
        const jobCard = createJobCard(job);
        if (pausedContainer) {
            const column = createColumn();
            column.appendChild(jobCard);
            pausedContainer.appendChild(column);
        }
    });

    // 更新计数
    selectOne('#activeJobsCount').text(`${activeJobs.length} 项`);
    selectOne('#pausedJobsCount').text(`${pausedJobs.length} 项`);

    // 如果没有进行中的任务，显示提示
    if (activeJobs.length === 0) {
        if (activeContainer) {
            activeContainer.innerHTML = `
            <div class="col-12">
                <div class="text-center text-muted py-4">
                    <i class="fas fa-play-circle fa-2x mb-2"></i>
                    <p>暂无进行中的任务</p>
                </div>
            </div>
            `;
        }
    }

    // 如果没有已暂停的任务，显示提示
    if (pausedJobs.length === 0) {
        if (pausedContainer) {
            pausedContainer.innerHTML = `
            <div class="col-12">
                <div class="text-center text-muted py-4">
                    <i class="fas fa-pause-circle fa-2x mb-2"></i>
                    <p>暂无已暂停的任务</p>
                </div>
            </div>
            `;
        }
    }
}

// 创建任务卡片
/**
 * 生成单个任务的卡片 DOM。
 *
 * @param {Object} job 任务对象，包含 name/state/trigger 等字段。
 * @returns {HTMLElement} 渲染完成的卡片节点。
 */
function createJobCard(job) {
    const statusMeta = getStatusMeta(job.state);
    const nextRunTime = job.next_run_time ? formatTime(job.next_run_time) : '未计划';
    const lastRunTime = job.last_run_time ? formatTime(job.last_run_time) : '从未运行';
    const triggerChips = renderTriggerChips(job.trigger_args);

    const template = document.createElement('template');
    template.innerHTML = `
        <div class="scheduler-card">
            <div class="scheduler-card__header">
                <div>
                    <p class="scheduler-card__title">${escapeHtml(job.name)}</p>
                    <div class="scheduler-card__chips">
                        ${job.is_builtin ? '<span class="chip-outline chip-outline--muted">内置任务</span>' : ''}
                        ${job.func ? `<span class="chip-outline">${escapeHtml(job.func)}</span>` : ''}
                        ${job.trigger_type ? `<span class="chip-outline chip-outline--muted">${escapeHtml(job.trigger_type)}</span>` : ''}
                    </div>
                </div>
                ${renderStatusPill(statusMeta.text, statusMeta.tone, statusMeta.icon)}
            </div>
            <p class="scheduler-card__description">${escapeHtml(job.description || '该任务暂无描述')}</p>
            <div class="scheduler-card__meta">
                <div class="scheduler-card__meta-item">
                    <i class="fas fa-calendar-check"></i>
                    <span>下次运行</span>
                    <span class="chip-outline chip-outline--muted">${nextRunTime}</span>
                </div>
                <div class="scheduler-card__meta-item">
                    <i class="fas fa-history"></i>
                    <span>上次运行</span>
                    <span class="chip-outline chip-outline--muted">${lastRunTime}</span>
                </div>
                <div class="scheduler-card__meta-item">
                    <i class="fas fa-layer-group"></i>
                    <span>任务 ID</span>
                    <span class="chip-outline chip-outline--muted">${escapeHtml(job.id)}</span>
                </div>
            </div>
            <div class="scheduler-trigger-chips">
                ${triggerChips}
            </div>
            <div class="job-actions">
                ${getActionButtons(job)}
            </div>
        </div>
    `.trim();
    return template.content.firstElementChild;
}

/**
 * 将任务状态映射为卡片 CSS 类。
 *
 * @param {string} state 后端返回的任务状态常量。
 * @returns {string} CSS 类名，区分 active/paused/error。
 */
/**
 * 格式化触发器参数为 HTML 描述。
 *
 * @param {Object|string} triggerArgs 触发器参数对象或 JSON 字符串。
 * @returns {string} 适合渲染的 HTML 片段。
 */
function formatTriggerInfo(triggerArgs) {
    if (!triggerArgs) {
        return [];
    }

    try {
        const args = typeof triggerArgs === 'string' ? JSON.parse(triggerArgs) : triggerArgs;
        const fieldOrder = ['second', 'minute', 'hour', 'day', 'month', 'day_of_week', 'year'];
        const orderedFields = [];

        fieldOrder.forEach(field => {
            if (Object.prototype.hasOwnProperty.call(args, field)) {
                orderedFields.push(`${field}: ${args[field]}`);
            }
        });

        Object.entries(args).forEach(([key, value]) => {
            if (!fieldOrder.includes(key) && key !== 'description') {
                orderedFields.push(`${key}: ${value}`);
            }
        });

        return orderedFields;
    } catch (e) {
        return [triggerArgs.toString()];
    }
}

function renderTriggerChips(triggerArgs) {
    const entries = formatTriggerInfo(triggerArgs);
    if (!entries.length) {
        return '<span class="chip-outline chip-outline--muted">默认 Cron</span>';
    }
    return entries
        .map(item => `<span class="chip-outline chip-outline--muted">${escapeHtml(item)}</span>`)
        .join('');
}

/**
 * 根据状态生成操作按钮 HTML。
 *
 * @param {Object} job 任务对象。
 * @returns {string} 包含按钮的 HTML 字符串。
 */
function getActionButtons(job) {
    const buttons = [];

    if (job.state === 'STATE_RUNNING' || job.state === 'STATE_EXECUTING') {
        buttons.push(
            `<button class="btn btn-outline-secondary btn-icon btn-disable-job" data-job-id="${job.id}" title="暂停任务">
                <i class="fas fa-pause"></i>
            </button>`
        );
    } else {
        buttons.push(
            `<button class="btn btn-outline-secondary btn-icon btn-enable-job" data-job-id="${job.id}" title="启用任务">
                <i class="fas fa-play"></i>
            </button>`
        );
    }

    buttons.push(
        `<button class="btn btn-outline-secondary btn-icon btn-run-job" data-job-id="${job.id}" title="立即执行">
            <i class="fas fa-bolt"></i>
        </button>`
    );

    buttons.push(
        `<button class="btn btn-outline-secondary btn-icon btn-edit-job" data-job-id="${job.id}" title="编辑任务">
            <i class="fas fa-edit"></i>
        </button>`
    );

    return buttons.join('');
}



/**
 * 调用 store 恢复任务。
 *
 * @param {string|number} jobId 任务唯一标识。
 * @returns {void}
 */
function enableJob(jobId) {
    if (!ensureSchedulerStore()) {
        return;
    }
    const button = select(`[data-job-id="${jobId}"].btn-enable-job`);
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

/**
 * 调用 store 暂停任务。
 *
 * @param {string|number} jobId 任务唯一标识。
 * @returns {void}
 */
function disableJob(jobId) {
    if (!ensureSchedulerStore()) {
        return;
    }
    const button = select(`[data-job-id="${jobId}"].btn-disable-job`);
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

/**
 * 触发任务立即执行。
 *
 * @param {string|number} jobId 任务唯一标识。
 * @returns {void}
 */
function runJobNow(jobId) {
    if (!ensureSchedulerStore()) {
        return;
    }
    const button = select(`[data-job-id="${jobId}"].btn-run-job`);
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

/**
 * 删除指定任务。
 *
 * @param {string|number} jobId 任务唯一标识。
 * @returns {void}
 */
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

    const button = select(`[data-job-id="${jobId}"].btn-delete-job`);
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

/**
 * 占位：查看任务日志。
 *
 * @param {string|number} jobId 任务标识。
 * @returns {void}
 */
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
/**
 * 提交新增任务表单。
 *
 * @param {HTMLFormElement|EventTarget|Object} form 触发提交的表单或事件目标。
 * @returns {void}
 */
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
    const formElement = form instanceof HTMLFormElement ? form : selectOne('#addJobForm').first();
    if (!formElement) {
        console.error('找不到新增任务表单，无法提交');
        return;
    }
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
    const submitButton = from(formElement).find('button[type="submit"]');
    showLoadingState(submitButton, '添加中...');

    schedulerStore.actions.createJob(payload)
        .then(function () {
            toast.success('任务添加成功');
            hideAddJobModal();
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
/**
 * 为按钮显示加载态。
 *
 * @param {string|Element|Object} element 可解析为 Umbrella.js 集合的目标。
 * @param {string} text 加载提示文案。
 * @returns {void}
 */
function showLoadingState(element, text) {
    const normalized = normalizeElements(element);
    if (!normalized.length) {
        return;
    }
    const node = normalized.first();
    const originalText = normalized.text();
    normalized.data('original-text', originalText);
    const isIconButton = node?.classList?.contains('btn-icon');
    normalized.html(
        isIconButton ? '<i class="fas fa-spinner fa-spin"></i>' : `<i class="fas fa-spinner fa-spin me-2"></i>${text}`
    );
    if (node) {
        node.disabled = true;
    }
}

// 隐藏加载状态
/**
 * 恢复按钮原有文案并取消禁用。
 *
 * @param {string|Element|Object} element 被操作的按钮或集合。
 * @param {string} originalText 缺少缓存时使用的默认文案。
 * @returns {void}
 */
function hideLoadingState(element, originalText) {
    const normalized = normalizeElements(element);
    if (!normalized.length) {
        return;
    }
    const textContent = originalText || normalized.data('original-text');
    normalized.html(textContent);
    const node = normalized.first();
    if (node) {
        node.disabled = false;
    }
}


// 格式化时间 - 使用统一的时间工具
/**
 * 将时间字符串格式化为本地时间。
 *
 * @param {string} timeString ISO 字符串或 timeUtils 可解析的值。
 * @returns {string} 已格式化的文本。
 */
function formatTime(timeString) {
    // 强制使用统一的时间工具
    return timeUtils.formatTime(timeString, 'datetime');
}

/**
 * 订阅 store 事件刷新 UI。
 *
 * @param {void} 无参数。依赖 schedulerStore。
 * @returns {void}
 */
function bindSchedulerStoreEvents() {
    if (!schedulerStore) {
        return;
    }
    schedulerStore.subscribe('scheduler:loading', function (payload) {
        if (payload?.target === 'jobs') {
            showElement('#loadingRow');
            hideElement('#emptyRow');
        }
    });
    schedulerStore.subscribe('scheduler:updated', function (payload) {
        hideElement('#loadingRow');
        const jobs = payload?.jobs || schedulerStore.getState().jobs || [];
        displayJobs(jobs);
    });
    schedulerStore.subscribe('scheduler:error', function (payload) {
        hideElement('#loadingRow');
        const message = payload?.error?.message || '定时任务操作失败';
        toast.error(message);
    });
}

/**
 * 从 store 当前状态查找指定任务。
 *
 * @param {string|number} jobId 任务唯一标识。
 * @returns {Object|null} 若存在则返回任务对象，否则为 null。
 */
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

/**
 * 将选择器或 DOM 节点转换为 Umbrella.js 集合。
 *
 * @param {string|Element|NodeList|Array<Element>|Object} target 可解析对象。
 * @returns {Object} Umbrella.js 集合，便于统一 DOM 操作。
 */
function normalizeElements(target) {
    if (typeof target === 'string') {
        return select(target);
    }
    return from(target);
}

/**
 * 显示 DOM 元素。
 *
 * @param {string|Element|NodeList|Array<Element>} target 待展示节点。
 * @returns {void}
 */
function showElement(target) {
    const element = normalizeElements(target);
    if (!element.length) {
        return;
    }
    element.each((node) => {
        node.style.display = '';
    });
}

/**
 * 隐藏 DOM 元素。
 *
 * @param {string|Element|NodeList|Array<Element>} target 待隐藏节点。
 * @returns {void}
 */
function hideElement(target) {
    const element = normalizeElements(target);
    if (!element.length) {
        return;
    }
    element.each((node) => {
        node.style.display = 'none';
    });
}

/**
 * 清空元素内部 HTML。
 *
 * @param {string|Element|NodeList|Array<Element>} target DOM 节点或选择器。
 * @returns {void}
 */
function clearContainer(target) {
    const element = normalizeElements(target);
    if (!element.length) {
        return;
    }
    element.html('');
}

/**
 * 关闭新增任务模态框。
 *
 * @param {void} 无参数。函数内部查找 #addJobModal。
 * @returns {void}
 */
function hideAddJobModal() {
    const modalEl = document.getElementById('addJobModal');
    if (!modalEl || typeof bootstrap === 'undefined') {
        return;
    }
    const instance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    instance.hide();
}

function escapeHtml(value) {
    if (value === undefined || value === null) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

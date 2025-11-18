(function (window, document) {
    'use strict';

    function createController(options) {
        const {
            FormValidator,
            ValidationRules,
            toast,
            getJob,
            ensureStore,
            getStore,
            showLoadingState,
            hideLoadingState,
            timeUtils = window.timeUtils,
        } = options || {};

        if (!ensureStore || !getStore) {
            throw new Error('SchedulerModals: 缺少 store 访问方法');
        }

        const editModalEl = document.getElementById('editJobModal');
        const editForm = document.getElementById('editJobForm');
        const editModal = editModalEl ? new bootstrap.Modal(editModalEl) : null;
        let editValidator = null;

        function init() {
            if (FormValidator && ValidationRules && editForm) {
                editValidator = FormValidator.create('#editJobForm');
                editValidator
                    .useRules('#editJobName', ValidationRules.scheduler.jobName)
                    .useRules('#editJobFunction', ValidationRules.scheduler.jobFunction)
                    .useRules('#editCronSecond', ValidationRules.scheduler.cronField)
                    .useRules('#editCronMinute', ValidationRules.scheduler.cronField)
                    .useRules('#editCronHour', ValidationRules.scheduler.cronField)
                    .useRules('#editCronDay', ValidationRules.scheduler.cronField)
                    .useRules('#editCronMonth', ValidationRules.scheduler.cronField)
                    .useRules('#editCronWeekday', ValidationRules.scheduler.cronField)
                    .useRules('#editCronYear', ValidationRules.scheduler.cronYear)
                    .onSuccess(function (event) {
                        event?.preventDefault?.();
                        handleSubmit();
                    })
                    .onFail(function () {
                        toast?.error?.('请检查任务信息填写');
                    });
                ['#editJobName', '#editJobFunction', '#editCronSecond', '#editCronMinute', '#editCronHour', '#editCronDay', '#editCronMonth', '#editCronWeekday', '#editCronYear'].forEach(function (selector) {
                    const field = editForm.querySelector(selector);
                    if (!field) return;
                    const eventType = selector === '#editJobFunction' ? 'change' : 'input';
                    field.addEventListener(eventType, function () {
                        editValidator.revalidateField(selector);
                    });
                });
            }
        }

        function openEdit(jobId) {
            if (!ensureStore()) {
                return;
            }
            const job = getJob?.(jobId);
            if (!job) {
                toast?.error?.('任务不存在');
                return;
            }
            fillEditForm(job);
            editValidator?.refresh?.();
            editModal?.show();
        }

        function fillEditForm(job) {
            setFieldValue('#editJobId', job.id);
            setFieldValue('#editJobName', job.name);
            setFieldValue('#editJobDescription', job.description || '');

            const funcValue = job.func || job.name;
            const funcField = document.getElementById('editJobFunction');
            if (funcField) {
                funcField.value = funcValue;
                funcField.disabled = true;
                funcField.classList.add('form-control-plaintext');
            }

            // 触发器固定为 cron
            toggleTriggerConfig('cron');
            const triggerArgs = parseTriggerArgs(job.trigger_args);
            populateCron(triggerArgs);
        }

        function parseTriggerArgs(raw) {
            if (!raw) return {};
            if (typeof raw === 'string') {
                try {
                    return JSON.parse(raw);
                } catch (e) {
                    console.warn('解析 trigger_args 失败:', e);
                    return {};
                }
            }
            return raw;
        }

        function populateCron(triggerArgs) {
            if (!triggerArgs || typeof triggerArgs !== 'object') {
                return;
            }
            const cronExpression = triggerArgs.cron_expression || '';
            if (cronExpression) {
                const parts = cronExpression.trim().split(/\s+/);
                const [s = '0', m = '0', h = '0', d = '*', M = '*', w = '*', y = ''] =
                    parts.length === 5
                        ? ['0', parts[0], parts[1], parts[2], parts[3], parts[4], '']
                        : parts.length === 6
                            ? parts
                            : parts;
                setFieldValue('#editCronSecond', s || '0');
                setFieldValue('#editCronMinute', m || '0');
                setFieldValue('#editCronHour', h || '0');
                setFieldValue('#editCronDay', d || '*');
                setFieldValue('#editCronMonth', M || '*');
                setFieldValue('#editCronWeekday', w || '*');
                setFieldValue('#editCronYear', y || '');
            } else {
                setFieldValue('#editCronSecond', triggerArgs.second ?? '0');
                setFieldValue('#editCronMinute', triggerArgs.minute ?? '0');
                setFieldValue('#editCronHour', triggerArgs.hour ?? '0');
                setFieldValue('#editCronDay', triggerArgs.day ?? '*');
                setFieldValue('#editCronMonth', triggerArgs.month ?? '*');
                setFieldValue('#editCronWeekday', triggerArgs.day_of_week ?? '*');
                setFieldValue('#editCronYear', triggerArgs.year ?? '');
            }
            updateCronPreview();
        }

        function updateCronPreview() {
            const second = getFieldValue('#editCronSecond', '0');
            const minute = getFieldValue('#editCronMinute', '0');
            const hour = getFieldValue('#editCronHour', '0');
            const day = getFieldValue('#editCronDay', '*');
            const month = getFieldValue('#editCronMonth', '*');
            const weekday = getFieldValue('#editCronWeekday', '*');
            const year = getFieldValue('#editCronYear', '');
            const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
            const expression = year && year.trim() !== '' ? `${base} ${year}` : base;
            setFieldValue('#editCronPreview', expression);
        }

        function handleSubmit() {
            if (!ensureStore()) {
                return;
            }
            const formElement = editForm;
            const formData = new FormData(formElement);
            const jobId = formData.get('job_id');
            const originalJob = getJob?.(jobId);
            if (!originalJob) {
                toast?.error?.('任务不存在');
                return;
            }

            const payload = buildPayload(formElement, formData, originalJob);
            const submitButton = $(formElement).find('button[type="submit"]');
            showLoadingState?.(submitButton, '保存中...');

            getStore()
                .actions.updateJob(jobId, payload)
                .then(function () {
                    toast?.success?.('任务更新成功');
                    editModal?.hide();
                    editValidator?.refresh?.();
                })
                .catch(function (error) {
                    const message = error?.response?.message || error?.message || '未知错误';
                    toast?.error?.('更新失败: ' + message);
                })
                .finally(function () {
                    hideLoadingState?.(submitButton, '保存修改');
                });
        }

        function buildPayload(formElement, formData, originalJob) {
            const isBuiltInJob = [
                'sync_accounts',
                'cleanup_logs',
                'monitor_partition_health',
                'collect_database_sizes',
                'calculate_database_size_aggregations',
            ].includes(originalJob.id);

            const payload = {
                trigger_type: 'cron',
            };

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
            if (year && year.trim() !== '') {
                payload.year = year;
            }

            if (!isBuiltInJob) {
                payload.name = formData.get('name') || originalJob.name;
                const editFuncField = formElement.querySelector('#editJobFunction');
                if (editFuncField && !editFuncField.disabled) {
                    payload.func = editFuncField.value;
                } else {
                    payload.func = originalJob.func || originalJob.id;
                }
                payload.description = formData.get('description') || '';
            }

            return payload;
        }

        function toggleTriggerConfig(type) {
            document.querySelectorAll('.edit-trigger-config').forEach(function (el) {
                el.style.display = 'none';
            });
            if (type === 'cron') {
                const cronEl = document.getElementById('editCronConfig');
                if (cronEl) cronEl.style.display = '';
            }
        }

        function setFieldValue(selector, value) {
            const el = document.querySelector(selector);
            if (el) {
                el.value = value ?? '';
            }
        }

        function getFieldValue(selector, fallback) {
            const el = document.querySelector(selector);
            if (!el) return fallback;
            return el.value || fallback;
        }

        return {
            init,
            openEdit,
        };
    }

    window.SchedulerModals = {
        createController,
    };
})(window, document);

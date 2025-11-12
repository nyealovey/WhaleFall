/**
 * 标签表单公共脚本（创建 / 编辑）
 * 统一接入 Just-Validate 并处理提交状态。
 */

(function () {
    'use strict';

    let validator = null;
    let controller = null;

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('tagForm');
        if (!form) {
            return;
        }

        const root = document.getElementById('tag-form-root');
        const mode = root?.dataset.formMode || 'create';

        if (window.ResourceFormController) {
            controller = new window.ResourceFormController(form, {
                loadingText: mode === 'edit' ? '保存中...' : '创建中...',
            });
        }

        if (!window.FormValidator || !window.ValidationRules) {
            console.error('表单校验模块未正确加载');
            return;
        }

        validator = window.FormValidator.create('#tagForm');
        if (!validator) {
            return;
        }

        validator
            .useRules('#name', window.ValidationRules.tag.name)
            .useRules('#display_name', window.ValidationRules.tag.displayName)
            .useRules('#category', window.ValidationRules.tag.category)
            .useRules('#sort_order', window.ValidationRules.tag.sortOrder)
            .onSuccess(function (event) {
                controller?.toggleLoading(true);
                event.target.submit();
            })
            .onFail(function () {
                window.toast?.error('请检查标签表单填写');
            });

        setupRealtimeValidation();
        initializeColorPreview();
    });

    function setupRealtimeValidation() {
        const map = {
            '#name': 'blur',
            '#display_name': 'blur',
            '#category': 'change',
            '#sort_order': 'input',
        };
        Object.entries(map).forEach(([selector, eventName]) => {
            const element = document.querySelector(selector);
            if (element) {
                element.addEventListener(eventName, function () {
                    validator?.revalidateField(selector);
                });
            }
        });
    }

    function initializeColorPreview() {
        const select = document.getElementById('color');
        const preview = document.getElementById('colorPreview');
        if (!select || !preview) {
            return;
        }

        const updatePreview = () => {
            const value = select.value || 'primary';
            preview.className = 'badge bg-' + value;
        };

        select.addEventListener('change', updatePreview);
        updatePreview();
    }
})();

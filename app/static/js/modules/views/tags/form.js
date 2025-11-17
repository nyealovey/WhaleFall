/**
 * 标签表单公共脚本（创建 / 编辑）
 * 统一接入 Just-Validate 并处理提交状态。
 */
function mountTagForm(window) {
    'use strict';

    const helpers = window.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化，无法加载标签表单脚本');
        return;
    }

    const { ready, selectOne } = helpers;

    let validator = null;
    let controller = null;

    ready(() => {
        const form = selectOne('#tagForm');
        const formElement = form.first();
        if (!formElement) {
            return;
        }

        const root = selectOne('#tag-form-root').first();
        const mode = root?.dataset?.formMode || 'create';

        if (window.ResourceFormController) {
            controller = new window.ResourceFormController(formElement, {
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
            .onSuccess((event) => {
                controller?.toggleLoading(true);
                event.target.submit();
            })
            .onFail(() => {
                window.toast.error('请检查标签表单填写');
            });

        setupRealtimeValidation();
        initializeColorPreview();
    });

    function setupRealtimeValidation() {
        const map = [
            { selector: '#name', eventName: 'blur' },
            { selector: '#display_name', eventName: 'blur' },
            { selector: '#category', eventName: 'change' },
            { selector: '#sort_order', eventName: 'input' },
        ];

        map.forEach(({ selector, eventName }) => {
            const element = selectOne(selector);
            if (!element.length) {
                return;
            }
            element.on(eventName, () => {
                validator?.revalidateField(selector);
            });
        });
    }

    function initializeColorPreview() {
        const select = selectOne('#color');
        const preview = selectOne('#colorPreview');
        const selectEl = select.first();
        const previewEl = preview.first();

        if (!selectEl || !previewEl) {
            return;
        }

        const updatePreview = () => {
            const value = selectEl.value || 'primary';
            preview.attr('class', `badge bg-${value}`);
        };

        select.on('change', updatePreview);
        updatePreview();
    }
}

window.TagFormPage = {
    mount: function () {
        mountTagForm(window);
    },
};

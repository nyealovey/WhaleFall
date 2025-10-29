/**
 * 标签表单公共脚本（创建 / 编辑）
 * 统一接入 Just-Validate 并处理提交状态。
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('tagForm');
        if (!form) {
            return;
        }

        if (!window.FormValidator || !window.ValidationRules) {
            console.error('表单校验模块未正确加载');
            return;
        }

        const validator = window.FormValidator.create('#tagForm');
        if (!validator) {
            return;
        }

        validator
            .useRules('#name', window.ValidationRules.tag.name)
            .useRules('#display_name', window.ValidationRules.tag.displayName)
            .useRules('#category', window.ValidationRules.tag.category)
            .useRules('#sort_order', window.ValidationRules.tag.sortOrder)
            .onSuccess(function (event) {
                const targetForm = event.target;
                setSubmittingState(targetForm, true);
                targetForm.submit();
            })
            .onFail(function () {
                toast.error('请检查标签表单填写');
            });

        setupRealtimeValidation(validator);
    });

    function setupRealtimeValidation(validator) {
        const nameInput = document.getElementById('name');
        if (nameInput) {
            nameInput.addEventListener('blur', function () {
                validator.revalidateField('#name');
            });
        }

        const displayNameInput = document.getElementById('display_name');
        if (displayNameInput) {
            displayNameInput.addEventListener('blur', function () {
                validator.revalidateField('#display_name');
            });
        }

        const categorySelect = document.getElementById('category');
        if (categorySelect) {
            categorySelect.addEventListener('change', function () {
                validator.revalidateField('#category');
            });
        }

        const sortOrderInput = document.getElementById('sort_order');
        if (sortOrderInput) {
            sortOrderInput.addEventListener('input', function () {
                validator.revalidateField('#sort_order');
            });
        }
    }

    function setSubmittingState(form, isSubmitting) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (!submitBtn) {
            return;
        }

        if (isSubmitting) {
            submitBtn.dataset.originalText = submitBtn.dataset.originalText || submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>提交中...';
            submitBtn.disabled = true;
        } else if (submitBtn.dataset.originalText) {
            submitBtn.innerHTML = submitBtn.dataset.originalText;
            submitBtn.disabled = false;
        }
    }
})();

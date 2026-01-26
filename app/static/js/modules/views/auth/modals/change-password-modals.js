(function (window, document) {
  "use strict";

  const LOGIN_PAGE = "/auth/login";

  function resolveErrorMessage(error, fallback) {
    const fallbackText = fallback || "操作失败";
    if (!error) {
      return fallbackText;
    }
    if (typeof error === "string") {
      return error;
    }
    if (typeof error.message === "string" && error.message.trim()) {
      return error.message;
    }
    const nested = error?.response?.data || error?.data || null;
    if (nested && typeof nested.message === "string" && nested.message.trim()) {
      return nested.message;
    }
    return fallbackText;
  }

  function isTruthyParam(value) {
    if (value == null) {
      return false;
    }
    const normalized = String(value).trim().toLowerCase();
    return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
  }

  function stripUrlParam(key) {
    try {
      const url = new URL(window.location.href);
      if (!url.searchParams.has(key)) {
        return;
      }
      url.searchParams.delete(key);
      window.history.replaceState({}, "", url.toString());
    } catch {
      // 非关键路径: URL API 不可用时忽略
    }
  }

  function mountChangePasswordModal() {
    const modalEl = document.getElementById("changePasswordModal");
    if (!modalEl) {
      return;
    }
    const bootstrapLib = window.bootstrap;
    if (!bootstrapLib?.Modal) {
      console.error("ChangePasswordModals: bootstrap.Modal 未加载");
      return;
    }
    const AuthService = window.AuthService;
    const createAuthStore = window.createAuthStore;
    if (!AuthService || typeof createAuthStore !== "function") {
      console.error("ChangePasswordModals: AuthService/AuthStore 未加载");
      return;
    }
    let store = null;
    try {
      store = createAuthStore({
        service: new AuthService(),
      });
    } catch (error) {
      console.error("ChangePasswordModals: 初始化 AuthStore 失败", error);
      return;
    }

    const toast = window.toast;
    const FormValidator = window.FormValidator;
    const ValidationRules = window.ValidationRules;

    const modal = new bootstrapLib.Modal(modalEl);
    const form = document.getElementById("changePasswordModalForm");
    const submitBtn = document.getElementById("changePasswordModalSubmit");
    if (!(form instanceof HTMLFormElement)) {
      console.error("ChangePasswordModals: 找不到 #changePasswordModalForm");
      return;
    }

    let validator = null;

    function init() {
      bindOpenActions();
      bindAutoOpenFromQuery();
      setupValidation();
      modalEl.addEventListener("hidden.bs.modal", resetForm);
    }

    function bindOpenActions() {
      document.querySelectorAll('[data-action="open-change-password"]').forEach((node) => {
        node.addEventListener("click", (event) => {
          event.preventDefault();
          modal.show();
        });
      });
    }

    function bindAutoOpenFromQuery() {
      try {
        const params = new URLSearchParams(window.location.search || "");
        if (!isTruthyParam(params.get("open_change_password"))) {
          return;
        }
        stripUrlParam("open_change_password");
        modal.show();
      } catch {
        // 非关键路径: URLSearchParams 不可用时忽略
      }
    }

    function setupValidation() {
      if (!FormValidator || !ValidationRules) {
        console.warn("ChangePasswordModals: FormValidator 或 ValidationRules 未加载");
        form.addEventListener("submit", handleSubmit);
        return;
      }

      validator = FormValidator.create("#changePasswordModalForm");
      if (!validator) {
        console.warn("ChangePasswordModals: FormValidator 初始化失败");
        form.addEventListener("submit", handleSubmit);
        return;
      }

      const newPasswordRules = ValidationRules.auth.changePassword.newPassword.slice();
      newPasswordRules.push({
        validator(value, fields) {
          const oldPasswordField = fields["#old_password"];
          const oldPassword = oldPasswordField ? oldPasswordField.elem.value : "";
          return value !== oldPassword;
        },
        errorMessage: "新密码不能与当前密码相同",
      });

      validator
        .useRules("#old_password", ValidationRules.auth.changePassword.oldPassword)
        .useRules("#new_password", newPasswordRules)
        .useRules("#confirm_password", ValidationRules.auth.changePassword.confirmPassword)
        .onSuccess(handleSubmit)
        .onFail(() => toast?.error?.("请检查密码修改表单填写"));
    }

    function resetForm() {
      form.reset();
      if (validator?.instance?.refresh) {
        validator.instance.refresh();
      }
      toggleLoading(false);
    }

    function toggleLoading(loading) {
      if (!submitBtn) {
        return;
      }
      submitBtn.disabled = Boolean(loading);
      if (loading) {
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>更新中...';
      } else {
        submitBtn.textContent = "更新密码";
      }
    }

    function buildPayload() {
      const data = new FormData(form);
      return {
        old_password: data.get("old_password"),
        new_password: data.get("new_password"),
        confirm_password: data.get("confirm_password"),
      };
    }

    async function handleSubmit(event) {
      event.preventDefault();
      toggleLoading(true);
      try {
        const payload = buildPayload();
        const resp = await store.actions.changePassword(payload);
        toast?.success?.(resp?.message || "密码修改成功");

        try {
          await store.actions.logout();
        } catch (logoutError) {
          console.warn("ChangePasswordModals: 登出失败, 将继续跳转登录页", logoutError);
        }
        window.location.href = LOGIN_PAGE;
      } catch (error) {
        console.error("ChangePasswordModals: 修改密码失败", error);
        toast?.error?.(resolveErrorMessage(error, "密码修改失败"));
        toggleLoading(false);
      }
    }

    init();
  }

  document.addEventListener("DOMContentLoaded", mountChangePasswordModal);
})(window, document);

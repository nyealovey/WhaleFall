(function (global) {
  "use strict";

  function createView(options) {
    const {
      PermissionPolicyCenter = global.PermissionPolicyCenter,
      toast = global.toast,
      handleRequestError,
    } = options || {};

    if (!PermissionPolicyCenter) {
      throw new Error("policy-center-view: PermissionPolicyCenter 未加载");
    }

    function loadByPrefix(prefix = "") {
      const elementId = prefix ? `${prefix}RuleDbType` : "ruleDbType";
      const dbTypeElement = document.getElementById(elementId);
      if (!dbTypeElement) {
        console.error("找不到数据库类型选择元素:", elementId);
        return Promise.resolve();
      }

      const dbType = dbTypeElement.value;
      const containerId = prefix ? `${prefix}PermissionsConfig` : "permissionsConfig";

      return PermissionPolicyCenter.load(dbType, containerId, prefix).catch(error => {
        handleRequestError?.(error, "加载权限配置失败", "load_permissions");
      });
    }

    return {
      loadByPrefix,
      load: PermissionPolicyCenter.load?.bind(PermissionPolicyCenter),
      reset: PermissionPolicyCenter.reset?.bind(PermissionPolicyCenter),
      collectSelected: PermissionPolicyCenter.collectSelected?.bind(PermissionPolicyCenter),
      hasSelection: PermissionPolicyCenter.hasSelection?.bind(PermissionPolicyCenter),
      buildExpression: PermissionPolicyCenter.buildExpression?.bind(PermissionPolicyCenter),
      renderDisplay: PermissionPolicyCenter.renderDisplay?.bind(PermissionPolicyCenter),
      setSelected: PermissionPolicyCenter.setSelected?.bind(PermissionPolicyCenter),
    };
  }

  global.AccountClassificationPermissionView = {
    createView,
  };
})(window);

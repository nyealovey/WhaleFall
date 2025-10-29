/**
 * ValidationRules - 通用验证规则集合
 *
 * 提供各业务模块共享的规则与消息，便于集中维护。
 */
(function (global) {
    'use strict';

    var helpers = {
        required: function required(message) {
            return {
                rule: 'required',
                errorMessage: message,
            };
        },
        minLength: function minLength(length, message) {
            return {
                rule: 'minLength',
                value: length,
                errorMessage: message,
            };
        },
        maxLength: function maxLength(length, message) {
            return {
                rule: 'maxLength',
                value: length,
                errorMessage: message,
            };
        },
        email: function email(message) {
            return {
                rule: 'email',
                errorMessage: message,
            };
        },
        number: function number(message) {
            return {
                rule: 'number',
                errorMessage: message,
            };
        },
        minNumber: function minNumber(value, message) {
            return {
                rule: 'minNumber',
                value: value,
                errorMessage: message,
            };
        },
        maxNumber: function maxNumber(value, message) {
            return {
                rule: 'maxNumber',
                value: value,
                errorMessage: message,
            };
        },
        custom: function custom(validator, message) {
            return {
                validator: validator,
                errorMessage: message,
            };
        },
    };

    var messages = {
        required: '此字段不能为空',
        minLength: function minLength(length) {
            return '至少需要 ' + length + ' 个字符';
        },
        passwordLength: '密码至少需要 6 个字符',
        usernameLength: '用户名至少需要 2 个字符',
        loginUsername: '用户名至少需要 3 个字符',
        credentialType: '请选择凭据类型',
        credentialDbType: '请选择数据库类型',
        instanceName: '实例名称不能为空',
        host: '主机地址不能为空',
        port: '端口号必须在 1-65535 之间',
        credential: '请选择凭据',
        tagCode: '标签代码不能为空',
        tagCodeLength: '标签代码至少需要 2 个字符',
        tagCodeFormat: '标签代码仅支持字母、数字、下划线或中划线',
        tagDisplayName: '显示名称不能为空',
        tagDisplayNameLength: '显示名称至少需要 2 个字符',
        tagCategory: '请选择标签分类',
        tagSortOrder: '排序顺序必须是大于等于 0 的整数',
        classificationName: '分类名称不能为空',
        classificationNameLength: '分类名称至少需要 2 个字符',
        classificationColor: '请选择显示颜色',
        classificationPriority: '优先级必须是 0-100 之间的整数',
        classificationRuleName: '规则名称不能为空',
        classificationRuleNameLength: '规则名称至少需要 2 个字符',
        classificationRuleClassification: '请选择分类',
        classificationRuleDbType: '请选择数据库类型',
        classificationRuleOperator: '请选择匹配逻辑',
        confirmPassword: '请再次输入新密码',
    };

    var credentialRules = {
        name: [
            helpers.required('凭据名称不能为空'),
            helpers.minLength(2, '凭据名称至少需要2个字符'),
        ],
        credentialType: [helpers.required(messages.credentialType)],
        dbType: [
            helpers.custom(function (value, fields) {
                var credentialTypeField = fields['#credential_type'];
                var credentialType = credentialTypeField ? credentialTypeField.elem.value : '';

                if (credentialType !== 'database') {
                    return true;
                }
                return value != null && String(value).trim().length > 0;
            }, messages.credentialDbType),
        ],
        username: [
            helpers.required('用户名不能为空'),
            helpers.minLength(2, messages.usernameLength),
        ],
        password: [
            helpers.required('密码不能为空'),
            helpers.minLength(6, messages.passwordLength),
        ],
    };

    var authRules = {
        login: {
            username: [
                helpers.required('请输入用户名'),
                helpers.minLength(3, messages.loginUsername),
            ],
            password: [
                helpers.required('请输入密码'),
                helpers.minLength(6, messages.passwordLength),
            ],
        },
        changePassword: {
            oldPassword: [helpers.required('请输入当前密码')],
            newPassword: [
                helpers.required('请输入新密码'),
                helpers.minLength(6, messages.passwordLength),
            ],
            confirmPassword: [
                helpers.required(messages.confirmPassword),
                helpers.custom(function (value, fields) {
                    var newPasswordField = fields['#new_password'];
                    var newPassword = newPasswordField ? newPasswordField.elem.value : '';
                    return value === newPassword;
                }, '两次输入的新密码不一致'),
            ],
        },
    };

    var instanceRules = {
        name: [
            helpers.required(messages.instanceName),
            helpers.minLength(2, '实例名称至少需要2个字符'),
        ],
        dbType: [helpers.required('请选择数据库类型')],
        host: [helpers.required(messages.host)],
        port: [
            helpers.required(messages.port),
            helpers.number(messages.port),
            helpers.minNumber(1, messages.port),
            helpers.maxNumber(65535, messages.port),
        ],
        credential: [helpers.required(messages.credential)],
    };

    var classificationRules = {
        name: [
            helpers.required(messages.classificationName),
            helpers.minLength(2, messages.classificationNameLength),
        ],
        color: [helpers.required(messages.classificationColor)],
        priority: [
            helpers.custom(function (value) {
                if (value == null || String(value).trim() === '') {
                    return true;
                }
                var num = Number(value);
                return Number.isInteger(num) && num >= 0 && num <= 100;
            }, messages.classificationPriority),
        ],
    };

    var classificationRuleRules = {
        classification: [helpers.required(messages.classificationRuleClassification)],
        name: [
            helpers.required(messages.classificationRuleName),
            helpers.minLength(2, messages.classificationRuleNameLength),
        ],
        dbType: [helpers.required(messages.classificationRuleDbType)],
        operator: [helpers.required(messages.classificationRuleOperator)],
    };

    var tagRules = {
        name: [
            helpers.required(messages.tagCode),
            helpers.minLength(2, messages.tagCodeLength),
            helpers.custom(function (value) {
                if (value == null) {
                    return false;
                }
                const normalized = String(value).trim();
                if (!normalized) {
                    return false;
                }
                return /^[A-Za-z0-9_-]+$/.test(normalized);
            }, messages.tagCodeFormat),
        ],
        displayName: [
            helpers.required(messages.tagDisplayName),
            helpers.minLength(2, messages.tagDisplayNameLength),
        ],
        category: [helpers.required(messages.tagCategory)],
        sortOrder: [
            helpers.custom(function (value) {
                if (value == null || String(value).trim() === '') {
                    return true;
                }
                const num = Number(value);
                return Number.isInteger(num) && num >= 0;
            }, messages.tagSortOrder),
        ],
    };

    global.ValidationRules = Object.assign({}, global.ValidationRules, {
        helpers: helpers,
        messages: messages,
        credential: credentialRules,
        auth: authRules,
        instance: instanceRules,
        classification: classificationRules,
        classificationRule: classificationRuleRules,
        tag: tagRules,
    });
})(window);

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
    };

    global.ValidationRules = Object.assign({}, global.ValidationRules, {
        helpers: helpers,
        messages: messages,
        credential: credentialRules,
        auth: authRules,
    });
})(window);

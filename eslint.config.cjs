const eslintJs = require("@eslint/js");
const globals = require("globals");
const importPlugin = require("eslint-plugin-import");
const securityPlugin = require("eslint-plugin-security");

const importRecommendedRules = importPlugin.configs.recommended?.rules ?? {};
const securityRecommendedRules = securityPlugin.configs.recommended?.rules ?? {};

module.exports = [
  {
    ignores: [
      "node_modules/**",
      "app/static/vendor/**",
      "app/static/js/modules/README.md",
    ],
  },
  eslintJs.configs.recommended,
  {
    files: ["app/static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        ...globals.browser,
      },
    },
    plugins: {
      import: importPlugin,
      security: securityPlugin,
    },
    settings: {
      "import/extensions": [".js"],
      "import/resolver": {
        node: {
          extensions: [".js"],
        },
      },
    },
    rules: {
      ...importRecommendedRules,
      ...securityRecommendedRules,
      "import/no-commonjs": "off",
      "import/no-unresolved": ["error", { commonjs: true, amd: false }],
      "import/order": [
        "error",
        {
          groups: [["builtin", "external"], "internal", "parent", "sibling", "index", "object", "type"],
          "newlines-between": "always",
          alphabetize: { order: "asc", caseInsensitive: true },
        },
      ],
    },
  },
];

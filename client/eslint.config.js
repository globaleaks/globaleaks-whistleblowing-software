// @ts-check
const eslint = require("@eslint/js");
const tseslint = require("typescript-eslint");
const angular = require("angular-eslint");

module.exports = tseslint.config(
  {
    files: ["**/*.ts"],
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.recommended,
      ...tseslint.configs.stylistic,
      ...angular.configs.tsRecommended,
    ],
    processor: angular.processInlineTemplates,
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: __dirname,
      },
    },
    rules: {
      "@angular-eslint/directive-selector": [
        "error",
        {
          type: "attribute",
          prefix: ["src", "app", "flow"],
          style: "camelCase",
        },
      ],
      "@angular-eslint/component-selector": [
        "error",
        {
          type: "element",
          prefix: ["src", "app"],
          style: "kebab-case",
        },
      ],
      // Reported, not enforced: the remaining `any` are being removed
      // incrementally while the models get typed.
      "@typescript-eslint/no-explicit-any": "warn",
      // A member assigned once and never reassigned is readonly: keeps the
      // SonarQube S2933 debt from growing back.
      "@typescript-eslint/prefer-readonly": "error",
      // Deprecated APIs break at the next major: fix them as they appear.
      "@typescript-eslint/no-deprecated": "error",
      // A promise nobody awaits or catches fails in silence: mark the
      // fire-and-forget ones with `void`, handle the others.
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
    },
  },
  {
    files: ["cypress/**/*.ts"],
    rules: {
      // A Cypress chain is a thenable, not a promise: it is enqueued, never
      // awaited, and the promise rules would flag every command.
      "@typescript-eslint/no-floating-promises": "off",
      "@typescript-eslint/no-misused-promises": "off",
    },
  },
  {
    files: ["**/*.html"],
    extends: [
      ...angular.configs.templateRecommended,
      ...angular.configs.templateAccessibility,
    ],
    rules: {
      // Reported, not enforced: the labels of the templates are still to be tied to their controls.
      "@angular-eslint/template/label-has-associated-control": "warn",
    },
  }
);

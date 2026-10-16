import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";
import globals from "globals";

/**
 * ESLint owns correctness, Prettier owns layout, and `tsc`/`vue-tsc` own types — so no type-aware
 * rules here: the three type projects already answer those questions and a second type channel
 * would only disagree with them.
 */
export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "coverage/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  {
    languageOptions: {
      globals: { ...globals.node, ...globals.browser },
      parserOptions: { parser: tseslint.parser },
    },
    rules: {
      // The console has its own components; a stray `console.log` is a leftover, not a feature.
      "no-console": ["error", { allow: ["warn", "error"] }],
      // `_name` is how this codebase marks a parameter or binding it means to ignore.
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_" },
      ],
      // Types are erased at runtime: keep the import that says so.
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { fixStyle: "separate-type-imports" },
      ],
      // `App` and `LoginView` are route components; the rule only adds noise here.
      "vue/multi-word-component-names": "off",
    },
  },
  {
    files: ["src/browser/**/*.{ts,vue}"],
    rules: {
      // A page or a component may log nothing; the browser has no logger to route through.
      "no-console": "error",
    },
  },
  {
    files: ["scripts/**/*.ts", "e2e/**/*.ts", "*.config.{ts,js}"],
    rules: {
      // Command-line tools and test code report through stdout by design.
      "no-console": "off",
    },
  },
  prettier,
);

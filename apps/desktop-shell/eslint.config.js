// ESLint 9 (flat config) — .eslintrc.json não é mais o padrão a partir do ESLint 9; ver
// tasks.md T004 (ajustado para refletir isso após tentativa real de `npx eslint`).
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.ts", "tests/**/*.ts"],
    languageOptions: {
      parserOptions: {
        project: "./tsconfig.json",
      },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": "error",
    },
  },
  {
    ignores: ["dist/**", "node_modules/**", "eslint.config.js", "vite.config.ts"],
  },
);

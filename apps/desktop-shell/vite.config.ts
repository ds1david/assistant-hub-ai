import { defineConfig } from "vitest/config";

// Shell desktop Tauri 2 — ver plan.md § Project Structure. `clearScreen: false` e a porta
// fixa seguem a convenção padrão de projetos Tauri (o CLI Rust observa este servidor de dev).
// Issue #41: import from vitest/config for Vite 8 + Vitest 4 (minimal adaptation).
export default defineConfig({
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
  },
});

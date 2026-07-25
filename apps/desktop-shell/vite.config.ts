import { defineConfig } from "vitest/config";

// Shell desktop Tauri 2 — ver plan.md § Project Structure. `clearScreen: false` e a porta
// fixa seguem a convenção padrão de projetos Tauri (o CLI Rust observa este servidor de dev).
// Issue #41: import from vitest/config for Vite 8 + Vitest 4 (minimal adaptation).
// Não observar src-tauri: o Vite tenta watchar .exe em target/debug/build e falha com
// EBUSY no Windows, derrubando beforeDevCommand e o `cargo tauri dev` inteiro.
export default defineConfig({
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
  },
});

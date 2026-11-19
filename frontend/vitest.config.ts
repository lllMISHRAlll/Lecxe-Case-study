import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules/**", ".next/**"],
    css: false,
    coverage: {
      provider: "v8",
      include: ["app/**", "components/**", "hooks/**", "lib/**", "stores/**", "middleware.ts"],
      exclude: ["**/*.test.{ts,tsx}", "app/layout.tsx", "app/providers.tsx", "lib/types.ts"],
      reporter: ["text", "text-summary"],
      thresholds: {
        lines: 80,
        "lib/sse.ts": { branches: 100 },
        "components/po/POCard.tsx": { branches: 100 },
        "components/auth/LoginForm.tsx": { branches: 100 },
      },
    },
  },
});

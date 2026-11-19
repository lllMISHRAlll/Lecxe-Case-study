import { defineConfig, devices } from "@playwright/test";

const BACKEND_PORT = 8001;
const FRONTEND_PORT = 3100;
export const E2E_DATABASE_URL = "postgresql://postgres:postgres@localhost:55432/assistant_e2e";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  globalSetup: "./global-setup.ts",
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `../backend/.venv/bin/uvicorn app.main:create_app --factory --port ${BACKEND_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${BACKEND_PORT}/api/health`,
      reuseExistingServer: true,
      env: {
        DATABASE_URL: E2E_DATABASE_URL,
        DATABASE_SSLMODE: "disable",
        FAKE_LLM: "true",
        DEMO_LOGIN_PASSWORD: "1234567890",
        APP_ENV: "dev",
      },
    },
    {
      command: `npx next dev -p ${FRONTEND_PORT}`,
      cwd: "../frontend",
      url: `http://localhost:${FRONTEND_PORT}/login`,
      reuseExistingServer: true,
      env: { BACKEND_URL: `http://localhost:${BACKEND_PORT}` },
    },
  ],
});

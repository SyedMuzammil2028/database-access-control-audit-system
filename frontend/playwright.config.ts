import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 120000,
  expect: { timeout: 20000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:8000",
    browserName: "chromium",
    headless: true,
    actionTimeout: 20000,
    navigationTimeout: 30000,
    viewport: { width: 1440, height: 1000 },
    trace: "off",
    launchOptions: { args: ["--renderer-process-limit=2", "--disable-gpu"] },
    screenshot: "only-on-failure",
  },
});

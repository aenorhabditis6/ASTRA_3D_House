import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  fullyParallel: false,
  timeout: 30_000,
  outputDir: "output/playwright/test-results",
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:8765",
    locale: "zh-CN",
    timezoneId: "America/Los_Angeles",
    colorScheme: "light",
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: [8765, 8766, 8767].map((port, index) => ({
    command: `python3 -m http.server ${port} --bind 127.0.0.1 --directory ${index === 2 ? 'build/dorm-right-bedroom/capture-candidate' : `build/browser-simulation/capture-pack${index ? "-third-mode" : ""}`}`,
    url: `http://127.0.0.1:${port}/index.html`,
    reuseExistingServer: false,
  })),
});

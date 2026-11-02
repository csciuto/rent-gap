const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://localhost:8091' },
  webServer: {
    command: 'python3 -m http.server 8091',
    url: 'http://localhost:8091',
    reuseExistingServer: !process.env.CI,
  },
});

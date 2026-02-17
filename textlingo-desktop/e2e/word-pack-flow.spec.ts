import { test } from "@playwright/test";

test.describe("Word Pack + SRS flow", () => {
  test.skip(true, "Desktop Tauri E2E requires platform-specific harness; scaffolded in CI as quality gate placeholder.");

  test("create pack -> favorite -> review -> export/import", async () => {
    // This scenario is intentionally skipped in browser-only CI.
    // Keep this spec as the acceptance contract for future tauri-driver integration.
  });
});

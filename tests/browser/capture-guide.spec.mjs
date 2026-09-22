import { expect, test } from "@playwright/test";
import { pathToFileURL } from "node:url";

const THIRD_URL = "http://127.0.0.1:8766/index.html";
const KEY_PREFIX = "astra.capture.v2/room:dorm-right-bedroom/capture:dorm-right-bedroom-diagnostic-01/mode:";

async function chooseMode(page, modeId) {
  await page.locator(`button[data-mode-id="${modeId}"]`).click();
  const acknowledgement = page.getByLabel("I checked the Xiaomi settings");
  if (await acknowledgement.count()) {
    await acknowledgement.check();
    await page.getByRole("button", { name: "Start route", exact: true }).click();
  }
}

async function startMode(page, modeId = "lite-24", url = "/index.html") {
  await page.goto(url);
  await chooseMode(page, modeId);
}

async function confirmCurrent(page) {
  await page.getByRole("button", { name: /^I am at station \d/ }).click();
}

async function readExport(page) {
  const pending = page.waitForEvent("download");
  await page.locator("#export-progress").click();
  const download = await pending;
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString("utf8");
  expect(text.endsWith("\n")).toBe(true);
  return JSON.parse(text);
}

async function storedMode(page, modeId = "lite-24") {
  return page.evaluate(({ prefix, modeId }) => {
    const key = Object.keys(localStorage).find(key => key.startsWith(`${prefix}${modeId}/hash/`) && !key.includes("/corrupt/"));
    return { key, record: key ? JSON.parse(localStorage.getItem(key)) : null };
  }, { prefix: KEY_PREFIX, modeId });
}

async function updateStoredMode(page, mutate, modeId = "lite-24") {
  const saved = await storedMode(page, modeId);
  expect(saved.record).not.toBeNull();
  mutate(saved.record);
  await page.evaluate(({ key, record }) => localStorage.setItem(key, JSON.stringify(record)), saved);
  return saved;
}

async function completeRoute(page) {
  for (let step = 0; step < 80; step += 1) {
    const complete = page.getByRole("button", { name: "All photos taken — complete group", exact: true });
    if (!await complete.count()) return;
    if (await complete.isDisabled()) await confirmCurrent(page);
    await complete.click();
  }
  throw new Error("Route failed to reach a handoff after 80 groups");
}

test("capture controller gates shots and records auditable manual events", async ({ page }) => {
  await startMode(page, "standard-48");
  await expect(page.getByLabel("A01-L", { exact: true })).toBeDisabled();
  await confirmCurrent(page);
  await page.getByLabel("A01-L", { exact: true }).check();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  const data = await readExport(page);
  expect(data.pending_shot_ids).toHaveLength(47);
  expect(data.events.map(event => event.type)).toEqual(["capture_started", "station_confirmed", "shot_completed"]);
  expect(data.mode_plan_sha256).toMatch(/^[0-9a-f]{64}$/);
  for (const [index, event] of data.events.entries()) {
    expect(event).toMatchObject({ seq: index + 1, tz_offset_min: -420, room_id: data.room_id, capture_id: data.capture_id, mode_id: data.mode_id, mode_plan_sha256: data.mode_plan_sha256 });
    expect(Number.isInteger(event.t_ms)).toBe(true);
  }
  expect(data.events[1]).toMatchObject({ station_id: "S01", method: "manual_station" });
  expect(data.events[2]).toMatchObject({ group_id: "STD-A01", station_id: "S01", shot_ids: ["A01-L"], method: "shot" });
  expect(data.first_event_t_ms).toBe(data.events[0].t_ms);
  expect(data.last_event_t_ms).toBe(data.events.at(-1).t_ms);
  expect(data).toHaveProperty("coverage_review_status");
  expect(data).toHaveProperty("coverage_review_digest");
});

test("group completion records only pending shots in displayed order and advances", async ({ page }) => {
  await startMode(page, "standard-48");
  await confirmCurrent(page);
  const initialIds = await page.locator('#task-view input[type="checkbox"][data-shot-id]').evaluateAll(nodes => nodes.map(node => node.dataset.shotId));
  await page.getByLabel(initialIds[0], { exact: true }).check();
  await page.getByRole("button", { name: "All photos taken — complete group", exact: true }).click();
  const data = await readExport(page);
  expect(data.events.at(-1)).toMatchObject({ type: "group_completed", shot_ids: initialIds.slice(1), method: "group", within_group_order: "inferred" });
  await expect(page.getByTestId("current-station")).not.toHaveText("1");
  await expect(page.locator('#task-view input[type="checkbox"]').first()).toBeDisabled();
});

test("capture traversal searches forward then wraps and keeps same-station confirmation", async ({ page }) => {
  await startMode(page, "standard-48");
  const groups = await page.locator("#capture-data").evaluate(node => JSON.parse(node.textContent).modes.find(mode => mode.id === "standard-48").passes.flatMap(pass => pass.groups));
  await page.locator('button[data-station-id="S08"]').click();
  const finalStationFirst = groups.findIndex(group => group.station_id === "S08");
  await page.getByRole("button", { name: "Next incomplete", exact: true }).click();
  await expect(page.locator("#task-view")).toContainText(groups[finalStationFirst + 1].id);
  for (let index = finalStationFirst + 2; index <= groups.length; index += 1) await page.getByRole("button", { name: "Next incomplete", exact: true }).click();
  await expect(page.locator("#task-view")).toContainText(groups[0].id);
  // B-pass groups are consecutive at one station; navigate there without resolving shots.
  const sameStationIndex = groups.findIndex((group, index) => groups[index + 1]?.station_id === group.station_id);
  expect(sameStationIndex).toBeGreaterThanOrEqual(0);
  for (let index = 0; index < sameStationIndex; index += 1) await page.getByRole("button", { name: "Next incomplete", exact: true }).click();
  await confirmCurrent(page);
  await page.getByRole("button", { name: "All photos taken — complete group", exact: true }).click();
  await expect(page.locator("#task-view")).toContainText(groups[sameStationIndex + 1].id);
  await expect(page.getByRole("button", { name: "All photos taken — complete group", exact: true })).toBeEnabled();
});

test("map arrows retain resolved shots and expose independent station states", async ({ page }) => {
  await startMode(page);
  const marker = page.locator('.station-marker[data-station-id="S01"]');
  await expect(marker).toHaveAttribute("data-pass-state", "current");
  await expect(marker).toHaveAttribute("data-mode-state", "upcoming");
  await expect(page.locator('.shot-ray[data-shot-id="L01-A"]')).toHaveClass(/current/);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await expect(page.locator('.shot-ray[data-shot-id="L01-A"]')).toBeVisible();
  await expect(page.locator('.shot-ray[data-shot-id="L01-A"]')).toHaveClass(/completed/);
  await expect(page.locator('.shot-ray[data-shot-id="L01-B"]')).toHaveClass(/current/);
  await expect(marker).toHaveAttribute("data-mode-state", "in-progress");
  const before = await readExport(page);
  await page.locator("#toggle-diagnostics").click();
  await expect(page.locator('.shot-cone[data-shot-id="L01-B"]')).toBeVisible();
  expect((await readExport(page)).events).toEqual(before.events);
});

test("repeated unchanged note save emits no event", async ({ page }) => {
  await startMode(page);
  const note = page.getByLabel("Note for L01-A", { exact: true });
  await note.fill("Keep this retake");
  await page.locator(".shot-card").filter({ has: note }).getByRole("button", { name: "Save note", exact: true }).click();
  const before = await readExport(page);
  await page.locator(".shot-card").filter({ has: note }).getByRole("button", { name: "Save note", exact: true }).click();
  expect((await readExport(page)).events).toEqual(before.events);
});

test("static DOM preserves every source instruction exactly", async ({ page }) => {
  await page.goto("/index.html");
  const mismatches = await page.evaluate(() => {
    const data = JSON.parse(document.getElementById("capture-data").textContent);
    return data.modes.flatMap(mode => mode.passes.flatMap(pass => pass.groups.flatMap(group => group.shots))).filter(shot => document.querySelector(`[data-static-shot-id="${shot.id}"] p`)?.textContent !== shot.instruction).map(shot => shot.id);
  });
  expect(mismatches).toEqual([]);
  await expect(page.locator("[data-static-shot-id]")).toHaveCount(72);
});

test("station navigation and diagnostics do not mutate status or event log", async ({ page }) => {
  await startMode(page, "standard-48");
  const before = await readExport(page);
  for (let number = 1; number <= 8; number += 1) {
    const button = page.locator('button[data-station-id]').filter({ hasText: new RegExp(`^Station ${number} ·`) });
    await button.click();
    await expect(page.getByTestId("current-station")).toHaveText(String(number));
    await expect(page.getByTestId("complete-count")).toHaveText("0");
    expect(await button.evaluate(node => { const r = node.getBoundingClientRect(); return node.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)); })).toBe(true);
  }
  await page.locator("#toggle-diagnostics").click();
  expect((await readExport(page)).events).toEqual(before.events);
});

test("native station navigation has visible keyboard focus and selects on Enter", async ({ page }) => {
  await startMode(page);
  const station = page.locator('button[data-station-id="S04"]');
  await page.keyboard.press("Tab");
  await station.focus();
  await expect(station).toBeFocused();
  const outline = await station.evaluate(node => ({ style: getComputedStyle(node).outlineStyle, width: getComputedStyle(node).outlineWidth }));
  expect(outline.style).not.toBe("none");
  expect(parseFloat(outline.width)).toBeGreaterThanOrEqual(2);
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("current-station")).toHaveText("4");
});

test("completed station remains reachable and can reopen without renewed confirmation", async ({ page }) => {
  await startMode(page, "test-3", THIRD_URL);
  await confirmCurrent(page);
  await page.getByLabel("T-ONLY", { exact: true }).click();
  await page.reload();
  await page.locator('button[data-station-id="S01"]').click();
  await expect(page.getByLabel("T-ONLY", { exact: true })).toBeChecked();
  await page.getByLabel("T-ONLY", { exact: true }).uncheck();
  await expect(page.getByTestId("complete-count")).toHaveText("0");
  expect((await readExport(page)).events.at(-1).type).toBe("shot_reopened");
});

test("reload restores persisted progress and cursor without station confirmation", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await page.reload();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  await expect(page.getByLabel("L01-B", { exact: true })).toBeDisabled();
  const saved = await storedMode(page);
  expect(saved.key).toMatch(/\/hash\/[0-9a-f]{64}$/);
  expect(saved.record).not.toHaveProperty("confirmedStationId");
  expect((await readExport(page)).events.filter(event => event.type === "capture_started")).toHaveLength(1);
});

test("two consecutive undo actions compensate distinct events after reload", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await page.getByLabel("L01-B", { exact: true }).click();
  await page.reload();
  await page.locator("#undo-action").click();
  await page.locator("#undo-action").click();
  await expect(page.getByTestId("complete-count")).toHaveText("0");
  const data = await readExport(page);
  const undo = data.events.filter(event => event.type === "undo");
  expect(undo.map(event => event.undoes_seq)).toEqual([4, 3]);
  expect(undo.every(event => data.events[event.undoes_seq - 1].type !== "undo")).toBe(true);
});

test("undo can restore a reopened completed shot without confirmation", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await page.getByLabel("L01-A", { exact: true }).uncheck();
  await page.reload();
  await page.locator("#undo-action").click();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  expect((await readExport(page)).events.at(-1)).toMatchObject({ type: "undo", undoes_seq: 4 });
});

test("mode switching isolates progress and confirmed reset only clears selected mode", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await page.locator("#change-mode").click();
  await chooseMode(page, "standard-48");
  await expect(page.getByTestId("complete-count")).toHaveText("0");
  await confirmCurrent(page);
  await page.getByLabel("A01-L", { exact: true }).check();
  page.once("dialog", dialog => dialog.dismiss());
  await page.locator("#reset-mode").click();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  page.once("dialog", dialog => dialog.accept());
  await page.locator("#reset-mode").click();
  await expect(page.getByLabel("I checked the Xiaomi settings")).toBeVisible();
  await expect(page.locator("#task-view button")).toHaveCount(0);
  await page.getByLabel("I checked the Xiaomi settings").check();
  await page.getByRole("button", { name: "Start route", exact: true }).click();
  await expect(page.getByTestId("complete-count")).toHaveText("0");
  expect((await readExport(page)).events.map(event => event.type)).toEqual(["capture_started"]);
  await page.locator("#change-mode").click();
  await chooseMode(page, "lite-24");
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  expect((await readExport(page)).events.filter(event => event.type === "capture_started")).toHaveLength(1);
});

test("invalid cursor recovers first pending group without discarding events", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await updateStoredMode(page, record => { record.last_group_id = "NO-SUCH-GROUP"; });
  await page.reload();
  await expect(page.getByTestId("complete-count")).toHaveText("1");
  await expect(page.getByTestId("current-station")).toHaveText("1");
  expect((await readExport(page)).events).toHaveLength(3);
});

test("invalid middle event replays longest valid prefix and exports untouched suffix", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  await page.getByLabel("L01-B", { exact: true }).click();
  const saved = await updateStoredMode(page, record => { record.events[2].shot_ids = ["UNKNOWN-SHOT"]; });
  await page.reload();
  await expect(page.getByTestId("complete-count")).toHaveText("0");
  await expect(page.locator('#storage-warning')).toContainText(/invalid|replay|prefix/i);
  expect((await readExport(page)).events).toEqual(saved.record.events);
});

test("stale hash state is discoverable and exportable but never applied", async ({ page }) => {
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  const old = await storedMode(page);
  const staleHash = "a".repeat(64);
  old.record.mode_plan_sha256 = staleHash;
  await page.evaluate(({ old, staleHash }) => {
    localStorage.removeItem(old.key);
    localStorage.setItem(old.key.replace(/[^/]+$/, staleHash), JSON.stringify(old.record));
  }, { old, staleHash });
  await page.reload();
  if (await page.locator('button[data-mode-id="lite-24"]').isVisible()) await chooseMode(page, "lite-24");
  await expect(page.getByTestId("complete-count")).toHaveText("0");
  await expect(page.locator('#stale-states')).toContainText(/older|stale|previous/i);
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: /export.*(older|stale|previous)/i }).click();
  const stream = await (await pending).createReadStream();
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  expect(JSON.parse(Buffer.concat(chunks).toString())).toEqual(old.record);
});

test("corrupt storage is quarantined without preventing a new capture", async ({ page }) => {
  await startMode(page);
  const saved = await storedMode(page);
  await page.evaluate(key => localStorage.setItem(key, "{not-json"), saved.key);
  await page.reload();
  await expect(page.locator('#storage-warning')).toContainText(/could not read|corrupt/i);
  expect(await page.evaluate(key => Object.keys(localStorage).some(item => item.startsWith(`${key}/corrupt/`) && localStorage.getItem(item) === "{not-json"), saved.key)).toBe(true);
});

for (const failure of ["unavailable", "writes fail", "quarantine fails"]) {
  test(`storage ${failure} warns and capture continues in memory`, async ({ page }) => {
    if (failure === "quarantine fails") {
      await startMode(page);
      const saved = await storedMode(page);
      await page.evaluate(key => localStorage.setItem(key, "{not-json"), saved.key);
    }
    await page.addInitScript(failure => {
      if (failure === "unavailable") Object.defineProperty(window, "localStorage", { get() { throw new DOMException("denied", "SecurityError"); } });
      else Storage.prototype.setItem = () => { throw new DOMException("full", "QuotaExceededError"); };
    }, failure);
    await page.goto("/index.html");
    if (await page.locator('button[data-mode-id="lite-24"]').isVisible()) await chooseMode(page, "lite-24");
    await confirmCurrent(page);
    await page.getByLabel("L01-A", { exact: true }).check();
    await expect(page.getByTestId("complete-count")).toHaveText("1");
    await expect(page.locator('#storage-warning')).toContainText(/refresh|closing|close/i);
    expect((await readExport(page)).completed_shot_ids).toEqual(["L01-A"]);
    if (failure === "quarantine fails") expect(await page.evaluate(prefix => Object.keys(localStorage).some(key => key.startsWith(prefix) && localStorage.getItem(key) === "{not-json"), KEY_PREFIX)).toBe(true);
  });
}

for (const delivery of ["clipboard", "execCommand", "manual"]) {
  test(`export fallback delivers exact JSON through ${delivery}`, async ({ page }) => {
    await page.addInitScript(delivery => {
      URL.createObjectURL = () => { throw new Error("blocked"); };
      Object.defineProperty(navigator, "clipboard", { configurable: true, value: delivery === "clipboard" ? { writeText: async text => { window.copiedProgress = text; } } : { writeText: async () => { throw new Error("denied"); } } });
      document.execCommand = command => { window.copyCommand = command; return delivery === "execCommand"; };
    }, delivery);
    await startMode(page);
    await page.locator("#export-progress").click();
    const area = page.getByRole("textbox", { name: /^Progress JSON/ });
    await expect(area).toBeVisible();
    await expect(area).toHaveAttribute("readonly", "");
    const json = await area.inputValue();
    expect(JSON.parse(json).mode_id).toBe("lite-24");
    await page.locator("#copy-export").click();
    if (delivery === "clipboard") expect(await page.evaluate(() => window.copiedProgress)).toBe(json);
    else expect(await page.evaluate(() => window.copyCommand)).toBe("copy");
    if (delivery === "manual") expect(await area.evaluate(node => [node.selectionStart, node.selectionEnd])).toEqual([0, json.length]);
  });
}

test("third mode completes, persists, and exports through the generic controller", async ({ page }) => {
  await startMode(page, "test-3", THIRD_URL);
  await confirmCurrent(page);
  await page.getByLabel("T-ONLY", { exact: true }).click();
  await expect(page.getByText("Checklist complete — verify the album", { exact: true })).toBeVisible();
  await page.reload();
  const data = await readExport(page);
  expect(data.mode_id).toBe("test-3");
  expect(data.completed_shot_ids).toEqual(["T-ONLY"]);
  expect(data.pending_shot_ids).toEqual([]);
});

for (const [modeId, count] of [["lite-24", 24], ["standard-48", 48]]) {
  test(`${modeId} full route reaches complete handoff with exact totals`, async ({ page }) => {
    await startMode(page, modeId);
    await completeRoute(page);
    await expect(page.getByText("Checklist complete — verify the album", { exact: true })).toBeVisible();
    const data = await readExport(page);
    expect(data.completed_shot_ids).toHaveLength(count);
    expect(data.pending_shot_ids).toEqual([]);
    expect(data.skipped_shot_ids).toEqual([]);
  });
}

test("skipping with a note ends in gaps rather than false completion", async ({ page }) => {
  await startMode(page, "test-3", THIRD_URL);
  await page.getByLabel("Note for T-ONLY", { exact: true }).fill("Blocked by a chair");
  await page.getByRole("button", { name: "Skip T-ONLY", exact: true }).click();
  await expect(page.getByText("Route reviewed with gaps", { exact: true })).toBeVisible();
  const data = await readExport(page);
  expect(data.skipped_shot_ids).toEqual(["T-ONLY"]);
  expect(data.events.at(-1)).toMatchObject({ type: "shot_skipped", note: "Blocked by a chair" });
});

test("static ledgers remain readable with JavaScript disabled", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:8765/index.html");
  for (const id of ["L01-A", "L14-A", "A01-L", "D08"]) await expect(page.locator('.static-guide').getByText(id, { exact: true })).toBeVisible();
  await context.close();
});

test("initialization failure preserves static instructions and displays warning", async ({ page }) => {
  await page.addInitScript(() => { window.__ASTRA_FORCE_INIT_ERROR__ = true; });
  await page.goto("/index.html");
  await expect(page.locator("html")).not.toHaveClass(/enhanced/);
  for (const id of ["L14-A", "D08"]) await expect(page.locator('.static-guide').getByText(id, { exact: true })).toBeVisible();
  await expect(page.locator('#enhancement-warning')).toContainText(/static|enhance|interactive/i);
});

test("direct file origin honestly warns about unverified persistence", async ({ page }) => {
  await page.goto(pathToFileURL(`${process.cwd()}/build/browser-simulation/capture-pack/index.html`).href);
  await expect(page.locator('#storage-warning')).toContainText(/persistence.*unverified|unverified.*persistence/i);
});

test("generated page has no runtime network dependencies or permission requests", async ({ page }) => {
  const requests = [];
  page.on("request", request => { if (request.resourceType() !== "document") requests.push(request.url()); });
  await page.addInitScript(() => {
    window.permissionRequests = [];
    if (navigator.geolocation) navigator.geolocation.getCurrentPosition = () => window.permissionRequests.push("geolocation");
    if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = () => { window.permissionRequests.push("camera"); return Promise.reject(new Error("blocked")); };
  });
  await startMode(page);
  await confirmCurrent(page);
  await page.getByLabel("L01-A", { exact: true }).check();
  expect(requests).toEqual([]);
  expect(await page.evaluate(() => window.permissionRequests)).toEqual([]);
  await expect(page.locator('[aria-live="polite"]').first()).toBeAttached();
});

for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }, { width: 320, height: 800 }]) {
  test(`responsive layout and visual baseline ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/index.html");
    await expect(page.locator("#mode-chooser")).toHaveScreenshot(`mode-choice-${viewport.width}.png`, { animations: "disabled" });
    await chooseMode(page, "lite-24");
    await confirmCurrent(page);
    await page.getByLabel("L01-A", { exact: true }).check();
    const widths = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
    expect(widths[0]).toBe(widths[1]);
    await expect(page.locator("#map-section")).toHaveScreenshot(`map-${viewport.width}.png`, { animations: "disabled" });
    await expect(page.locator("#task-view")).toHaveScreenshot(`current-task-${viewport.width}.png`, { animations: "disabled" });
  });
}

test("third-mode gap and completed handoff visual baselines", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await startMode(page, "test-3", THIRD_URL);
  await page.getByRole("button", { name: "Skip T-ONLY", exact: true }).click();
  const eventWindow = page.getByText(/^Operator event window:/);
  await expect(page.locator("#task-view")).toHaveScreenshot("gap-handoff-390.png", { mask: [eventWindow] });
  await page.locator("#undo-action").click();
  await confirmCurrent(page);
  await page.getByLabel("T-ONLY", { exact: true }).click();
  await expect(page.locator("#task-view")).toHaveScreenshot("complete-handoff-390.png", { mask: [eventWindow] });
});

for (const [modeId, count] of [["candidate-lite-32",32], ["candidate-standard-64",64]]) {
  test(`${modeId} actual production-gated draft completes and exports`, async ({ page }) => {
    await startMode(page, modeId, "http://127.0.0.1:8767/index.html");
    const data = await page.locator('#capture-data').evaluate(node => JSON.parse(node.textContent));
    expect(data.report.status).toBe('draft');
    expect(data.coverage.flatMap(mode => mode.issues).filter(issue => issue.severity === 'error')).toEqual([]);
    await completeRoute(page);
    await expect(page.getByText('Checklist complete — verify the album', {exact:true})).toBeVisible();
    const exported = await readExport(page);
    expect(exported.completed_shot_ids).toHaveLength(count);
    expect(exported.pending_shot_ids).toEqual([]);
    expect(exported.capture_id).toContain('candidate-02');
    expect(exported.coverage_review_status).toBe('missing');
    expect(exported.coverage_review_digest).toBeNull();
  });
}

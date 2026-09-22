/* Metadata-only capture workflow. Geometry is supplied by the Python preflight. */
(() => {
  "use strict";
  const groupsOf = mode => mode.passes.flatMap(pass => pass.groups);
  const shotsOf = mode => groupsOf(mode).flatMap(group => group.shots);
  const reversible = new Set(["shot_completed", "group_completed", "shot_skipped", "shot_reopened", "note_changed"]);
  const identityFields = ["room_id", "capture_id", "mode_id", "mode_plan_sha256"];
  const initialShots = mode => Object.fromEntries(shotsOf(mode).map(shot => [shot.id, {status: "pending", note: ""}]));
  const applyEvents = (mode, events, compensated) => {
    const shots = initialShots(mode);
    for (const event of events) {
      if (compensated.has(event.seq)) continue;
      for (const id of event.shot_ids || []) {
        if (event.type === "shot_completed" || event.type === "group_completed") shots[id].status = "completed";
        if (event.type === "shot_reopened") shots[id].status = "pending";
        if (event.type === "shot_skipped") shots[id].status = "skipped";
        if (event.type === "note_changed" || event.type === "shot_skipped") shots[id].note = event.note;
      }
    }
    return shots;
  };

  class EventReducer {
    static nextUndoTarget(events, compensated = new Set(events.filter(e => e.type === "undo").map(e => e.undoes_seq))) {
      return [...events].reverse().find(e => reversible.has(e.type) && !compensated.has(e.seq)) || null;
    }
    static replay(mode, rawEvents) {
      const valid = [], compensated = new Set();
      let warning = null;
      const raw = Array.isArray(rawEvents) ? rawEvents : [];
      if (!Array.isArray(rawEvents)) warning = "Event log must be an array.";
      for (const e of raw) {
        const fail = reason => { warning = `Invalid event at sequence ${valid.length + 1}: ${reason}. Raw history is retained for export. Export this log and reset the current mode before recording new actions.`; };
        if (!e || typeof e !== "object" || e.seq !== valid.length + 1 || !Number.isSafeInteger(e.t_ms) || e.t_ms < 0 || !Number.isInteger(e.tz_offset_min) || Math.abs(e.tz_offset_min) > 840) { fail("sequence or timestamp"); break; }
        if (identityFields.some(key => e[key] !== (key === "mode_id" ? mode.id : mode[key]))) { fail("identity mismatch"); break; }
        if (e.type === "capture_started") {
          if (valid.length !== 0) { fail("capture already started"); break; }
        } else if (!valid.length || valid[0].type !== "capture_started") { fail("missing capture start"); break; }
        else if (e.type === "undo") {
          const target = this.nextUndoTarget(valid, compensated);
          if (!target || target.seq !== e.undoes_seq) { fail("invalid undo target"); break; }
          compensated.add(target.seq);
        } else {
          const group = groupsOf(mode).find(g => g.id === e.group_id);
          if (!group || group.station_id !== e.station_id) { fail("unknown group or station"); break; }
          if (e.type === "station_confirmed") {
            if (e.method !== "manual_station") { fail("station method"); break; }
          } else {
            if (!reversible.has(e.type) || !Array.isArray(e.shot_ids) || !e.shot_ids.length || new Set(e.shot_ids).size !== e.shot_ids.length || e.shot_ids.some(id => !group.shots.some(s => s.id === id))) { fail("shot reference or event type"); break; }
            const isGroup = e.type === "group_completed";
            if (e.method !== (isGroup ? "group" : "shot") || (!isGroup && e.shot_ids.length !== 1) || (isGroup && e.within_group_order !== "inferred")) { fail("resolution method"); break; }
            if (["note_changed", "shot_skipped"].includes(e.type) && typeof e.note !== "string") { fail("note payload"); break; }
            const state = applyEvents(mode, valid, compensated);
            if (isGroup) {
              const pending = group.shots.filter(s => state[s.id].status === "pending").map(s => s.id);
              if (JSON.stringify(pending) !== JSON.stringify(e.shot_ids)) { fail("group resolution must contain all pending shots in plan order"); break; }
            } else {
              const before = state[e.shot_ids[0]];
              if ((e.type === "shot_completed" && before.status !== "pending") || (e.type === "shot_reopened" && before.status === "pending") || (e.type === "shot_skipped" && before.status === "skipped") || (e.type === "note_changed" && before.note === e.note)) { fail("no-op or invalid transition"); break; }
            }
          }
        }
        valid.push(e);
      }
      return {shots: applyEvents(mode, valid, compensated), valid_events: valid, raw_events: rawEvents, valid_prefix_length: valid.length, compensated_seqs: [...compensated], warning};
    }
  }

  class StateStore {
    constructor(identity, storage) {
      this.identity = identity; this.memory = new Map(); this.persistenceWarning = "";
      try { this.storage = storage === undefined ? window.localStorage : storage; if (!this.storage) throw new Error("Storage unavailable"); }
      catch (error) { this.fail(error); }
    }
    fail(error) { this.storage = null; this.persistenceWarning = `Saved progress unavailable: ${String(error)}. Refresh or closing this page can lose progress; export regularly.`; }
    prefix(mode) { return `astra.capture.v2/room:${this.identity.room_id}/capture:${this.identity.capture_id}/mode:${mode.id}/hash/`; }
    key(mode) { return this.prefix(mode) + mode.mode_plan_sha256; }
    pointerKey() { return `astra.capture.v2/room:${this.identity.room_id}/capture:${this.identity.capture_id}/last_active_mode`; }
    empty(mode) { return {schema_version: "2.0", ...this.identity, mode_id: mode.id, mode_plan_sha256: mode.mode_plan_sha256, last_group_id: null, events: []}; }
    load(mode) {
      if (this.memory.has(mode.id)) return this.memory.get(mode.id);
      let raw = null, record = this.empty(mode);
      try {
        raw = this.storage?.getItem(this.key(mode));
        if (raw !== null && raw !== undefined) {
          const value = JSON.parse(raw);
          if (!value || value.schema_version !== "2.0" || !Array.isArray(value.events) || identityFields.some(k => value[k] !== record[k])) throw new Error("invalid saved identity or schema");
          record = value;
        }
      } catch (error) {
        if (raw !== null) {
          try {
            this.storage.setItem(`${this.key(mode)}/corrupt/${Date.now()}`, raw);
            this.storage.removeItem(this.key(mode));
            this.persistenceWarning = "Could not read saved progress. Original data was quarantined for recovery; a clean route can be started.";
          } catch (quarantineError) { this.fail(`Could not read saved progress; original left untouched. ${quarantineError}`); }
        } else this.fail(error);
      }
      this.memory.set(mode.id, record); return record;
    }
    save(mode, events, lastGroupId) {
      const record = {...this.empty(mode), last_group_id: lastGroupId, events};
      this.memory.set(mode.id, record);
      try {
        this.storage?.setItem(this.key(mode), JSON.stringify(record));
        this.storage?.setItem(this.pointerKey(), JSON.stringify({...this.identity, mode_id: mode.id, mode_plan_sha256: mode.mode_plan_sha256, last_group_id: lastGroupId}));
      } catch (error) { this.fail(error); }
    }
    active() { try { return JSON.parse(this.storage?.getItem(this.pointerKey()) || "null"); } catch (error) { return null; } }
    findStale(mode) {
      const result = [];
      try {
        if (!this.storage) return result;
        for (let i = 0; i < this.storage.length; i++) {
          const key = this.storage.key(i);
          if (key.startsWith(this.prefix(mode)) && key !== this.key(mode)) {
            const raw = this.storage.getItem(key); let count = null;
            try { count = JSON.parse(raw)?.events?.length ?? null; } catch (_) { /* retain unreadable raw */ }
            result.push({key, mode_plan_sha256: key.slice(this.prefix(mode).length), event_count: count, raw});
          }
        }
      } catch (error) { this.fail(error); }
      return result.sort((a, b) => a.key.localeCompare(b.key));
    }
    reset(mode) {
      this.memory.set(mode.id, this.empty(mode));
      try { this.storage?.removeItem(this.key(mode)); const pointer = this.active(); if (pointer?.mode_id === mode.id) this.storage?.removeItem(this.pointerKey()); }
      catch (error) { this.fail(error); }
    }
  }

  class ProgressExport {
    static build(data, mode, replay) {
      const events = replay.raw_events;
      const times = replay.valid_events.map(e => e.t_ms);
      const ids = status => shotsOf(mode).filter(s => replay.shots[s.id].status === status).map(s => s.id);
      return {schema_version: "2.0", room_id: data.room_id, capture_id: data.capture_id, mode_id: mode.id, mode_plan_sha256: mode.mode_plan_sha256,
        coverage_review_status: data.report?.coverage_review_status?.[mode.id] || "missing", coverage_review_digest: data.report?.coverage_review_digests?.[mode.id] || null,
        events, valid_prefix_length: replay.valid_prefix_length, replay_warning: replay.warning,
        completed_shot_ids: ids("completed"), skipped_shot_ids: ids("skipped"), pending_shot_ids: ids("pending"),
        first_event_t_ms: times[0] ?? null, last_event_t_ms: times.at(-1) ?? null};
    }
    static canonicalJson(value) { return JSON.stringify(value, null, 2) + "\n"; }
    static async deliver(text, environment = window) {
      try {
        const url = environment.URL.createObjectURL(new environment.Blob([text], {type: "application/json"}));
        const link = document.createElement("a"); link.href = url; link.download = "capture-progress.json"; document.body.append(link); link.click(); link.remove();
        environment.setTimeout(() => environment.URL.revokeObjectURL(url), 1000); return "download";
      } catch (_) {
        document.getElementById("export-panel").hidden = false;
        const area = document.getElementById("export-text"); area.value = text; area.focus(); area.select(); return "manual";
      }
    }
    static async copyFallback(area) {
      area.focus(); area.select();
      if (window.isSecureContext && navigator.clipboard?.writeText) {
        try { await navigator.clipboard.writeText(area.value); return "clipboard"; } catch (_) { /* next path */ }
      }
      try { if (document.execCommand?.("copy")) return "execCommand"; } catch (_) { /* manual remains selected */ }
      area.focus(); area.select(); return "manual";
    }
  }

  const el = (tag, text, attrs = {}) => {
    const node = document.createElement(tag); if (text !== null) node.textContent = text;
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  const button = (text, action, disabled = false) => { const node = el("button", text, {type: "button"}); node.disabled = disabled; node.addEventListener("click", action); return node; };
  const passState = statuses => statuses.every(s => s === "completed") ? "completed" : statuses.every(s => s !== "pending") ? "gap" : statuses.some(s => s !== "pending") ? "in-progress" : "upcoming";

  class MapView {
    constructor(root, data, onStationSelected) {
      this.root = root; this.data = data;
      for (const node of document.querySelectorAll("#map-view [data-station-id], #station-list button[data-station-id]")) {
        node.addEventListener("click", () => onStationSelected(node.dataset.stationId));
        if (node.tagName.toLowerCase() === "g") {
          node.setAttribute("role", "button"); node.setAttribute("tabindex", "0");
          node.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onStationSelected(node.dataset.stationId); } });
        }
      }
    }
    render(mode, group, replay, currentShotId) {
      const modeGroups = groupsOf(mode), pass = mode.passes.find(p => p.groups.some(g => g.id === group?.id));
      for (const marker of document.querySelectorAll("#map-view [data-station-id], #station-list button[data-station-id]")) {
        const station = this.data.stations.find(s => s.id === marker.dataset.stationId);
        const used = modeGroups.filter(g => g.station_id === station.id).flatMap(g => g.shots);
        marker.style.display = used.length ? "" : "none";
        const passShots = (pass?.groups || []).filter(g => g.station_id === station.id).flatMap(g => g.shots);
        const state = group?.station_id === station.id ? "current" : passShots.length ? passState(passShots.map(s => replay.shots[s.id].status)) : "not-in-pass";
        const whole = used.length ? passState(used.map(s => replay.shots[s.id].status)) : "upcoming";
        marker.dataset.passState = state; marker.dataset.modeState = whole;
        marker.setAttribute("aria-label", `Station ${station.number} · ${state.replaceAll("-", " ")} · whole route ${whole.replaceAll("-", " ")}`);
        if (marker.tagName === "BUTTON") marker.textContent = `Station ${station.number} · ${state.replaceAll("-", " ")}`;
      }
      for (const path of document.querySelectorAll(".shot-ray[data-shot-id], .shot-cone[data-shot-id]")) {
        const id = path.dataset.shotId, inGroup = group?.shots.some(s => s.id === id);
        path.style.display = inGroup ? "" : "none";
        path.dataset.state = id === currentShotId ? "current" : replay.shots[id]?.status || "pending";
        path.classList.toggle("current", id === currentShotId);
        path.classList.toggle("completed", replay.shots[id]?.status === "completed");
      }
    }
  }

  class TaskView {
    constructor(root, handlers) { this.root = root; this.h = handlers; }
    render(mode, group, replay, confirmedStationId) {
      this.root.replaceChildren();
      const station = this.h.station(group.station_id), confirmed = confirmedStationId === group.station_id;
      const heading = el("h2", `Go to station ${station.number}`);
      heading.append(el("span", String(station.number), {"data-testid": "current-station", class: "visually-hidden"}));
      this.root.append(heading, el("p", station.label), el("p", `${group.id} · ${group.title}`), el("p", group.purpose));
      this.root.append(button(confirmed ? `At station ${station.number} — manually confirmed` : `I am at station ${station.number}`, () => this.h.confirmStation(station.id), confirmed));
      this.root.append(el("p", "Manual confirmation only; the guide does not detect your position or observe the camera."));
      for (const shot of group.shots) {
        const state = replay.shots[shot.id], card = el("article", null, {class: "shot-card"});
        const label = el("label", null), check = el("input", null, {type: "checkbox", "aria-label": shot.id, "data-shot-id": shot.id});
        check.checked = state.status === "completed"; check.disabled = state.status === "pending" && !confirmed;
        if (state.status === "skipped") check.disabled = true;
        check.addEventListener("change", () => this.h.setShotCompleted(group.id, shot.id, check.checked));
        label.append(check, document.createTextNode(`${shot.id} · ${state.status}`)); card.append(label);
        card.append(el("p", shot.instruction), el("p", `${shot.pitch} · ${shot.pitch_deg}° · ${shot.target_ids.join(", ")}`));
        const noteLabel = el("label", `Note / skip reason for ${shot.id}`), note = el("textarea", null, {"aria-label": `Note for ${shot.id}`, rows: "2"}); note.value = state.note; noteLabel.append(note); card.append(noteLabel);
        card.append(button("Save note", () => this.h.setNote(group.id, shot.id, note.value)));
        card.append(button(`Skip ${shot.id}`, () => this.h.skipShot(group.id, shot.id, note.value), state.status === "skipped"));
        if (state.status === "skipped") card.append(button(`Restore ${shot.id}`, () => this.h.setShotCompleted(group.id, shot.id, false)));
        this.root.append(card);
      }
      this.root.append(button("All photos taken — complete group", () => this.h.completeGroup(group.id), !confirmed || !group.shots.some(s => replay.shots[s.id].status === "pending")));
      this.root.append(button("Next incomplete", () => this.h.nextIncomplete()));
      if (group.next_hint) this.root.append(el("p", group.next_hint));
    }
    renderCompletion(mode, replay) {
      this.root.replaceChildren();
      const missing = shotsOf(mode).filter(s => replay.shots[s.id].status !== "completed").map(s => s.id);
      this.root.append(el("h2", missing.length ? "Route reviewed with gaps" : "Checklist complete — verify the album"));
      if (missing.length) this.root.append(el("p", `Missing planned photos: ${missing.join(", ")}`));
      this.root.append(el("p", `Expected at least ${mode.expected_image_count} planned originals for a complete route. Keep extra retakes. These checks do not verify photo existence.`));
      const times = replay.valid_events.map(e => new Date(e.t_ms).toISOString());
      this.root.append(el("p", `Operator event window: ${times[0] || "—"} to ${times.at(-1) || "—"}. Action times are advisory; group photo order is inferred, not observed shutter timing.`));
      this.root.append(el("p", "Upload all untouched original Xiaomi JPG files as one folder or ZIP with the exported progress JSON. Do not rename, edit, recompress, or transfer through messaging apps. Mention moved stations and untracked retakes."));
    }
  }

  class CaptureController {
    constructor(data, store, clock = Date) {
      this.data = data; this.store = store; this.clock = clock; this.mode = null; this.group = null; this.events = []; this.confirmedStationId = null;
      for (const mode of data.modes) {
        mode.room_id = data.room_id; mode.capture_id = data.capture_id;
        mode.mode_plan_sha256 ||= data.coverage.find(c => c.mode_id === mode.id)?.mode_plan_sha256;
      }
    }
    init() {
      const mapSection = document.getElementById("map-section");
      if (mapSection) document.getElementById("workflow").insertBefore(mapSection, document.getElementById("task-view"));
      this.map = new MapView(document.getElementById("interactive-guide"), this.data, id => this.selectStation(id));
      this.task = new TaskView(document.getElementById("task-view"), this);
      document.querySelectorAll("[data-mode-id]").forEach(node => { if (node.tagName === "BUTTON") node.addEventListener("click", () => this.chooseMode(node.dataset.modeId)); });
      const bind = (id, action) => document.getElementById(id)?.addEventListener("click", action);
      bind("undo-action", () => this.undoLastAction()); bind("export-progress", () => this.exportProgress());
      bind("reset-mode", () => { if (this.mode && window.confirm("Reset current mode? Export first if you need this history.")) this.resetCurrentMode(); });
      bind("change-mode", () => this.showChooser());
      bind("toggle-diagnostics", () => { const enabled = document.documentElement.classList.toggle("show-diagnostics"); document.getElementById("toggle-diagnostics").setAttribute("aria-pressed", String(enabled)); });
      bind("select-export", () => { const area = document.getElementById("export-text"); area.focus(); area.select(); });
      bind("copy-export", async () => { const result = await ProgressExport.copyFallback(document.getElementById("export-text")); document.getElementById("export-message").textContent = result === "manual" ? "Press Copy in your browser or keyboard to copy the selected JSON." : "Progress JSON copied."; });
      if (!document.getElementById("export-message")) document.getElementById("export-panel").append(el("p", "", {id: "export-message", role: "status"}));
      for (const mode of this.data.modes) this.store.load(mode);
      const pointer = this.store.active(), mode = this.data.modes.find(m => m.id === pointer?.mode_id && m.mode_plan_sha256 === pointer?.mode_plan_sha256);
      if (mode && pointer.room_id === this.data.room_id && pointer.capture_id === this.data.capture_id && this.store.load(mode).events.length) this.activate(mode);
      else this.showChooser();
      this.warnings();
    }
    station(id) { return this.data.stations.find(s => s.id === id); }
    resetCurrentMode() {
      const id = this.mode.id;
      this.store.reset(this.mode);
      this.mode = null; this.group = null; this.events = []; this.replay = null; this.confirmedStationId = null;
      document.getElementById("task-view").replaceChildren();
      document.getElementById("export-panel").hidden = true;
      this.showChooser(); this.chooseMode(id);
    }
    showChooser() {
      this.confirmedStationId = null; document.getElementById("mode-chooser").hidden = false; document.getElementById("workflow").hidden = true;
      document.getElementById("capture-preflight")?.remove();
      for (const b of document.querySelectorAll("#mode-chooser button[data-mode-id]")) {
        const mode = this.data.modes.find(m => m.id === b.dataset.modeId); if (!mode) continue;
        const replay = EventReducer.replay(mode, this.store.load(mode).events), count = Object.values(replay.shots).filter(s => s.status === "completed").length;
        b.textContent = `${mode.id} · ${mode.title} · ${count}/${mode.expected_image_count}${replay.valid_events.length ? " · Resume" : ""}`;
      }
      this.warnings();
    }
    chooseMode(id) {
      const mode = this.data.modes.find(m => m.id === id); if (!mode) return;
      if (this.store.load(mode).events.length) { this.activate(mode); return; }
      this.confirmedStationId = null;
      document.getElementById("capture-preflight")?.remove();
      const card = el("section", null, {id: "capture-preflight"});
      card.append(el("h2", `${mode.title} · camera setup`), el("p", "1× 23 mm main camera · landscape 4:3 JPG · unchanged Leica style. Turn watermark, filters, AI scene, HDR, flash, digital zoom and Dynamic Shot off. Keep lighting/curtains stable; both doors closed. If doors change, restart with a new capture ID."));
      const label = el("label", null), check = el("input", null, {type: "checkbox", id: "camera-ack"}); label.append(check, document.createTextNode("I checked the Xiaomi settings")); card.append(label);
      const start = button("Start route", () => this.startMode(id), true); check.addEventListener("change", () => { start.disabled = !check.checked; }); card.append(start);
      document.getElementById("mode-chooser").append(card);
    }
    startMode(id) { if (!document.getElementById("camera-ack")?.checked) return; const mode = this.data.modes.find(m => m.id === id); if (mode) this.activate(mode, true); }
    activate(mode, start = false) {
      this.mode = mode; this.confirmedStationId = null;
      const record = this.store.load(mode); this.events = [...record.events]; this.replay = EventReducer.replay(mode, this.events);
      const groups = groupsOf(mode);
      this.group = groups.find(g => g.id === record.last_group_id) || groups.find(g => g.shots.some(s => this.replay.shots[s.id].status === "pending")) || null;
      if (start && !this.events.length) this.append("capture_started", {}, false);
      document.getElementById("mode-chooser").hidden = true; document.getElementById("workflow").hidden = false;
      document.getElementById("capture-preflight")?.remove(); this.save(); this.render();
    }
    append(type, payload, redraw = true) {
      if (this.replay.warning) { this.warnings(); return false; }
      const event = {seq: this.events.length + 1, t_ms: this.clock.now(), tz_offset_min: -new this.clock().getTimezoneOffset(), type,
        room_id: this.data.room_id, capture_id: this.data.capture_id, mode_id: this.mode.id, mode_plan_sha256: this.mode.mode_plan_sha256, ...payload};
      const candidate = [...this.events, event], replay = EventReducer.replay(this.mode, candidate);
      if (replay.warning) throw new Error(replay.warning);
      this.events = candidate; this.replay = replay; this.save(); if (redraw) this.render(); return true;
    }
    save() { if (this.mode) this.store.save(this.mode, this.events, this.group?.id || null); }
    payload(group, shotIds, method = "shot") { return {group_id: group.id, station_id: group.station_id, shot_ids: shotIds, method}; }
    confirmStation(id) {
      if (!this.group || id !== this.group.station_id || this.confirmedStationId === id) return;
      if (this.append("station_confirmed", {group_id: this.group.id, station_id: id, method: "manual_station"}, false)) { this.confirmedStationId = id; this.render(); }
    }
    setShotCompleted(groupId, shotId, completed) {
      const group = groupsOf(this.mode).find(g => g.id === groupId); if (!group || !group.shots.some(s => s.id === shotId)) return;
      const state = this.replay.shots[shotId];
      if (completed && (state.status !== "pending" || this.group?.id !== groupId || this.confirmedStationId !== group.station_id)) return;
      if (!completed && state.status === "pending") return;
      if (this.append(completed ? "shot_completed" : "shot_reopened", this.payload(group, [shotId]), false)) this.afterResolution(group, completed);
    }
    completeGroup(groupId) {
      const group = this.group; if (!group || group.id !== groupId || this.confirmedStationId !== group.station_id) return;
      const ids = group.shots.filter(s => this.replay.shots[s.id].status === "pending").map(s => s.id); if (!ids.length) return;
      if (this.append("group_completed", {...this.payload(group, ids, "group"), within_group_order: "inferred"}, false)) this.afterResolution(group, true);
    }
    skipShot(groupId, id, note = "") {
      const group = groupsOf(this.mode).find(g => g.id === groupId); if (!group?.shots.some(s => s.id === id) || this.replay.shots[id].status === "skipped") return;
      if (this.append("shot_skipped", {...this.payload(group, [id]), note}, false)) this.afterResolution(group, true);
    }
    setNote(groupId, id, note) {
      const group = groupsOf(this.mode).find(g => g.id === groupId); if (!group?.shots.some(s => s.id === id) || this.replay.shots[id].note === note) return;
      this.append("note_changed", {...this.payload(group, [id]), note});
    }
    afterResolution(group, advance) {
      if (advance && !group.shots.some(s => this.replay.shots[s.id].status === "pending")) this.nextIncomplete();
      else { this.moveTo(group); this.render(); }
    }
    moveTo(group) { if (group?.station_id !== this.group?.station_id) this.confirmedStationId = null; this.group = group; this.save(); }
    nextIncomplete() {
      const groups = groupsOf(this.mode), index = groups.findIndex(g => g.id === this.group?.id); let next = null;
      for (let offset = 1; offset <= groups.length; offset++) { const group = groups[(index + offset) % groups.length]; if (group.shots.some(s => this.replay.shots[s.id].status === "pending")) { next = group; break; } }
      this.moveTo(next); this.render();
    }
    selectStation(id) {
      if (!this.mode) return;
      const groups = groupsOf(this.mode).filter(g => g.station_id === id); if (!groups.length) return;
      this.moveTo(groups.find(g => g.shots.some(s => this.replay.shots[s.id].status === "pending")) || groups.at(-1)); this.render();
    }
    undoLastAction() {
      if (!this.mode) return; const target = EventReducer.nextUndoTarget(this.replay.valid_events); if (!target) return;
      if (this.append("undo", {undoes_seq: target.seq}, false)) { this.moveTo(groupsOf(this.mode).find(g => g.id === target.group_id)); this.render(); }
    }
    async exportProgress() { if (this.mode) await ProgressExport.deliver(ProgressExport.canonicalJson(ProgressExport.build(this.data, this.mode, this.replay))); }
    warnings() {
      const messages = [this.store.persistenceWarning, this.replay?.warning].filter(Boolean);
      if (!["http:", "https:"].includes(location.protocol) || /MiuiBrowser|MicroMessenger|; wv\)/i.test(navigator.userAgent)) messages.push("This origin/browser has unverified persistence and downloads. Use current Chrome over a stable HTTP(S) URL; export before leaving.");
      document.getElementById("storage-warning").textContent = messages.join(" ");
      const staleRoot = document.getElementById("stale-states"); staleRoot.replaceChildren();
      for (const mode of this.data.modes) for (const item of this.store.findStale(mode)) {
        const card = el("div", null); card.append(el("p", `Older / quarantined ${mode.id} progress: ${item.event_count ?? "unknown"} events. Not applied to this route.`));
        card.append(button("Export older raw progress", () => ProgressExport.deliver(item.raw))); staleRoot.append(card);
      }
    }
    render() {
      const count = status => Object.values(this.replay.shots).filter(s => s.status === status).length;
      const progress = document.getElementById("progress-status"); progress.replaceChildren(el("span", String(count("completed")), {"data-testid": "complete-count"}), document.createTextNode(` / ${this.mode.expected_image_count} complete · ${count("skipped")} skipped · ${this.mode.title}`));
      const currentShot = this.group?.shots.find(s => this.replay.shots[s.id].status === "pending")?.id;
      this.map.render(this.mode, this.group, this.replay, currentShot);
      if (this.group) this.task.render(this.mode, this.group, this.replay, this.confirmedStationId); else this.task.renderCompletion(this.mode, this.replay);
      if (this.replay.warning) {
        for (const control of document.querySelectorAll("#task-view input, #task-view textarea, #task-view button")) control.disabled = true;
      }
      document.getElementById("undo-action").disabled = !EventReducer.nextUndoTarget(this.replay.valid_events) || !!this.replay.warning;
      this.warnings();
    }
  }

  // The same pure reducer is available to the offline Node regression suite.
  if (typeof module !== "undefined" && module.exports) module.exports = {EventReducer, StateStore, ProgressExport};
  if (typeof window !== "undefined") {
    window.addEventListener("DOMContentLoaded", () => {
      try {
        if (window.__ASTRA_FORCE_INIT_ERROR__) throw new Error("forced initialization failure");
        const data = JSON.parse(document.getElementById("capture-data").textContent);
        const controller = new CaptureController(data, new StateStore({room_id: data.room_id, capture_id: data.capture_id}));
        controller.init();
        document.querySelectorAll("details.static-guide").forEach(node => { node.open = false; });
        document.documentElement.classList.add("enhanced");
      } catch (error) {
        const map = document.getElementById("map-section"), interactive = document.getElementById("interactive-guide");
        if (map && interactive?.parentNode) interactive.parentNode.insertBefore(map, interactive);
        document.getElementById("enhancement-warning").textContent = `Interactive controls unavailable; use the complete static guide below. ${String(error)}`;
      }
    });
  }
})();

# Native Notebook Correspondence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the PDF round trip with one four-page native Ferrari notebook whose incoming and reciprocal letters stream into a fixed vertical grid around an untouched native-ink huipi and a reversible marked copy.

**Architecture:** Xochitl creates and owns the notebook, templates, pages, ink, stock toolbar, and gestures. A USB-bound Mac bridge owns durable session state and one two-turn Codex review task; QML polls only bounded render state and draws non-interactive letter/review layers. No code writes Xochitl's private document files or imports a replacement PDF.

**Tech Stack:** Python 3.12, `unittest`, Codex app-server JSON-RPC, Xochitl QML 3.28.0.162, QMLDiff `25681c3`, Xovi/QRR, native declarative `.template` JSON, macOS LaunchAgents.

## Global Constraints

- Ferrari is exactly model `Ferrari`, OS `3.28.0.162`, native portrait `954×1696`.
- Chiappa remains a separate unimplemented exact-resource target.
- One letter page has 10 columns × 18 rows = 180 glyph cells; provider target is 150–168 characters and fitted output must be at least 144 cells.
- Publish only complete sentences ending in `。`, `！`, or `？`; never cut through a sentence or silently lose a glyph.
- Page 1 is incoming text, page 2 is native participant ink, page 3 is a duplicate plus reversible review, and page 4 is the streamed reciprocal letter in the same document ID.
- Never add pointer, pen, tap, swipe, pull-down, close, or replacement-toolbar handlers.
- Never write `.rm`, `.content`, `.metadata`, or any live Xochitl document-store file.
- Page 2 is immutable after submit; only its stock duplicate receives page-3 display marginalia.
- Only grounded, high-confidence, single-glyph corrections are red; uncertain readings remain neutral; no scores or grades.
- Required tests use fixtures. Live Codex, tablet SSH, template install, QML mutation, Xovi restart, and WHOOP remain human-approved lanes.
- Do not log or commit participant ink, provider payloads, conversation text, biometric samples, secret values, or the supplied hardware photograph.
- Preserve unrelated user changes. The current unstaged PDF-start USB retry in `mac_bridge/service.py` and `tests/test_native_codex_bridge.py` is superseded in Task 4 and must not be committed separately.

---

## File map

**Create**

- `contracts/native-notebook-api.ferrari-3.28.0.162.json` — exact resource and symbol hashes required by the Ferrari native path.
- `mac_bridge/letter_grid.py` — 180-cell vertical placement and stable complete-sentence streaming.
- `mac_bridge/notebook_session.py` — durable app-private notebook session state and phase transitions.
- `mac_bridge/notebook_service.py` — asynchronous start/bind/submit orchestration without PDF import.
- `mac_bridge/launch_agent.py` — deterministic sanitized LaunchAgent rendering and bidirectional health.
- `toolbar_launcher/templates/letters-home-ferrari.template` — app-owned 10×18 native notebook background in the exact format used by the 3.28 Ferrari backup.
- `mac_bridge/launchd/com.erniesg.letters-home.bridge.plist` — generated fixture used by installer tests.
- `scripts/install-letters-home-bridge` and `scripts/uninstall-letters-home-bridge` — reversible per-user Mac service control.
- `tests/test_letter_grid.py`, `tests/test_notebook_session.py`, `tests/test_notebook_service.py`, and `tests/test_bridge_launch_agent.py` — focused contracts.

**Modify**

- `mac_bridge/contracts.py` — notebook-review schema and 180-cell letter boundary.
- `mac_bridge/codex_app_server.py` — one persisted review task with structured-review and streamed-response turns.
- `mac_bridge/server.py` — notebook start, bind, submit, state, and health routes.
- `mac_bridge/service.py` — remove the active PDF start/submit wiring while retaining compatibility exports needed by historical tests.
- `mac_bridge/trial_bundle.py` — package QMDs and app-owned template assets with exact hashes.
- `toolbar_launcher/qmldiff/20-letters-home-launch.qmd` — start a session and create/bind a native notebook.
- `toolbar_launcher/qmldiff/30-letters-home-submit.qmd` — fixed-grid overlays, stock submit action, page duplication/add, review polling, and guarded page-4 advance.
- `toolbar_launcher/launcher.py` — host fixture mirrors of the exact QMLDiff behavior.
- `tests/test_native_codex_bridge.py`, `tests/test_native_document_launcher.py`, `tests/test_toolbar_launcher.py`, and `tests/test_device_installer.py` — replace PDF assertions with notebook contracts.
- `docs/product-brief.md`, `docs/architecture.md`, `docs/issues/010-native-codex-roundtrip.md`, `docs/mac-bridge.md`, and `docs/paper-pro-hardware-trial.md` — record the landed notebook behavior and exact operator gates.

---

### Task 1: Pin the native Ferrari API boundary

**Files:**

- Create: `contracts/native-notebook-api.ferrari-3.28.0.162.json`
- Modify: `tests/test_native_document_launcher.py`
- Modify: `mac_bridge/trial_bundle.py`

**Interfaces:**

- Consumes: saved Ferrari hashtab SHA `ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd`.
- Produces: `load_native_api_contract(target_name: str) -> Mapping[str, object]`; later QML tasks rely on these exact IDs and hashes.

- [ ] **Step 1: Write the failing exact-contract test**

```python
def test_ferrari_native_notebook_api_contract_pins_required_resources_and_symbols(self):
    contract = json.loads(
        (ROOT / "contracts/native-notebook-api.ferrari-3.28.0.162.json").read_text()
    )
    self.assertEqual(contract["os_version"], "3.28.0.162")
    self.assertEqual(contract["hashtab_sha256"], TARGETS["ferrari"].hashtab_sha256)
    self.assertEqual(
        contract["resources"],
        {
            "sidebar": "[[4911547370760691430]]",
            "document_view": "[[1224665461898798997]]",
            "create_notebook": "[[8651031636888757197]]",
            "create_notebook_window": "[[16344100773210839301]]",
            "pages": "[[4530443761526121003]]",
            "pages_actions": "[[11797611520953530268]]",
        },
    )
    self.assertEqual(contract["symbols"]["LibraryController.createDocument"], "[[16080285492618834883]]")
    self.assertEqual(contract["symbols"]["DocumentController.addPageWithTemplateAndPageSize"], "[[14285801537390842371]]")
    self.assertEqual(contract["symbols"]["DocumentController.setTemplateForPage"], "[[7540657167845513638]]")
    self.assertEqual(contract["symbols"]["createNotebookFromExistingPages"], "[[5450413349604854157]]")
```

- [ ] **Step 2: Run the test and verify the missing contract fails**

Run: `python3 -m unittest tests.test_native_document_launcher.NativeLauncherContractTests.test_ferrari_native_notebook_api_contract_pins_required_resources_and_symbols`

Expected: FAIL because `contracts/native-notebook-api.ferrari-3.28.0.162.json` does not exist.

- [ ] **Step 3: Add the exact contract and loader**

Create the JSON with the five resource IDs above and these additional symbol hashes recovered from the pinned table:

```json
{
  "hashtab_sha256": "ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd",
  "os_version": "3.28.0.162",
  "resources": {
    "create_notebook": "[[8651031636888757197]]",
    "create_notebook_window": "[[16344100773210839301]]",
    "document_view": "[[1224665461898798997]]",
    "pages": "[[4530443761526121003]]",
    "sidebar": "[[4911547370760691430]]"
  },
  "symbols": {
    "DocumentController.addPageWithTemplateAndPageSize": "[[14285801537390842371]]",
    "DocumentController.copyPages": "[[12188519148798835813]]",
    "DocumentController.setTemplateForPage": "[[7540657167845513638]]",
    "LibraryController.createDocument": "[[16080285492618834883]]",
    "createNotebook": "[[11689254259907176254]]",
    "createNotebookFromExistingPages": "[[5450413349604854157]]",
    "currentFolderId": "[[1536661485978992373]]",
    "documentName": "[[15793094956877606249]]",
    "document.idForPage": "[[532004573879022759]]",
    "NavigationManager.activeContext.explorer.currentFolderId": "[[7073776824345929404]]",
    "onNotebookClicked": "[[15540280890624773142]]",
    "root.createNotebook": "[[13558404569428295472]]"
  },
  "target": "ferrari"
}
```

Add a private loader in `mac_bridge/trial_bundle.py` that rejects a missing key, wrong target, wrong OS, or wrong saved hashtab hash with `TrialBundleError("native_notebook_api_unverified")`.

- [ ] **Step 4: Prove the saved table contains every pinned entry**

Run:

```bash
test "$(shasum -a 256 /private/tmp/ferrari-3.28.0.162.hashtab | awk '{print $1}')" = "ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd"
/private/tmp/qmldiff-25681c3/target/release/qmldiff dump-hashtab /private/tmp/ferrari-3.28.0.162.hashtab > /tmp/ferrari-3.28.0.162.hashtab.txt
rg '(/qt/qml/xofm/modules/library/ui/qml/CreateNotebook.qml|/qt/qml/xofm/modules/library/ui/qml/CreateNotebookWindow.qml|/qml/device/view/documentview/Pages.qml|/qml/device/view/documentview/DocumentView.qml|/qml/device/view/navigator/Sidebar.qml)' /tmp/ferrari-3.28.0.162.hashtab.txt
```

Expected: exact paths resolve to the resource IDs in the contract. If any entry differs, stop before QML implementation.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m unittest tests.test_native_document_launcher`

Expected: PASS.

```bash
git add contracts/native-notebook-api.ferrari-3.28.0.162.json mac_bridge/trial_bundle.py tests/test_native_document_launcher.py
git commit -m "test: pin Ferrari native notebook APIs"
```

---

### Task 2: Implement the 10×18 glyph grid and stable sentence stream

**Files:**

- Create: `mac_bridge/letter_grid.py`
- Create: `tests/test_letter_grid.py`
- Modify: `mac_bridge/contracts.py`
- Modify: `mac_bridge/codex_app_server.py`

**Interfaces:**

- Produces: `GridSpec`, `GlyphPlacement`, `place_vertical(text, spec)`, and `SentenceStream.append(delta) -> str`.
- Consumers: Task 3 session state and Task 7 QML render model.

- [ ] **Step 1: Write failing grid and photographed-fixture tests**

```python
PHOTO_TEXT = "家中寄来的话都收到了，隔着海与城，读来像灯下有人轻声叮嘱。你们汇来的钱已到账，我先缴了本学期学费，余下留作房租和药费，账目记得清楚，请别再省自己的饭菜。父亲的咳嗽要按时复诊，母亲也莫总说不累；我每天走路，睡得尚安，功课虽紧，成绩没有落下。等课程结束，我便带着书和给家里的小礼物回去。到时换我料理窗前的花、陪你们看诊，也把这些年欠下的团圆，一顿顿补回来。"

def test_photographed_176_character_letter_places_every_glyph_once():
    placements = place_vertical(PHOTO_TEXT, FERRARI_GRID)
    assert len(placements) == len(PHOTO_TEXT) == 176
    assert "".join(item.glyph for item in placements) == PHOTO_TEXT
    assert all(0 <= item.x < 954 and 0 <= item.y < 1696 for item in placements)
    assert placements[-7].glyph == "一"
    assert placements[-1].glyph == "。"

def test_stream_publishes_only_complete_sentences_that_fit():
    stream = SentenceStream(FERRARI_GRID, minimum=12)
    assert stream.append("家中安好，勿") == ""
    assert stream.append("念。功课顺利") == "家中安好，勿念。"
    assert stream.append("。") == "家中安好，勿念。功课顺利。"
```

- [ ] **Step 2: Run tests and verify missing imports fail**

Run: `python3 -m unittest tests.test_letter_grid`

Expected: ERROR importing `mac_bridge.letter_grid`.

- [ ] **Step 3: Implement the minimal grid types and fitter**

```python
from dataclasses import dataclass

TERMINATORS = frozenset("。！？")
ATTACHED_PUNCTUATION = frozenset("，。、；：！？）】》”’")

@dataclass(frozen=True)
class GridSpec:
    width: int = 954
    height: int = 1696
    columns: int = 10
    rows: int = 18
    left: float = 72
    top: float = 104
    right: float = 882
    bottom: float = 1592

    @property
    def capacity(self) -> int:
        return self.columns * self.rows

@dataclass(frozen=True)
class GlyphPlacement:
    glyph: str
    index: int
    column: int
    row: int
    x: float
    y: float
    punctuation: bool

FERRARI_GRID = GridSpec()

def place_vertical(text: str, spec: GridSpec = FERRARI_GRID) -> tuple[GlyphPlacement, ...]:
    if len(text) > spec.capacity:
        raise ValueError("letter_grid_overflow")
    cell_width = (spec.right - spec.left) / spec.columns
    cell_height = (spec.bottom - spec.top) / spec.rows
    result = []
    for index, glyph in enumerate(text):
        column, row = divmod(index, spec.rows)
        x = spec.right - (column + 0.5) * cell_width
        y = spec.top + (row + 0.5) * cell_height
        if glyph in ATTACHED_PUNCTUATION:
            x += cell_width * 0.18
            y -= cell_height * 0.18
        result.append(GlyphPlacement(glyph, index, column, row, x, y, glyph in ATTACHED_PUNCTUATION))
    return tuple(result)
```

Implement `SentenceStream` with separate raw and published buffers. Scan only newly completed sentences; append a sentence only when `place_vertical(candidate)` succeeds. Refuse finalization below its configured minimum and never publish an incomplete tail.

- [ ] **Step 4: Add boundary and punctuation tests, then implement kinsoku without reflow**

Add tests proving a closing mark cannot become the first visible item in a new column and that the earlier published prefix never changes. Implement look-ahead within each unpublished complete sentence: when a closing mark would occupy row 0, reserve the previous column's final cell and place the preceding glyph plus mark at rows 0 and 1 of the next column. Count the reserved cell against the 180-cell capacity.

- [ ] **Step 5: Align contracts and prompt**

Set `MAX_LETTER = 180`, add `MIN_NOTEBOOK_LETTER = 144`, and change the incoming prompt to `Use 150 to 168 Chinese characters; never exceed 180 including punctuation.` Keep final validation in `parse_letter_text`.

- [ ] **Step 6: Run focused and broad tests, then commit**

Run:

```bash
python3 -m unittest tests.test_letter_grid tests.test_native_codex_bridge
python3 -m unittest discover -s tests
```

Expected: all required tests PASS; only existing explicit skips remain.

```bash
git add mac_bridge/letter_grid.py mac_bridge/contracts.py mac_bridge/codex_app_server.py tests/test_letter_grid.py tests/test_native_codex_bridge.py
git commit -m "feat: bound streamed letters to the Ferrari grid"
```

---

### Task 3: Add durable notebook session state

**Files:**

- Create: `mac_bridge/notebook_session.py`
- Create: `tests/test_notebook_session.py`
- Modify: `mac_bridge/__init__.py`

**Interfaces:**

- Consumes: `SentenceStream` and `place_vertical` from Task 2.
- Produces: `NotebookSessionStore.begin`, `bind`, `mark_first_ink`, `append_incoming`, `finish_incoming`, `begin_review`, `finish_review`, `append_response`, `finish_response`, `fail`, `public_state`, and `expire`.

- [ ] **Step 1: Write failing phase, persistence, and privacy tests**

```python
def test_one_session_binds_one_native_notebook_and_survives_restart(tmp_path):
    path = tmp_path / "notebook-sessions.json"
    first = NotebookSessionStore(path)
    session_id = first.begin("private context")
    first.bind(session_id, document_id="doc-1", incoming_page_id="p1", reply_page_id="p2")
    first.append_incoming(session_id, "家中安好，勿念。")
    recovered = NotebookSessionStore(path)
    public = recovered.public_state(session_id)
    assert public["document_id"] == "doc-1"
    assert public["page_ids"] == {"incoming": "p1", "reply": "p2"}
    assert "private context" not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600

def test_review_and_response_phase_transitions_are_idempotent(tmp_path):
    store = bound_ready_store(tmp_path)
    assert store.begin_review("s1", marked_page_id="p3", response_page_id="p4")["phase"] == "reviewing"
    assert store.begin_review("s1", marked_page_id="p3", response_page_id="p4")["phase"] == "reviewing"
```

- [ ] **Step 2: Run tests and verify the missing store fails**

Run: `python3 -m unittest tests.test_notebook_session`

Expected: ERROR importing `NotebookSessionStore`.

- [ ] **Step 3: Implement the explicit phase model**

Use these exact public phases:

```python
PHASES = {
    "incoming", "ready", "reviewing", "review-ready",
    "response-streaming", "complete", "failed",
}
```

Persist only pseudonymous IDs, document/page IDs, fitted texts, bounded review geometry, safe error codes, timestamps, expiry, and Codex thread/turn IDs. Keep conversation context in memory only. Every mutator takes the store lock, increments `version` exactly once when public render state changes, writes through a mode-0600 temporary file, `fsync`s, and atomically replaces the state file.

`mark_first_ink(session_id, observed_at)` sets `first_ink_at` exactly once while
the session is bound and page 2 is active. Review submit sets `submitted_at` and
closes the capture-window state atomically even when consent is declined or the
source is unavailable.

- [ ] **Step 4: Implement public render state and recovery**

`public_state` must return JSON-safe values and precomputed glyph placements for incoming/response pages:

```python
{
    "session_id": session_id,
    "phase": state.phase,
    "version": state.version,
    "document_id": state.document_id,
    "page_ids": dict(state.page_ids),
    "incoming": {"text": state.incoming.text, "glyphs": glyph_dicts(state.incoming.text)},
    "review": state.review_public,
    "response": {"text": state.response.text, "glyphs": glyph_dicts(state.response.text)},
    "error": state.error,
}
```

On restart, an active `thread_id` plus `active_turn_id` remains recoverable; do not create a second task. `expire(now)` deletes every expired session and its private render directory.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m unittest tests.test_notebook_session tests.test_letter_grid`

Expected: PASS.

```bash
git add mac_bridge/notebook_session.py mac_bridge/__init__.py tests/test_notebook_session.py
git commit -m "feat: persist native notebook session state"
```

---

### Task 4: Replace synchronous PDF orchestration with asynchronous notebook APIs

**Files:**

- Create: `mac_bridge/notebook_service.py`
- Create: `tests/test_notebook_service.py`
- Modify: `mac_bridge/server.py`
- Modify: `mac_bridge/service.py`
- Modify: `tests/test_native_codex_bridge.py`

**Interfaces:**

- Consumes: `NotebookSessionStore` from Task 3, existing `RemarkableUsbDocuments.export_pdf`, and renderer `render_reply_page`.
- Produces: `NotebookCoordinator.start`, `bind`, `mark_first_ink`, `submit`, and `state`; HTTP routes keep `/v1/sessions/start`, `/v1/sessions/bind`, `/v1/sessions/ink-start`, `/v1/sessions/submit`, and `/v1/sessions/<id>`.

- [ ] **Step 1: Write failing start/bind tests proving no PDF upload**

```python
def test_start_returns_session_without_uploading_a_pdf(tmp_path):
    tablet = FakeTabletDocuments()
    coordinator = coordinator_fixture(tmp_path, tablet=tablet)
    response = coordinator.start({"profile_id": "ferrari_3.28.0.162"})
    assert response == {"status": "incoming", "session_id": response["session_id"]}
    assert tablet.upload_calls == []

def test_bind_records_the_stock_created_notebook_pages(tmp_path):
    coordinator = coordinator_fixture(tmp_path)
    session_id = coordinator.start({"profile_id": "ferrari_3.28.0.162"})["session_id"]
    result = coordinator.bind({
        "session_id": session_id, "document_id": "doc-1",
        "incoming_page_id": "p1", "reply_page_id": "p2",
    })
    assert result["status"] == "bound"
```

- [ ] **Step 2: Run tests and verify they fail on the old PDF starter**

Run: `python3 -m unittest tests.test_notebook_service`

Expected: FAIL because `NotebookCoordinator` does not exist and old start uploads a PDF.

- [ ] **Step 3: Implement immediate start and idempotent bind**

`start` validates only the Ferrari profile and bounded context, calls `store.begin`, starts incoming generation in the injected background runner, and returns immediately. It never calls `build_initial_packet` or `upload_pdf`. `bind` validates UUID-like identifiers, refuses binding the session to a second document, and returns the existing binding for duplicate input.

- [ ] **Step 4: Write the failing asynchronous submit test**

```python
def test_submit_returns_reviewing_before_codex_finishes_and_never_uploads(tmp_path):
    pending = []
    tablet = FakeTabletDocuments()
    coordinator = coordinator_fixture(tmp_path, tablet=tablet, background=pending.append)
    session_id = ready_bound_session(coordinator)
    result = coordinator.submit({
        "session_id": session_id, "document_id": "doc-1", "reply_page_index": 1,
        "marked_page_id": "p3", "response_page_id": "p4",
        "profile_id": "ferrari_3.28.0.162", "conversation_context": "",
    })
    assert result["status"] == "reviewing"
    assert len(pending) == 1
    assert tablet.upload_calls == []
```

- [ ] **Step 5: Implement submit and remove the obsolete unstaged PDF-start retry**

Validate page 2 and the bound document, export once with the existing pre-Codex transient retry, render page 2 into the private session directory, persist `reviewing` plus page-3/page-4 IDs, then enqueue the review workflow. Duplicate submit returns current public state without another export or task.

Delete the obsolete `SessionStarter` upload retry and its unstaged `test_start_retries_one_transient_usb_failure_before_generating`; notebook start has no USB upload. Preserve export retry coverage on the new submit path.

- [ ] **Step 6: Wire HTTP dispatch and health**

Route `/v1/sessions/bind`. Make `/health` call `coordinator.health()` and return:

```json
{"status":"ok","listener":true,"tablet_readable":true,"renderer":true,"codex":true}
```

Return HTTP 503 with safe booleans when the outbound read-only `/documents/` probe or renderer dependency check fails. Do not include exception text.

Route `/v1/sessions/ink-start` to `mark_first_ink`. Require the bound document
ID and page-2 ID, accept no biometric payload, and return the original
`first_ink_at` for duplicate observations.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
python3 -m unittest tests.test_notebook_service tests.test_native_codex_bridge
python3 -m unittest discover -s tests
```

Expected: PASS.

```bash
git add mac_bridge/notebook_service.py mac_bridge/server.py mac_bridge/service.py tests/test_notebook_service.py tests/test_native_codex_bridge.py
git commit -m "feat: orchestrate one native notebook session"
```

---

### Task 5: Run structured review and streamed response as two turns in one Codex task

**Files:**

- Modify: `mac_bridge/contracts.py`
- Modify: `mac_bridge/codex_app_server.py`
- Modify: `mac_bridge/notebook_service.py`
- Modify: `tests/test_native_codex_bridge.py`
- Modify: `tests/test_notebook_service.py`

**Interfaces:**

- Produces: `CodexAppServerClient.review_and_respond(..., on_response_delta) -> NotebookReviewResult`.
- Consumes: notebook session transition methods and `SentenceStream`.

- [ ] **Step 1: Add a notebook review schema without an embedded response letter**

Add `NotebookReview` and `NOTEBOOK_REVIEW_OUTPUT_SCHEMA` with exact fields `schema_version: 1`, `summary`, `corrections`, `annotations`, and `reflective_question`. Reuse the current normalized-anchor validation and red-correction rules. Do not remove legacy schema 3 until all historical packet tests have been retired.

Write tests that reject scoring language, multi-glyph corrections, anchors outside `[0,1]`, and more than 10 combined marks.

- [ ] **Step 2: Run the schema tests and verify they fail**

Run: `python3 -m unittest tests.test_native_codex_bridge.NotebookReviewContractTests`

Expected: FAIL because `NotebookReview` and its parser do not exist.

- [ ] **Step 3: Implement one-thread/two-turn workflow**

`review_and_respond` must:

1. initialize one channel;
2. create one named thread `Letters Home review · <session>`;
3. attach the page-2 render and run turn 1 with `NOTEBOOK_REVIEW_OUTPUT_SCHEMA`;
4. persist the review and phase `review-ready` before turn 2;
5. run turn 2 in the same thread with: `Write only a 150 to 168 character fictional Chinese reciprocal letter responding to the legible huipi. Never exceed 180 including punctuation.`;
6. forward only stable `item/agentMessage/delta` values to `on_response_delta`;
7. validate the final response through the 180-cell fitter;
8. return one result containing the single thread ID, structured review, and final fitted letter.

- [ ] **Step 4: Add channel-order and failure-retry tests**

Assert exactly one `thread/start`, two `turn/start` calls using the same `threadId`, image input only in turn 1, and deltas only from turn 2. A turn-2 failure must retain `review-ready` and allow response-only retry without repeating turn 1.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python3 -m unittest tests.test_native_codex_bridge tests.test_notebook_service
python3 -m unittest discover -s tests
```

Expected: PASS.

```bash
git add mac_bridge/contracts.py mac_bridge/codex_app_server.py mac_bridge/notebook_service.py tests/test_native_codex_bridge.py tests/test_notebook_service.py
git commit -m "feat: stream a response from the review task"
```

---

### Task 6: Package the native Ferrari template and rollback contract

**Files:**

- Create: `toolbar_launcher/templates/letters-home-ferrari.template`
- Modify: `mac_bridge/trial_bundle.py`
- Modify: `tests/test_native_document_launcher.py`
- Modify: `tests/test_device_installer.py`

**Interfaces:**

- Produces: template ID `letters-home-ferrari`, declared grid rectangle `(72,104)-(882,1592)`, and trial-manifest hashes.
- Consumers: QML page creation in Task 7 and live rollback in Task 9.

- [ ] **Step 1: Write failing template geometry and manifest tests**

```python
def test_ferrari_template_is_native_full_size_and_declares_the_10_by_18_grid(self):
    template = json.loads(
        (ROOT / "toolbar_launcher/templates/letters-home-ferrari.template").read_text()
    )
    constants = {next(iter(item)): next(iter(item.values())) for item in template["constants"]}
    self.assertEqual(template["formatVersion"], 1)
    self.assertEqual(template["orientation"], "portrait")
    self.assertEqual((constants["targetWidth"], constants["targetHeight"]), (954, 1696))
    self.assertEqual((constants["gridColumns"], constants["gridRows"]), (10, 18))
    self.assertEqual(
        (constants["gridLeft"], constants["gridTop"], constants["gridRight"], constants["gridBottom"]),
        (72, 104, 882, 1592),
    )
```

- [ ] **Step 2: Run tests and verify missing assets fail**

Run: `python3 -m unittest tests.test_native_document_launcher.NativeLauncherContractTests.test_ferrari_template_is_native_full_size_and_declares_the_10_by_18_grid`

Expected: FAIL because the template assets do not exist.

- [ ] **Step 3: Adapt the existing deterministic stationery fixture**

Translate the visual vocabulary from `fixtures/reply/reply-ferrari.svg` into the stock Ferrari 3.28 declarative `.template` JSON format recovered from the backup: retain the warm paper, fold memory, border, and muted red rules, and use ten equal columns and eighteen equal rows within the declared rectangle. Do not include generated text, signatures, seals, receipts, addresses, logos, or archival claims.

Install only the unique app-owned `.template` filename and portrait orientation. Do not replace the stock `templates.json` or any stock `.template` entry.

- [ ] **Step 4: Package and hash-pin assets**

Extend the trial bundle with `templates/letters-home-ferrari.template`. Its manifest entry includes SHA-256, byte count, mode `0644`, destination, `app_owned: true`, and rollback action `remove_if_hash_matches`. Refuse a pre-existing destination with different bytes.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m unittest tests.test_native_document_launcher tests.test_device_installer`

Expected: PASS.

```bash
git add toolbar_launcher/templates mac_bridge/trial_bundle.py tests/test_native_document_launcher.py tests/test_device_installer.py
git commit -m "feat: package the Ferrari letter template"
```

---

### Task 7: Create, bind, extend, and stream inside the stock notebook

**Files:**

- Modify: `toolbar_launcher/qmldiff/20-letters-home-launch.qmd`
- Modify: `toolbar_launcher/qmldiff/30-letters-home-submit.qmd`
- Modify: `toolbar_launcher/launcher.py`
- Modify: `tests/test_native_document_launcher.py`
- Modify: `tests/test_toolbar_launcher.py`

**Interfaces:**

- Consumes: Task 1 API contract, Task 3 public state, Task 4 HTTP routes, Task 6 template ID.
- Produces: one native notebook with page-specific non-interactive render layers and stock navigation.

- [ ] **Step 1: Recover and structurally verify the exact creation/duplication blocks**

Before editing QMDs, recover the exact Ferrari `CreateNotebook.qml`, `CreateNotebookWindow.qml`, and `Pages.qml` resources from the pinned Xochitl/QRR backup into the disposable exact tree. Confirm their resource IDs and the Task 1 symbols. Do not copy recovered proprietary source into commits or evidence.

Run `qmldiff check-compatibility` and a no-op structural apply against that tree. If direct creation, duplicate-page callback, or created document/page IDs cannot be observed in the exact sources, stop this task and report `native_notebook_api_unverified`; do not fall back to PDF or document-store mutation.

- [ ] **Step 2: Write failing QML contract tests**

Assert the launch and submit QMDs contain:

```python
self.assertIn("/v1/sessions/bind", launch)
self.assertIn("LibraryController.createDocument", launch)
self.assertIn("DocumentController.setTemplateForPage", launch)
self.assertIn("DocumentController.addPageWithTemplateAndPageSize", launch)
self.assertIn("DocumentController.copyPages", submit)
self.assertIn('phase === "response-streaming"', submit)
self.assertNotIn("response.document_id", launch + submit)
self.assertNotIn("upload", launch + submit)
self.assertNotIn("MouseArea", launch + submit)
self.assertNotIn("TapHandler", launch + submit)
```

Also assert the QML uses server-provided `incoming.glyphs` and `response.glyphs`; it must not contain `split("").join("\\n")`, height-derived `charactersPerColumn`, or `implicitWidth` placement.

Assert one `Connections` observer targets the existing stock stroke signal and
posts `/v1/sessions/ink-start` only for the bound page-2 ID. The patch must not
define a `MouseArea`, `TapHandler`, pen handler, or replacement gesture.

- [ ] **Step 3: Run tests and verify the old PDF path fails**

Run: `python3 -m unittest tests.test_native_document_launcher tests.test_toolbar_launcher`

Expected: FAIL on PDF document IDs, missing bind, and newline column layout.

- [ ] **Step 4: Implement native launch with a bounded readiness barrier**

The launcher sequence is:

1. POST start and receive `session_id`.
2. Invoke the exact stock creation callback with name `Letters Home <session_id>` and template `letters-home-ferrari` without showing the creator sheet.
3. Add page 2 with the same template.
4. POST bind with document and page IDs.
5. Poll `Library.entryForId(document_id)` with a 250 ms timer for at most 20 attempts.
6. Close the sidebar and open the stock `legacydevice/window/main` only after the entry exists.

On any failure, stop the timer, restore `Letters Home`, keep the sidebar usable, and enqueue one stock notification. Do not call `root.toggle()` before readiness.

- [ ] **Step 5: Implement page-specific render layers**

One `Item` inserted into stock `DocumentView` owns no input handlers and switches by current page ID:

- page 1 draws `incoming.glyphs`;
- page 3 draws red/neutral review geometry and compact text;
- page 4 draws `response.glyphs`.

Each glyph uses server `x`, `y`, `punctuation`, and a fixed Ferrari font size. Review ellipse coordinates multiply normalized anchors by the current scene width/height and clip to page bounds. The item is invisible for every non-Letters-Home notebook and on page 2.

Page 1 also shows the bounded provenance line `A fictional letter generated
for this encounter` below the grid without intercepting input.

- [ ] **Step 6: Implement submit, stock duplication, page add, and guarded advance**

The stock-styled envelope action appears only on the bound page-2 ID. On submit:

1. duplicate page 2 to page 3 through the exact stock
   `DocumentController.copyPages` callback used by Ferrari `PagesActions`;
2. add page 4 with `letters-home-ferrari`;
3. POST IDs to submit and return control immediately;
4. navigate to page 3 once IDs are durable;
5. poll state every 750 ms;
6. advance to page 4 once when the first response sentence is present only if the current page is still page 3 and the participant has not manually navigated since submit.

Every failure preserves page 2 and keeps stock close/swipe controls available.

- [ ] **Step 7: Run portable QML tests and exact structural gates**

Run:

```bash
python3 -m unittest tests.test_native_document_launcher tests.test_toolbar_launcher
/private/tmp/qmldiff-25681c3/target/release/qmldiff check-compatibility /private/tmp/ferrari-3.28.0.162.hashtab toolbar_launcher/qmldiff/20-letters-home-launch.qmd
/private/tmp/qmldiff-25681c3/target/release/qmldiff check-compatibility /private/tmp/ferrari-3.28.0.162.hashtab toolbar_launcher/qmldiff/30-letters-home-submit.qmd
```

Apply all QMDs to the disposable exact tree and assert exactly one sidebar entry, no QML parse error, and no replacement gesture or toolbar provider.

- [ ] **Step 8: Commit**

```bash
git add toolbar_launcher/qmldiff/20-letters-home-launch.qmd toolbar_launcher/qmldiff/30-letters-home-submit.qmd toolbar_launcher/launcher.py tests/test_native_document_launcher.py tests/test_toolbar_launcher.py
git commit -m "feat: run Letters Home as one native notebook"
```

---

### Task 8: Install and supervise the Mac bridge safely

**Files:**

- Create: `mac_bridge/launch_agent.py`
- Create: `mac_bridge/launchd/com.erniesg.letters-home.bridge.plist`
- Create: `scripts/install-letters-home-bridge`
- Create: `scripts/uninstall-letters-home-bridge`
- Create: `tests/test_bridge_launch_agent.py`
- Modify: `docs/mac-bridge.md`

**Interfaces:**

- Produces: a real `gui/$UID/com.erniesg.letters-home.bridge` LaunchAgent with explicit Python and sanitized environment.
- Consumes: notebook bridge server and bidirectional health from Task 4.

- [ ] **Step 1: Write failing plist tests**

```python
def test_launch_agent_uses_explicit_python_and_sanitized_environment(tmp_path):
    plist = render_launch_agent(
        repo_root=Path("/opt/letters-home"),
        python=Path("/opt/python/bin/python3"),
        home=Path("/Users/tester"),
    )
    assert plist["ProgramArguments"][:3] == ["/usr/bin/env", "-i", "HOME=/Users/tester"]
    assert "/opt/python/bin/python3" in plist["ProgramArguments"]
    assert "KeepAlive" in plist and plist["KeepAlive"] is True
    assert "EnvironmentVariables" not in plist
```

- [ ] **Step 2: Run tests and verify missing renderer fails**

Run: `python3 -m unittest tests.test_bridge_launch_agent`

Expected: ERROR importing `render_launch_agent`.

- [ ] **Step 3: Implement deterministic rendering and reversible scripts**

The generated job executes `/usr/bin/env -i` with only `HOME`, explicit `PATH`, and `PYTHONPATH`, then the verified Python executable and `-m mac_bridge.server`. It writes stdout/stderr under `~/.local/share/letters-home/`, uses `KeepAlive: true`, and never embeds tokens or inherited environment values.

Install validates `reportlab`, `pypdf`, `PIL`, `pdftoppm`, and the desktop-bundled Codex executable before atomically writing `~/Library/LaunchAgents/com.erniesg.letters-home.bridge.plist`, bootstrapping it, and checking bidirectional health. Uninstall bootouts only that label and removes only the hash-matching app-owned plist.

- [ ] **Step 4: Run tests and a disposable plist smoke**

Run:

```bash
python3 -m unittest tests.test_bridge_launch_agent
scripts/install-letters-home-bridge --check-only
plutil -lint mac_bridge/launchd/com.erniesg.letters-home.bridge.plist
```

Expected: PASS and `OK`; no service mutation in `--check-only`.

- [ ] **Step 5: Commit**

```bash
git add mac_bridge/launch_agent.py mac_bridge/launchd scripts/install-letters-home-bridge scripts/uninstall-letters-home-bridge tests/test_bridge_launch_agent.py docs/mac-bridge.md
git commit -m "feat: supervise the paired Mac bridge"
```

---

### Task 9: Retire the active PDF contract and validate the full slice

**Files:**

- Modify: `docs/product-brief.md`
- Modify: `docs/architecture.md`
- Modify: `docs/issues/010-native-codex-roundtrip.md`
- Modify: `docs/paper-pro-hardware-trial.md`
- Modify: `tests/test_native_document_launcher.py`
- Modify: `tests/test_device_installer.py`
- Modify: `mac_bridge/trial_bundle.py`

**Interfaces:**

- Consumes: all prior tasks.
- Produces: final portable evidence, exact Ferrari trial bundle, controlled install/rollback instructions, and live proof record.

- [ ] **Step 1: Replace stale PDF assertions and documentation**

Delete acceptance language that requires an imported initial/reviewed PDF, a second document ID, or vector text persisted in a reviewed packet. Replace it with the one-native-notebook, four-page, reversible-overlay contracts from the approved spec. Keep existing historical PDF documents untouched and document that migration behavior explicitly.

- [ ] **Step 2: Run the complete portable gate**

Run:

```bash
python3 -m unittest discover -s tests
tests/run-device-fixtures.sh
scripts/agent-evidence
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" PYTHONPATH="$PWD" /usr/bin/python3 -m unittest discover -s tests
```

Expected: required suite PASS on the developer runtime and the clean Darwin
Python runtime, only documented skips, and a new
`.agent/evidence/*/manifest.json` with no participant/model payload. Retire or
guard legacy PDF tests that import `PIL`, `pypdf`, or `reportlab`; do not make
the portable gate depend on trusted-Mac extras and do not edit CI workflow files
without a separate policy approval.

- [ ] **Step 3: Build and inspect the exact trial bundle**

Run:

```bash
scripts/build-native-trial-bundle --target ferrari --output /tmp/letters-home-ferrari-notebook-trial
python3 -m json.tool /tmp/letters-home-ferrari-notebook-trial/native-trial-manifest.json >/dev/null
```

Expected: manifest pins the three QMDs, native API contract, Ferrari template assets, rollback destinations, Xochitl/QRR hashes, and `requires_live_preflight: true`; it contains no execute mode or secrets.

- [ ] **Step 4: Commit the portable completion**

```bash
git add docs/product-brief.md docs/architecture.md docs/issues/010-native-codex-roundtrip.md docs/paper-pro-hardware-trial.md tests/test_native_document_launcher.py tests/test_device_installer.py mac_bridge/trial_bundle.py
git commit -m "docs: make the native notebook slice testable"
```

- [ ] **Step 5: Request the explicit physical-mutation checkpoint**

Before device writes, report exact current Ferrari OS, Xochitl hash, hashtab hash, installed QMD hashes, template destination state, bridge health, bundle hashes, backup destination, planned single Xovi restart, and rollback command. Stop for owner approval if any value differs or rollback is unavailable.

- [ ] **Step 6: Perform the approved Ferrari trial and record bounded evidence**

After approval, install only hash-pinned QMD/template assets, restart Xovi once, and verify:

1. one native notebook and no new PDF;
2. exactly two initial pages;
3. the 176-character fixture appears completely in multiple sentence batches;
4. page 2 has stock tools and gestures;
5. submit adds pages 3 and 4 under the same document ID;
6. known wrong glyph red, uncertain glyph neutral, page 2 unchanged;
7. one guarded advance and page-4 response streaming;
8. close/reopen recovers the same session;
9. Xochitl remains active with zero unexpected restarts.

Record only IDs, counts, hashes, service state, and pass/fail observations. Do not capture participant ink or model text in evidence.

- [ ] **Step 7: Rehearse rollback and run final verification**

Restore pretrial QMDs and template state, restart Xovi once, and verify every recorded pretrial hash. Reinstall only after rollback proof is green and the owner requests another trial.

Run `scripts/agent-evidence` again and commit only redacted documentation/evidence pointers if the repo policy allows them.

# Run the correspondence as one native notebook with a Mac Codex round trip

depends-on: 004,005,007,008
labels: rucksack-needs-human

## Goal

Create one portrait native reMarkable notebook, preserve every stock writing
and navigation control, stream a fictional incoming letter from the paired
Mac, and return reversible teacher marginalia plus a reciprocal letter inside
that same notebook.

## Acceptance tests

- The main-sidebar `Letters Home` entry starts a bridge session, clones one
  verified app-owned two-page blank seed through stock native page/document
  operations, binds both clone page ids, and opens that clone through
  `windowNavigator.open("legacydevice/window/main", ...)` within 1.5 seconds on
  a healthy warm Ferrari path. Codex generation is not on the open path.
- A missing or modified seed produces a stock notification, restores the
  enabled launcher within two seconds, and queues a stock-controller rebuild;
  it never leaves `Preparing letter…` stuck or consumes a damaged seed.
- The active flow contains no AppLoad window, PDF import, reviewed-document
  upload, second library item, or direct Xochitl document-store mutation.
- Page 1 polls cumulative stable `item/agentMessage/delta` text no faster than
  750 ms and renders server-provided glyph positions on a `954×1696`, `10×18`
  portrait grid, top-to-bottom with columns right-to-left. The fictional
  incoming letter is bounded to one page. Each published batch is revealed as
  a monotonic prefix at exactly one additional glyph per 90 ms tick.
- A bridge restart rehydrates page-1 text from durable session state. A missing
  or failed session leaves the stock document and exit/navigation behavior
  usable.
- Xochitl exclusively owns pen, marker, eraser, undo/redo, page navigation,
  close, swipe-down, and gesture behavior. The patch has no pointer handler,
  custom gesture window, or stock-toolbar mutation.
- Page 2 is native stationery and ink. The first completed stock pen stroke
  records `first_ink_at` once. `寄出` is the only added control, appears only on
  page 2, and stays clear of either stock toolbar orientation.
- Submit takes a read-only USB export, renders page 2 for Codex, and closes the
  biometric window atomically. Failure before Codex is retryable and leaves
  the ink safe; failure after task creation resumes from the durable receipt.
- Xochitl copies page 2 to page 3 and adds page 4 inside the same notebook.
  Duplicate submit reuses the same task, native page ids, and review state;
  it never adds duplicate pages or tasks.
- The first durable submit creates one visible, non-ephemeral `Letters Home
  review` Codex task. The task first returns schema-valid marginalia, then a
  reciprocal response in a second turn of the same task.
- Only grounded, high-confidence, single-glyph corrections become red ellipses
  with the suggested glyph adjacent on page 3. Uncertain readings stay neutral;
  page 2 remains untouched. The teacher note sizes to its content and is never
  a score, grade, or replacement transcription.
- Page 4 streams the reciprocal letter on the same portrait `10×18` grid. The
  response is constrained to one page and addresses only what is legible from
  the conversation.
- Completion may auto-advance to the ready page once only when the participant
  has not navigated. Manual page turns always win.
- Logs and evidence contain only state, counts, ids, hashes, and error codes;
  never participant ink, rendered reply bytes, correspondence text, biometric
  samples, Codex payloads, or secrets.
- Required tests use fake tablet, renderer, and Codex transports. Live Codex,
  USB export, QMLDiff/template install, LaunchAgent install, Xochitl restart,
  and hardware validation remain one explicit human-approved lane.

## Validation command

```bash
python3 -m unittest discover -s tests
tests/run-device-fixtures.sh
scripts/agent-evidence
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  PYTHONPATH="$PWD" /usr/bin/python3 -m unittest discover -s tests

# Human-approved only after portable and trusted-Mac evidence:
scripts/run-controlled-device-trial.sh --device ferrari
```

## Allowed secrets

None in required tests or the tablet bundle. The live path reuses the signed-in
desktop Codex installation; no OpenAI key is stored on the tablet, in the
LaunchAgent plist, or in the repository.

## Artifact outputs

- Exact Ferrari sidebar and document-view QMLDiffs.
- Native Ferrari KZip template package (`manifest.json`, `image.png`, and
  `image.svg`) and recovered native-notebook API contract.
- Paired-Mac notebook service, persisted Codex review/response client, and
  deterministic LaunchAgent installer/uninstaller.
- Hash-pinned, non-authorizing live-trial bundle with exact destinations and
  rollback actions.
- Fake round-trip tests, exact-resource compatibility proof, clean macOS system
  Python evidence, and redacted evidence manifest.

## Stop conditions

Stop before mutation if the exact Ferrari firmware, Xochitl, QRR hashtable,
recovered resources, active-QMD order, USB route, LaunchAgent health, or backup
boundary differs from the approved checkpoint. Stop before review if page 2
cannot be rendered without mutating the notebook. Preserve the open notebook;
never repair by importing a PDF or merging files into Xochitl's store.

## Human clarification protocol

The product owner has confirmed the one-notebook flow and a kind Chinese
teacher reading plus reciprocal response. Ask only before the exact physical
mutation plan or if that review tone or four-page structure changes.

## Recommended response

Keep Xochitl responsible for the notebook, ink, tools, and navigation. Keep the
paired Mac responsible for durable session state, Codex, reply rendering, and
review geometry. Exchange bounded state and a read-only page-2 rendering; never
exchange a replacement document.

## Trade-offs

One notebook removes duplicate library items and preserves the writer's native
ink, but page-1, page-3, and page-4 overlays depend on the exact proprietary QML
contract and paired-Mac session rehydration. The Ferrari pin makes that risk
testable and reversible; it does not imply compatibility with Chiappa or a
future Xochitl version.

## Definition of done

Ferrari is complete only after the owner observes one cloned notebook opening
from the main hamburger menu within 1.5 seconds on the warm path; page 1 visibly
streaming a complete one-page vertical
letter; page 2 accepting stock pen/marker/eraser and default gestures; submit
creating a persisted Codex task; page 3 circling a known wrong glyph with the
correct one adjacent while preserving page 2; page 4 streaming a readable
one-page response; no duplicate notebook/pages/task on retry; and uninstall
restoring exact pretrial hashes. Chiappa remains a separate unverified target.

## Free-form response

Record only the Codex task id, notebook/page ids, exact target/artifact hashes,
page count, and pass/fail observations. Do not attach participant ink, rendered
reply bytes, correspondence/model payloads, or biometric samples.

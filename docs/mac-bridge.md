# Paired Mac bridge runbook

The bridge is the private handoff between a connected reMarkable and the signed-in
Codex desktop installation on this Mac. On the verified Ferrari USB link it
binds to the observed Mac address `10.11.99.16:8765`, not the
Wi-Fi interface, and writes only identifier-only submit receipts under
`~/.local/share/letters-home/`.

## Preflight

1. In reMarkable settings, enable the USB web interface and keep the tablet
   connected by USB.
2. Confirm the Mac can see the tablet without SSH:

   ```bash
   curl --fail --silent http://10.11.99.1/documents/ >/dev/null
   ```

3. Install the trusted-Mac renderer dependencies and confirm Poppler is present:

   ```bash
   python3 -m pip install -e '.[trusted-mac]'
   command -v pdftoppm
   /Applications/ChatGPT.app/Contents/Resources/codex --version
   ```

4. Put any encounter themes in a private file outside the repository. Do not
   include participant ink, biometrics, provider payloads, or secrets.

## Run

```bash
scripts/letters-home-bridge \
  --conversation-context-file /private/path/to/encounter-context.txt
```

From the Mac, verify the USB-only listener:

```bash
curl --fail http://10.11.99.16:8765/health
```

Tapping `Letters Home` now creates a persisted incoming-image Codex task, imports
a native two-page PDF, and opens it in stock Xochitl. On page 2, `Send to Codex`
exports the annotated PDF, creates one persisted review task with the rendered
huipi attached, appends the marked copy and review as page 3+, imports it, and
opens page 3. A duplicate tap returns the same receipt instead of creating a
second task.

## Fail closed

Do not install the QMLDiff trial if the USB web interface or bridge health check
fails, exact-resource compatibility is not green, the Codex synthetic preflight
cannot create a persisted task, or the reviewed upload cannot be resolved to one
new document id. Never repair a failed upload by editing Xochitl's live document
store.

Build the redacted, hash-pinned Ferrari patch bundle without contacting the
tablet:

```bash
scripts/build-native-trial-bundle \
  --target ferrari \
  --output /tmp/letters-home-ferrari-native-trial
```

The bundle deliberately has no execute/install mode. Its manifest still
requires a live read-only preflight and a separately recorded rollback before
the QMDs are copied to hardware. Chiappa is refused until its exact
DocumentView resource is independently recovered and validated.

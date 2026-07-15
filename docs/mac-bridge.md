# Paired Mac bridge runbook

The bridge is the private handoff between a connected reMarkable and the
signed-in Codex desktop installation on this Mac. On the verified Ferrari USB
link it binds only to the observed Mac address `10.11.99.16:8765`, not the
Wi-Fi interface. Durable state under `~/.local/share/letters-home/` contains
bounded session/render state and identifiers, never provider credentials.

## Native notebook flow

`Letters Home` now creates one stock Xochitl notebook in the active My Files
folder. It applies the app-owned `letters-home-ferrari` template to two native
pages and binds their native document/page IDs before opening stock
`legacydevice/window/main`.

- Page 1 polls complete AI sentences and draws the server-provided 10×18 glyph
  coordinates over the native letter template.
- Page 2 is an untouched native-ink huipi with the normal reMarkable toolbar,
  close action, pen settings, and swipe behavior. The small `寄出` action is
  outside the toolbar and moves clear of a right or bottom stock toolbar.
- Submit uses stock `DocumentController.copyPages` to make page 3, adds native
  page 4, and exports the notebook only to the paired Mac for review. It does
  not upload or import a replacement PDF and does not write Xochitl's private
  document store.
- Page 3 overlays reversible teacher marginalia on the copied ink. Page 4
  streams the reciprocal letter from a second turn in the same Codex task.

## Preflight

1. In reMarkable settings, enable the USB web interface and keep the tablet
   connected by USB.
2. Confirm the Mac can read the tablet without SSH:

   ```bash
   curl --fail --silent http://10.11.99.1/documents/ >/dev/null
   ```

3. Confirm Poppler and the desktop-bundled Codex executable are available:

   ```bash
   command -v pdftoppm
   /Applications/ChatGPT.app/Contents/Resources/codex --version
   ```

   The active native path uses the standard library plus `pdftoppm`; legacy
   packet-renderer extras (`PIL`, `pypdf`, and `reportlab`) are not bridge
   startup dependencies.

4. Put optional encounter themes in a private file outside the repository. Do
   not include participant ink, biometrics, provider payloads, or secrets.

## Supervised service

Validate the exact Python, Codex, Poppler, plist, and any existing managed job
without changing launchd:

```bash
scripts/install-letters-home-bridge --check-only
```

Install the per-user job only while the tablet is connected. Installation is
atomic and succeeds only when `/health` confirms the listener, tablet reader,
renderer, and Codex in both directions:

```bash
scripts/install-letters-home-bridge \
  --conversation-context-file /private/path/to/encounter-context.txt
```

The generated job uses `/usr/bin/env -i`, an explicit Python, and only `HOME`,
`PATH`, and `PYTHONPATH`. It has `KeepAlive` and `RunAtLoad`, writes logs under
the app-owned state directory, and never serializes an API key or context text
into the plist. A failed bootstrap or health check restores the previously
hash-owned job.

Check or remove only the hash-owned job:

```bash
scripts/uninstall-letters-home-bridge --check-only
scripts/uninstall-letters-home-bridge
```

Uninstall leaves logs and session data in place. It refuses a plist changed by
another owner instead of deleting it.

For a foreground diagnostic run, use:

```bash
scripts/letters-home-bridge \
  --conversation-context-file /private/path/to/encounter-context.txt
```

## Fail closed

Do not install the QMLDiff trial if USB documents or bridge health is red, the
exact Ferrari QMLDiff apply is not green, or rollback hashes are unavailable.
Never repair a failure by writing `.rm`, `.content`, `.metadata`, or another
file in Xochitl's live document store.

Build the redacted, hash-pinned Ferrari bundle without contacting the tablet:

```bash
scripts/build-native-trial-bundle \
  --target ferrari \
  --output /tmp/letters-home-ferrari-notebook-trial
```

The bundle has no execute/install mode. Its manifest requires a live read-only
preflight and separately recorded rollback before QMD/template assets are
copied to hardware. Chiappa remains refused until its independent exact native
resource target is implemented and validated.

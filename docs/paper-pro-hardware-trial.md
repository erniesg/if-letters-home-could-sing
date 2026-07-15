# Ferrari Paper Pro hardware trial

Status: the AppLoad window path is retired. It caused the blank/custom-chrome
behavior recorded below and must not be repaired or relaunched. The current
candidate keeps the existing main-sidebar placement but changes its action to
request a native PDF from the paired Mac and open stock `DocumentView`. A second
exact QMLDiff adds one page-2 `Send to Codex` action; the stock pen toolbar,
close action, swipe-down behavior, and gestures remain owned by Xochitl.

The portable and trusted-Mac gates for this native candidate pass. A real
incoming task emitted streamed Chinese text, a detail-grounded review returned
one schema-valid single-glyph correction plus a reciprocal letter, the renderer
produces an exact `954×1696` five-page portrait smoke, and the three QMDs apply
cleanly to recovered Ferrari 3.28 resources. The native QMD install is complete
and stable; the visible streamed-text, native ink, submit, page-3 mark, and
page-4 response checks remain owner-observed gates.

## Installed native-document checkpoint

The owner enabled the tablet USB web interface and approved the held Ferrari
trial. Live discovery reconfirmed model `reMarkable Ferrari`, OS `3.28.0.162`,
Xochitl SHA-256
`10082aeb857c69c3f404ab189d7403318ba97d0c169e756ae9a5b3532b248a4a`, and
hashtab SHA-256
`ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd`.
The enabled USB document API returned HTTP 200. The live Mac-side USB address
is `10.11.99.16` on `en11`; the tablet fetched the bridge health endpoint there
successfully. This replaces the unverified `.2` fixture assumption.

Before mutation, the current QMDs and Xochitl service state were copied to:

```text
/home/root/.local/share/letters-home-installer/backups/20260715-ba4315e-native-document-roundtrip
```

The old launch QMD hash was
`002383284266cb9c5d97f01de7da03a071ad66089a6e22999fca77edd287017f` and
`30-letters-home-submit.qmd` was absent. The initially installed native
candidates were:

| Artifact | SHA-256 |
|---|---|
| `20-letters-home-launch.qmd` | `92fd0d8846097c8ca7bdce00a3f10233d7d7ec3a9c0fde15ae715813464e17e6` |
| `30-letters-home-submit.qmd` | `27a7a1ea5658f797a1a7f7eb20190d292ee383a2344d5bb333f9af00d8f7e7a9` |

The first atomic-copy attempt stopped before changing live files because the
target BusyBox image has no `install` utility. The retry used verified
`cp`, `chmod 600`, and `mv` operations. `/home/root/xovi/start` ran once.
Xochitl returned with PID `89992`, `NRestarts=0`, and loaded QMDs `10`, `20`,
`30`, `90`, and `95` without a QMLDiff failure. The bridge remains bound to the
private USB interface at `10.11.99.16:8765`.

The first owner tap created a real image task and uploaded a new `Letters Home`
PDF, but the sidebar later showed `Mac unavailable` instead of opening it. The
cause was not connectivity: Ferrari's USB API retained the `.pdf` extension in
both visible-name fields, while the adapter accepted only the extensionless
form. The upload therefore succeeded but its bounded discovery loop returned a
false `remarkable_upload_not_visible` failure after 45 seconds.

A regression test now uses the observed Ferrari response shape. The adapter
accepts the exact uploaded name with or without `.pdf`, the sidebar restores
the fixed-width `Letters Home` label after an error, and submit strips a
retained `.pdf` suffix before recovering the session id. Exact-resource checks
and the required evidence gate passed before the correction was installed.
The prior QMDs and service state are backed up at:

```text
/home/root/.local/share/letters-home-installer/backups/20260715-upload-name-retry-fix
```

The installed correction hashes are:

| Artifact | SHA-256 |
|---|---|
| `20-letters-home-launch.qmd` | `c169cca1f4af18fabcb3c82454cf670b5f87982e024a95df652dd86942a3f033` |
| `30-letters-home-submit.qmd` | `4f9992a0ba1982cb4f773b008ac3572d0ed4b39d7f5eea72da678bfd000dfb6c` |

The correction used verified atomic replacements and one Xovi restart.
Xochitl returned with PID `90649`, `NRestarts=0`, and all five QMDs loaded
without a QMLDiff failure. The bridge was restarted on the corrected adapter
and its health endpoint passes. This checkpoint still does not claim the
visible open, ink, submit, or returned page 3 passed; those require the next
owner tap and physical observation.

## First native reply and portrait correction

The next owner tap opened a real two-page native packet and the owner wrote on
page 2 with Xochitl. The first `Send to Codex` attempt failed before a Codex
task or receipt was created. The tablet journal shows the scene file being
written at the same instant. A private-safe replay after the save boundary
completed export, created review task
`019f6428-e570-70a0-b630-b7b230cc11dc`, imported one reviewed PDF, and returned
review page index `2`. This isolates the failure to the pre-Codex export/render
boundary rather than the teacher-review or reviewed-upload path.

The bridge now retries only the transient `remarkable_usb_unreachable` and
`reply_page_render_failed` states before starting Codex. The submit QMD writes
only HTTP status and the bridge's bounded safe error body to the device journal,
keeps the button label at `Send to Codex`, and remains idempotent after a review
receipt exists.

The physical packet also exposed an orientation error: it used the hardware
resolution order as a landscape PDF media box. The native contract is now the
Paper Pro Move's full portrait page, `954×1696`, for the incoming letter,
blank huipi, reply rendering, and every review page. A rendered three-page
smoke confirms identical portrait media boxes. Visual inspection confirms the
first two pages are edge to edge and portrait marginalia wraps inside its note
column rather than clipping at the right edge. A newly generated physical
portrait packet and its automatic page-3 open remain to be observed.

## Initial observed target

The connected tablet identified itself as `reMarkable Ferrari`, ARM64, OS
`3.28.0.162`. It matches the verified Ferrari pins:

- Xochitl SHA-256: `10082aeb857c69c3f404ab189d7403318ba97d0c169e756ae9a5b3532b248a4a`
- QRR hashtable SHA-256: `ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd`
- qt-resource-rebuilder SHA-256: `6726f561557406f36347e43fc2b44a88deef4fb273d2ece88f48f427dad8800f`
- active QMDs, in order: `90-cjk-font-menu.qmd`, then
  `95-language-defaults-active.qmd`
- Xochitl: active/running, zero recorded restarts during discovery
- AppLoad: absent from both the extension set and application directory
- free persistent space: approximately 28.3 GiB
- system libc: 2.39; the native backend requires only `libc.so.6`,
  `GLIBC_2.17`, and `GLIBC_2.34`

`/home/root/xovi/services/xochitl.service/extensions.d` and `exthome` are
symlinks to the corresponding `/home/root/xovi` directories. There is one
canonical extension and application destination, not two copies.

## Pinned build and artifacts

The build uses:

- AppLoad `0.5.3`, commit
  `5bb34a362f09f753f18bd6261558f8e2737aacdb`
- Xovi source commit `2b99649f5e4fd6288be7792a8570bd16418adb70`
- SDK image
  `eeems/remarkable-toolchain@sha256:37699143ba448dc5b55c914a18af93466f5a55fc31cce388ef9efa49e30ed457`
- SDK Qt/RCC `6.8.2`
- upstream AppLoad QMD SHA-256:
  `adb0604ec314bf49a2194e8982df7a865f673561383b43584fa2fd236f433815`
- adapted AppLoad QMD SHA-256:
  `8a15eada28010751f7b4ae50ae8853837335820d3346887478b4b9736c073c6e`
- adapted AppLoad resource manifest SHA-256:
  `093e26c241b2b776228de174c0dce1feab5bb46dcc517ea30b2f3b7313191aee`
- upstream AppLoad `window.qml` SHA-256:
  `848b234015d2d8671648b6b661e57cdd3b51d80c537c38cb053e503cf3a95c30`
- validated and preserved AppLoad `window.qml` SHA-256:
  `848b234015d2d8671648b6b661e57cdd3b51d80c537c38cb053e503cf3a95c30`

Current reviewed artifacts:

| Artifact | SHA-256 |
|---|---|
| Adapted ARM64 `appload.so` | `633efa6c66aa741776280737b251ce2b50b1c00d74bbc02c966dee12ff5aa9e2` |
| Native ARM64 backend `entry` | `d7713ecf21851c264ab0e94edcef5c49045162faf9e1f14ed12d0f0a3e17a92c` |
| App `resources.rcc` | `0e78534cd02e069725461c6e4bcb28e0fe01ad131915be523a931121e55fe9c1` |
| App `manifest.json` | `ca6000280526388560715ca3869b3d1f2eb67cad626ee1b4bc36c3fd91938338` |
| Revised inert sidebar QMD | `da7f7d22fab609fd4f7c144e8661f65d7416fe74c0652a4a2e01be69c2cc304c` |
| Revised launch-action QMD | `002383284266cb9c5d97f01de7da03a071ad66089a6e22999fca77edd287017f` |
| Envelope SVG embedded in AppLoad | `c0437e3f3d8eb9436d3be8be54c5afa86bfd14370a78c3907c16a1803d5ccb30` |

Installed first render-repair attempt:

| Artifact | SHA-256 |
|---|---|
| No-chrome ARM64 `appload.so` | `9d370d31ac399b7f5b52b92afaaac0283b6ecd400ea0a4e8d6cc543639a5e8d1` |
| Repaired native ARM64 backend `entry` | `5fa9f01089ab497226162ae292aebbe8d5415877aa161ea6646597389ec67a20` |
| Repaired app `resources.rcc` | `1cb98ab70573ad0dbadde2be5b12f8d297c16bed8edbaae648f6d73d43553984` |
| Codex-generated Ferrari incoming fixture / app `icon.png` | `d8053206b0883fa4b39f3a6cbac9475bec34098586114c9562cb87f812b9495c` |

Corrective candidates built from the same pins:

| Artifact | SHA-256 |
|---|---|
| Stock-chrome ARM64 `appload.so` | `f150d6a6fb0f6be726d93a4fe7615fd960abb78260014359b306e000bac0a57a` |
| App `resources.rcc` without unsupported attached objects | `bfa560d40ceac00a4c7a603d85e1a154812ea59f74b97afea4c89abcaad5d10c` |

The AppLoad build normalizes embedded resource mtimes to upstream commit epoch
`1779378487`; two clean builds in the same pinned container reproduced the same
`appload.so` hash. Offline QMLDiff compatibility and full structural
application pass for adapted AppLoad + inert + launch phases in their intended
order. Linux tests also drive the compiled native backend through the complete
fixture page flow over a real `SOCK_SEQPACKET` connection.

## Completed first mutation: inert item only

The approved first mutation created backup
`/home/root/.local/share/letters-home-installer/backups/20260715-e58a8f7-first-inert`,
installed the adapted runtime, native app, and inert QMD, then ran
`/home/root/xovi/start` once. Xochitl returned under a new PID with zero
automatic restarts; QMLDiff loaded all three QMDs in order, AppLoad loaded the
`letters-home` app, and the original QRR/CJK/hashtable hashes remained exact.
The owner confirmed the item was visible but requested that it move from the
initial location to below `Import files`. Clicking remained intentionally inert.

## Completed placement correction and launch

The placement correction created backup
`/home/root/.local/share/letters-home-installer/backups/20260715-329f1c1-import-placement`,
installed inert QMD SHA-256
`da7f7d22fab609fd4f7c144e8661f65d7416fe74c0652a4a2e01be69c2cc304c`,
and restarted Xochitl once. The owner confirmed `Letters Home` appeared
immediately below `Import files`.

The separately approved launch phase created backup
`/home/root/.local/share/letters-home-installer/backups/20260715-329f1c1-launch-enable`,
installed launch QMD SHA-256
`002383284266cb9c5d97f01de7da03a071ad66089a6e22999fca77edd287017f`,
and restarted Xochitl once. The item then launched AppLoad and its native
backend successfully, with zero automatic Xochitl restarts.

## Reproduced blank-window failure and retired repair boundary

The live journal showed that the sidebar handler, AppLoad coordinator, native
backend process, and `SOCK_SEQPACKET` connection all started. The UI then
stopped at:

```text
Type StationeryLayer unavailable
Non-existent attached object
```

Adding the same Controls import as `Main.qml` did not resolve the failure: the
target repeated `Non-existent attached object` at the next line. An attempted
corrective bundle removed every `Accessible.*` attachment from the app QML, but
that AppLoad branch is now historical and must not be installed.

The no-chrome attempt also trapped the owner when the app failed before its own
close control could instantiate. The native replacement avoids AppLoad
entirely, so exit and swipe behavior are the stock document behavior even when
the Mac bridge is unavailable.

For the native trial, re-run the exact Ferrari firmware, Xochitl, Sidebar,
DocumentView, QRR hashtable, active-QMD, process, free-space, and
installed-artifact checks. Back up the current Letters Home QMDs, replace only
the sidebar launch action, add the exact DocumentView submit QMD, and run
`/home/root/xovi/start` once. No reboot is planned. Expected unavailability is
15–45 seconds, capped at two minutes. Rollback restores the backed-up QMD set
and restarts once. Verify the full-bleed incoming page, native pen controls on
the huipi, persisted Codex task, reviewed page 3, and unchanged stock
close/swipe behavior.

The stock reMarkable screenshot helper will not be used while Xovi runs.
Evidence is manual observation plus service status, restart count, and hashes.

## Rollback

For the placement correction, restore the backed-up original inert QMD and run
`/home/root/xovi/start` once. Its hash must return to
`fe98c19f1423516e1197c5e351c489ece17739c22eb7777ecf26b2bebe7b0dee`.

For a full trial rollback, remove only the three paths that were absent at
initial preflight—AppLoad extension, AppLoad application directory, and Letters
Home QMD—restore any recorded file that differs from its backup, and run
`/home/root/xovi/start` once. Rollback must restore the two original CJK QMD
hashes, QRR and hashtable hashes, and the pretrial active extension set. Stop
rather than broadening a hash or locator.

## Trial scope

The native vertical slice uses the signed-in desktop Codex app-server for both
conversation-conditioned streamed Chinese text and a structured teacher-style
review with a reciprocal response letter. It transfers native PDFs through the
enabled USB web interface, preserves the writer's original page, and marks only
a page-3 copy. Real WHOOP capture remains a later human-approved provider lane.

## Streamed-text and grounded-review smoke (2026-07-15)

- Persisted incoming Codex task `019f6443-8edf-77c1-a36a-86a2a49a6230`
  emitted 158 agent-message deltas. The bridge coalesced them into a bounded
  180-character final fictional letter without logging the text.
- Persisted schema-3 review task `019f6451-711d-7a00-aa5f-3e5d6ae618e7`
  returned five bounded annotations: one high-confidence single-glyph
  correction eligible for a red ellipse, one uncertain reading that remains
  non-red, and a 49-character reciprocal response letter.
- The private reply rendering and model payload were not copied into evidence,
  documentation, issues, or logs. Only task ids and bounded counts are recorded.
- Immediately before the streamed-text mutation, Ferrari still matched OS
  `3.28.0.162`, Xochitl
  `10082aeb857c69c3f404ab189d7403318ba97d0c169e756ae9a5b3532b248a4a`,
  hashtab
  `ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd`,
  and the prior QMD hashes. The prior submit QMD and service state are backed up
  under
  `/home/root/.local/share/letters-home-installer/backups/20260715-streamed-text-schema3`.
- Only `30-letters-home-submit.qmd` changed. Its installed SHA-256 is
  `2d31a7d0ecff761293178d5b9483d5c4eb9b6f9ae147be7ae05b4c6304bcb8b4`.
  One Xovi restart returned Xochitl as PID `92610`, `NRestarts=0`; the journal
  loaded QMDs 10, 20, and 30 without a QMLDiff error, and the tablet reached the
  replacement bridge at `10.11.99.16:8765`.

# Ferrari Paper Pro hardware trial

Status: the inert install, placement correction, and approved launch phase all
completed and remained stable. Two attempted launches reproduced a blank app
because this target rejects the app's `Accessible` attached objects. The tablet
has been recovered to its main screen. A corrective bundle without those
objects and with stock AppLoad exit chrome restored is built at the next
approval boundary below.

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

## Reproduced blank-window failure and repair boundary

The live journal showed that the sidebar handler, AppLoad coordinator, native
backend process, and `SOCK_SEQPACKET` connection all started. The UI then
stopped at:

```text
Type StationeryLayer unavailable
Non-existent attached object
```

Adding the same Controls import as `Main.qml` did not resolve the failure: the
target repeated `Non-existent attached object` at the next line. The corrective
bundle therefore removes every `Accessible.*` attachment from the app QML.
Target `qmllint` no longer reports unresolved attached types. Visible purpose,
provenance, state, and error copy remain unchanged.

The no-chrome attempt also trapped the owner when the app failed before its own
close control could instantiate. The correction preserves upstream AppLoad's
exact pull-down/minimize/maximize/close behavior for Letters Home. Exit remains
available even if application QML fails again.

Before a repair install, re-run the exact Ferrari firmware, Xochitl, QRR,
hashtable, active-QMD, process, free-space, and installed-artifact checks. Back
up the currently installed extension and app resource, then atomically replace:

- `/home/root/xovi/extensions.d/appload.so`
- `/home/root/xovi/exthome/appload/letters-home/resources.rcc`

The icon, backend, manifest, inert QMD, and launch QMD remain byte-identical. Run
`/home/root/xovi/start`
once; no reboot is planned. Expected unavailability is 15–45 seconds, capped at
two minutes. Rollback restores the two backed-up files and restarts once.
After repair, verify the incoming fictional letter, forward navigation to blank
huipi stationery, ink preservation, submit, teacher-style non-scoring fixture
marginalia on page 3, and stock swipe-down/minimize/maximize/close behavior.

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

The repaired vertical slice uses the bundled fictional incoming image and a
transparent teacher-style fixture review. It makes no live OpenAI or WHOOP
call. Response-dependent OCR/model review and real heart-rate capture remain
later human-approved provider lanes; the present trial proves the three-page
tablet interaction and preservation of the writer's original ink.

# Ferrari Paper Pro hardware trial

Status: the first inert Ferrari install completed and remained stable. The
owner confirmed the item was visible, requested placement below `Import files`,
and the revised replacement QMD is held at the approval boundary below.

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

The AppLoad build was repeated in the same pinned container and reproduced the
same `appload.so` hash. Offline QMLDiff compatibility and full structural
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

## Proposed placement correction: below Import files

This is the next approval boundary. The correction will:

1. Re-run the exact Ferrari firmware, Xochitl, QRR, hashtable, active-QMD,
   process, free-space, installed-artifact, and launch-QMD-absence checks.
2. Back up the currently installed inert QMD, SHA-256
   `fe98c19f1423516e1197c5e351c489ece17739c22eb7777ecf26b2bebe7b0dee`.
3. Stage and hash-verify revised inert QMD SHA-256
   `da7f7d22fab609fd4f7c144e8661f65d7416fe74c0652a4a2e01be69c2cc304c`.
4. Atomically replace only
   `/home/root/xovi/exthome/qt-resource-rebuilder/10-letters-home-inert.qmd`
   with mode `0600`; the launch QMD remains absent.
5. Run `/home/root/xovi/start` once. No reboot is planned; expected library
   unavailability is 15–45 seconds and the observed window is capped at two
   minutes.
6. Confirm `Letters Home` appears immediately below `Import files`, the CJK
   menus still work, and Xochitl remains stable. It stays inert in this phase.

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

## Second phase after visual confirmation

Only after the owner confirms the corrected inert placement and stability will
a second approval install `20-letters-home-launch.qmd` (`0600`) and restart
Xochitl once.
The owner can then tap `Letters Home`, decline or select unavailable WHOOP,
swipe to the blank huipi, write with the pen, submit, and verify page 3 shows
the unchanged ink plus reversible fixture marginalia and a short review. This
trial makes no live OpenAI or WHOOP call.

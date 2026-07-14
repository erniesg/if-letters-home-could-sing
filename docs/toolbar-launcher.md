# Fixture-only main-sidebar launcher spike

This round stops at deterministic host fixtures. It performs no tablet SSH,
Xochitl mutation, QMD installation, restart, reboot, or screenshot capture.
The fixture hash identifies checked-in sanitized bytes. Separate device-source,
Xochitl, and hashtable hashes come from the verified full backups; they are not
a claim about the device currently connected. Approved discovery must confirm
every physical pin without broadening the locator.

## Exact fixture matrix

| Target | Model label | OS | QRR resource | Sanitized fixture SHA-256 | Backed-up source SHA-256 |
|---|---|---|---|---|---|
| Chiappa | reMarkable Paper Pro (Chiappa) | `3.28.0.162` | `/qml/device/view/navigator/Sidebar.qml` / `[[4911547370760691430]]` | `03d6744e13fab8b4d268029e4b9529d90f71196e4a5f3caf68e990edaf522578` | `5cfd661e6c68c343513d9ca034042ee3f5cdc3ab0df77ea0396838c77135adc0` |
| Ferrari | reMarkable Paper Pro Move (Ferrari) | `3.28.0.162` | `/qml/device/view/navigator/Sidebar.qml` / `[[4911547370760691430]]` | `03d6744e13fab8b4d268029e4b9529d90f71196e4a5f3caf68e990edaf522578` | `5cfd661e6c68c343513d9ca034042ee3f5cdc3ab0df77ea0396838c77135adc0` |

The fixture and backed-up source hashes are deliberately separate contract
fields. A physical preflight must never compare device bytes with the
sanitized fixture hash.

| Target | Xochitl SHA-256 | QRR hashtable SHA-256 |
|---|---|---|
| Chiappa | `9e3e0372a15da25b148ac17667feb566014440e079c3e3ee504112d556ad2e10` | `313aaf72896b152c7668bcd83fa9ed23e1c5b9d24eacc1a34bebf66ce66d68b1` |
| Ferrari | `10082aeb857c69c3f404ab189d7403318ba97d0c169e756ae9a5b3532b248a4a` | `ebbb415d5e875a67a84416c3029e6ce7e94861a32bb8d390fd01fe0403d492cd` |

Ferrari and Chiappa are separate target records and fixtures even though the
current fixture and recovered sidebar bytes match. Their Xochitl binaries and
hashtables are distinct. Each independently pins AppLoad `0.5.3`, Xovi
`0.3.3`, QMLDiff commit
`25681c3cc7addb93fdbb41ceac1f1bdce8b2625d`, and qt-resource-rebuilder commit
`7874154dba6793cc68a15fae0fb9dd272c4ed20a`.

The exact fixture QMD order is:

1. `appload-0.5.3.qmd`
2. `fixture-cjk-font-1.qmd`
3. `fixture-cjk-language-1.qmd`

Those CJK names are fixture identities, not observations of device filenames.
The preflight accepts the declared unrelated
`fixture-quick-settings-clock-1.qmd`, because it affects
`/qml/QuickSettings.qml`, and rejects every undeclared active mod.

## Locator and staged action

The verified Chiappa and Ferrari `3.28.0.162` backups contain their distinct,
exactly pinned Xochitl binaries. Offline Qt-resource parsing and Zstandard
decompression recover a byte-identical main library sidebar from each as
`/qml/device/view/navigator/Sidebar.qml`; its own source comment identifies it
as the menu opened by the top-left menu button.
The saved QRR hashtable maps that path to resource
`[[4911547370760691430]]`. The candidate QMLDiff traverses
`FocusScope > ColumnLayout#filterColumn`, locates
`ArkControls.SidebarItem#filterMyFiles`, and inserts immediately before it.
The exact source uses `text`, `highlighted`, and `Common.Values`; the fixture
and QMLDiff pin those 3.28 names. Every hashed token passes the pinned QMLDiff
compatibility checker against both target-specific saved tables. Applying
phase 1 and then phases 1+2 to each target's recovered source succeeds with
exactly one and two diffs, respectively. Approved read-only discovery must
still confirm that the connected device matches the backed-up binary,
hashtable, and active runtime or stop.

The former `/qml/DocumentView.qml` / `toolbarProvider.editingTools` locator is
rejected by regression tests. The launcher must never appear among pen and
eraser controls inside an open document.

`10-letters-home-inert.qmd` adds one `Letters Home` sidebar item with an
envelope icon and an empty click handler. `20-letters-home-launch.qmd` changes
only that item's handler to
`AppLoadLauncher.launchApplication("letters-home", [], {}, false)`. The host
harness refuses the launch phase unless visual/stability confirmation is
explicitly represented. The SVG icon is packaged under
`qrc:/letters-home/icons/letter`.

The QMLDiff language and AppLoad call are pinned to their maintained upstream
contracts:

- <https://github.com/asivery/qmldiff/tree/25681c3cc7addb93fdbb41ceac1f1bdce8b2625d>
- <https://github.com/asivery/rm-appload/tree/v0.5.3>
- <https://github.com/asivery/rm-xovi-extensions/tree/7874154dba6793cc68a15fae0fb9dd272c4ed20a/qt-resource-rebuilder>

## Composition and rollback proof

The harness preserves the recorded AppLoad and CJK fixture order, while
correctly treating those patches as affecting resources other than
`Sidebar.qml`. It inserts the launcher in the bounded sidebar region. Tests
compare the pre-install and installed resources with that region removed, so
changes to another QML subtree fail. `My files`, `Tags`, and `Trash` remain
present, the launcher occurs before `My files`, repeated application is
deterministic, and duplicate input is rejected.

The rollback record pins both pre-install and installed SHA-256 values.
Uninstall refuses a resource changed after install, otherwise restores the
byte-identical pre-install composition. That restored composition still
contains the CJK font and language fixture changes.

Run the portable proof with:

```bash
python3 -m unittest tests.test_toolbar_launcher
scripts/agent-evidence
```

## Pending device observations

No physical UI or Xochitl stability observation was made in this round. Before
the first device step, the owner must approve the exact tablet, read-only
discovery commands, proposed QMD/RCC destinations and hashes, rollback files,
and expected downtime. The first mutation installs only the inert phase. The
launch phase remains held until the inert icon is visually confirmed and
Xochitl stability is reviewed. Evidence must use the approved
framebuffer/AppLoad path; the stock reMarkable screenshot helper is forbidden
while Xovi is running.

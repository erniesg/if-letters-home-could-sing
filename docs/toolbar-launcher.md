# Fixture-only toolbar launcher spike

This round stops at deterministic host fixtures. It performs no tablet SSH,
Xochitl mutation, QMD installation, restart, reboot, or screenshot capture.
The resource path and hash below identify the checked-in sanitized fixture,
not a claim that OS `3.28.0.162` hardware has been observed. An approved
hardware discovery must confirm every pin without broadening the locator.

## Exact fixture matrix

| Target | Model label | OS | QRR resource | Fixture SHA-256 |
|---|---|---|---|---|
| Chiappa | reMarkable Paper Pro (Chiappa) | `3.28.0.162` | `/qml/DocumentView.qml` / `[[2857280009207495592]]` | `095e19d24d23ee8d2cbc67f9a08d3af5a13e27644eb7a361fb6d0aa10f136c4e` |
| Ferrari | reMarkable Paper Pro Move (Ferrari) | `3.28.0.162` | `/qml/DocumentView.qml` / `[[2857280009207495592]]` | `095e19d24d23ee8d2cbc67f9a08d3af5a13e27644eb7a361fb6d0aa10f136c4e` |

Ferrari and Chiappa are separate target records and fixtures even though the
current fixture bytes match. Each independently pins AppLoad `0.5.3`, Xovi
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

The candidate hashed QMLDiff locator selects resource
`[[2857280009207495592]]`, then the unique
`toolbarProvider.editingTools` column. This follows the hashed toolbar shape
used by maintained QMLDiff mods, but its OS `3.28.0.162` mapping remains a
hardware assertion. If discovery does not reproduce the one exact match, the
run stops.

`10-letters-home-inert.qmd` adds one button whose click handler is empty.
`20-letters-home-launch.qmd` changes only that button handler to
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

The harness first composes the AppLoad and CJK fixture mods in recorded order,
then inserts the launcher in the bounded toolbar region. Tests compare the
pre-toolbar and installed resources with that region removed, so changes to
the CJK settings, canvas, or any other QML subtree fail. Repeated application
is deterministic and duplicate input is rejected.

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

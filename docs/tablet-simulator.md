# AppLoad UI and host simulator

`tablet_app/appload` is the source application. Its manifest, root QML
entrypoint, `AppLoad` endpoint, unload hook, Qt resource manifest, and
backend invocation follow the maintained `rm-appload` full example at
[commit `123c29eb2fa6d1025cb3fa1b47bece6cee0a74f6`](https://github.com/asivery/rm-appload/commit/123c29eb2fa6d1025cb3fa1b47bece6cee0a74f6)
(AppLoad v0.5.3 lineage).
The bundled backend is a small native C program. It connects to the temporary
Unix `SOCK_SEQPACKET` path supplied as `argv[1]` and exchanges the example
protocol's separate eight-byte header and UTF-8 body packets. The Python
adapter remains the portable reference model and simulator, but it is not
shipped to the tablet: Ferrari `3.28.0.162` has no `python3` executable.

The frontend keeps stationery, participant ink, and marginalia in separate
QML components. Page 1 always carries the fictional-provenance disclosure.
Page 2 begins with an empty stroke list over deterministic huipi stationery.
Page 3 reuses the same immutable stroke values and adds structured fixture
annotations as a toggleable overlay.

## Host simulator

Run the deterministic timeout/retry path with no tablet, network, private
data, provider credential, or third-party Python dependency:

```bash
python3 -m tablet_app.simulator --profile chiappa --orientation portrait --scenario timeout-retry
```

Profiles are `chiappa` and `ferrari`; orientations are `portrait` and
`landscape`; scenarios are `complete`, `timeout-retry`, `offline`, and
`empty`. The simulator prints state names and synthetic stroke counts only,
not pen coordinates or payload bodies.

The checked-in SVG layout goldens cover incoming, reply, and marginalia for
both exact device sizes in both orientations. Regenerate or verify them with:

```bash
python3 -m tablet_app.simulator --write-snapshots tablet_app/snapshots
python3 -m tablet_app.simulator --verify-snapshots tablet_app/snapshots
```

These are deterministic layout-model snapshots, not claims about the device
Qt renderer, colour e-ink refresh, or pen latency.

## AppLoad bundle

Source validation does not require Qt:

```bash
python3 -m tablet_app.packaging --check
```

With Qt's `rcc` and a C compiler available, build the exact AppLoad directory
shape containing `manifest.json`, `icon.png`, `resources.rcc`, and a native
executable `backend/entry`:

```bash
python3 -m tablet_app.packaging --output tmp/letters-home-appload
```

The bundle contains a fixture-only review backend. It does not contain Python,
provider credentials, or live provider calls. On Linux, the test suite compiles
and drives the native backend through a real Unix sequence-packet socket across
consent, reply, stroke, submit, and marginalia. Darwin skips that kernel-specific
test while still compiling the backend.

## Pending hardware assertions

The pinned reMarkable SDK container now builds both the Qt `resources.rcc` and
ARM64 backend. The following remain hardware integration assertions, not host
claims:

- QML `Canvas` refresh and `MouseArea` pressure/timing under the device input
  stack;
- accessibility roles and focus order in the target Qt/AppLoad build;
- AppLoad endpoint lifecycle and backend termination on the target image;
- colour e-ink contrast, refresh behavior, and physical pen latency.

No stock screenshot helper, tablet SSH, Xochitl mutation, installation,
reboot, or live provider request is part of this simulator lane.

# Fixture installer and recovery runbook

This round packages and validates only synthetic Ferrari and Chiappa roots. The
installer refuses any root without `.letters-home-fixture-device.json`; it does
not discover or contact a tablet. The candidate paths inside a fixture are test
contracts, not confirmed AppLoad or Xovi destinations on OS `3.28.0.162`.

No command in this runbook uses SSH, stops or restarts Xochitl, installs a QMD
on hardware, reboots, invokes the stock screenshot helper, or calls a live
provider.

## Versioned release

`device_installer` version `1.0.0-fixture.1` builds the existing AppLoad bundle
and packages both staged toolbar QMDs plus their icon resources. Its generated
`payload-manifest.json` contains separate Ferrari and Chiappa records, exact OS,
resource, QMLDiff/QRR, Xovi and AppLoad pins, required file modes, and a SHA-256
and byte count for every payload file. The install phase activates only
`10-letters-home-inert.qmd`; the launch QMD remains packaged but inactive until
an approved hardware trial confirms the inert icon and Xochitl stability.

With Qt `rcc` available, build the release with:

```bash
python3 -m device_installer build-release --output tmp/letters-home-release
```

The required tests use a deterministic fixture `rcc`, because the current VM
does not provide the target Qt toolchain. That proves the package, checksum,
permission, install and rollback contracts without claiming target-runtime
compatibility for the synthetic RCC bytes.

## Synthetic install and uninstall

```bash
python3 -m device_installer create-fixture --target chiappa --root tmp/chiappa
python3 -m device_installer preflight --release tmp/letters-home-release --fixture-root tmp/chiappa
python3 -m device_installer install --release tmp/letters-home-release --fixture-root tmp/chiappa
python3 -m device_installer uninstall --release tmp/letters-home-release --fixture-root tmp/chiappa
```

Repeat with `--target ferrari`; the records remain independent even while the
sanitized resource bytes share a hash. Preflight fails closed on low fixture
space, an absent or invalid backup marker, model/OS/resource/version mismatch,
unknown or reordered QMDs, missing dependencies, payload checksum/mode drift,
destination conflicts, and an active transaction.

Install stages the complete payload before moving either tree into place. It
records the original active-QMD bytes before the first move. A duplicate exact
install is a no-op. Uninstall first verifies every installed checksum and mode,
then restores the original active-QMD record byte-for-byte and removes only the
managed payload.

## Interrupted operation recovery

An interrupted install or uninstall leaves
`.letters-home-installer/transaction.json`. Normal preflight refuses to proceed
while that marker exists. Recover to the exact pre-install fixture state with:

```bash
python3 -m device_installer recover --release tmp/letters-home-release --fixture-root tmp/chiappa
```

Recovery refuses if the original active-QMD backup is unavailable or the pinned
resource changed during the transaction. Do not delete the transaction marker
or broaden a checksum manually.

Run the complete host matrix with:

```bash
tests/run-device-fixtures.sh
scripts/agent-evidence
```

The matrix covers both exact targets, all specified refusal classes,
idempotency, interrupted install/uninstall recovery, byte-identical rollback,
the three-page fixture flow, timeout/retry, first-ink state, reversible review,
mock heart-rate contracts, and both orientations. It does not prove device Qt
rendering, pen latency, suspend/resume, colour refresh, Xochitl stability, CJK
menus, or physical launcher behavior.

## Held hardware step

Before any physical trial, request owner approval separately for Ferrari and
Chiappa with the current backup verification, read-only discovery commands,
observed model/OS/resource/QMD/dependency pins, proposed destinations and file
modes, exact mutation duration, framebuffer/AppLoad evidence method, and
rollback commands. Stop on the first divergence. The first approved mutation
may activate only the inert QMD; launch activation remains a second decision.

Generate the target-specific held-boundary manifest with:

```bash
scripts/run-controlled-device-trial.sh --device chiappa
scripts/run-controlled-device-trial.sh --device ferrari
```

The script performs no device or network operation and exits `4` (`human
decision required`). It records fixture expectations separately from observed
device state, which remains empty until the owner approves a five-minute,
read-only discovery window. There is intentionally no `--execute` mode before
that discovery fixes the physical paths, hashes, backup files, rollback
commands, and expected downtime.

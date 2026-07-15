#!/usr/bin/env sh
set -eu

python3 -m unittest \
  tests.test_device_installer \
  tests.test_appload_runtime \
  tests.test_toolbar_launcher \
  tests.test_tablet_app \
  tests.test_reply_review \
  tests.test_heart_rate

for target in chiappa ferrari; do
  for orientation in portrait landscape; do
    python3 -m tablet_app.simulator \
      --profile "$target" \
      --orientation "$orientation" \
      --scenario complete
    python3 -m tablet_app.simulator \
      --profile "$target" \
      --orientation "$orientation" \
      --scenario timeout-retry
  done
done

python3 -m tablet_app.simulator --verify-snapshots tablet_app/snapshots
printf '%s\n' 'fixture device matrix passed: chiappa,ferrari; install,refusal,recovery,flow,orientation,retry'

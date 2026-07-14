#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$repo_root"
exec "${PYTHON:-python3}" -m device_installer.trial_plan "$@"

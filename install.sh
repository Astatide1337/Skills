#!/usr/bin/env bash

# Compatibility entry point for older GitOps/Kagent bootstraps.
set -euo pipefail
exec "$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/scripts/install.sh" "$@"

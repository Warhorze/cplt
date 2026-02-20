#!/usr/bin/env bash
# Backward-compatible wrapper for singular script name.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/generate_demos.sh" "$@"

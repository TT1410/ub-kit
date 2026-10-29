#!/usr/bin/env bash
# Install ub-kit into a repository (new or existing) or upgrade it there.
#   ./install.sh [REPO] [--langs python,go,typescript] [--mode strict|ratchet] [--main BRANCH]
#                [--ci] [--upgrade] [--dry-run]
# See README.md. Needs git and Python >= 3.9.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/installer/install.py" "$@"

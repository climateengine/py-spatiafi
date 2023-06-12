#!/usr/bin/env bash
set -eux -o pipefail

# cd to the directory one higher than this script
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

# Get python pkg name from the src dir
python_pkg_slug=$(find src/ -maxdepth 1 -type d | sed -n '2p' | sed 's/^src\///')


pytest \
	--cov="$python_pkg_slug" \
	--cov-fail-under=0

#!/usr/bin/env bash
set -eux -o pipefail

# cd to the directory one higher than this script
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

pip uninstall spfi-api -y || true
pip install -e .[dev] --constraint requirements.txt

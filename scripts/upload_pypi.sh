#!/bin/bash

set -eux -o pipefail

# Build sdist and upload to pypi

rm -rf dist
python -m build
python -m twine upload -r pypi dist/*

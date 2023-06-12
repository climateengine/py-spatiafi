#!/usr/bin/env bash

# cd to the directory one higher than this script
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

# Ensure we are running in a virtual environment
if [ -z "${VIRTUAL_ENV}" ]; then
    echo "Please run this script from within a virtual environment."
    echo "To create a virtual environment, run:"
    echo "    python3 -m venv venv"
    echo "    source venv/bin/activate"
    echo ""
    exit 1
fi

set -eux -o pipefail

# Install some required dev tools
# See https://cloud.google.com/artifact-registry/docs/python/quickstart#installing_the_client_library
# We absolutely need to upgrade pip, or gen_requirements.sh will take _hours_ vs a couple seconds!
pip install --upgrade \
  pip \
  keyring \
  keyrings.google-artifactregistry-auth \
  pip \
  pip-tools \
  setuptools-scm

# If pre-commit is not installed, install it
if ! command -v pre-commit &> /dev/null; then
    pip install pre-commit
fi

# Add https://us-python.pkg.dev/ce-builder/python/ to ~/.pypirc if it is not already there
# See https://cloud.google.com/artifact-registry/docs/python/quickstart#installing_the_client_library
# for more information.
if ! grep -q "us-python.pkg.dev/ce-builder/python" ~/.pypirc; then
    cat << EOF > ~/.pypirc
[distutils]
index-servers =
    us-python.pkg.dev/ce-builder/python

[us-python.pkg.dev/ce-builder/python]
repository: https://us-python.pkg.dev/ce-builder/python/

EOF
fi

scripts/gen_requirements.sh
pip-sync requirements-dev.txt
scripts/install_package.sh
pre-commit install

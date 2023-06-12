#!/usr/bin/env bash

# cd to the directory one higher than this script
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

# Get project name from the name of current directory
project_name=$(basename "$(pwd)")

export DOCKER_BUILDKIT=1

AR_ACCESS_TOKEN=$(gcloud auth print-access-token)
export AR_ACCESS_TOKEN

IMAGE_TAG=$(python -m setuptools_scm | tr + - )

docker build \
  --secret id=AR_ACCESS_TOKEN \
  -t "${1-$project_name}:${IMAGE_TAG}" \
  -t "${1-$project_name}:latest" \
  .

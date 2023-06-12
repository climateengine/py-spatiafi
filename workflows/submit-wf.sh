#!/bin/bash

set -eux -o pipefail

# If kubectl context gke_ce-builder_us-central1_ce-builder does not exist, create it
if ! kubectl config get-contexts gke_ce-builder_us-central1_ce-builder &> /dev/null; then
    gcloud container clusters get-credentials ce-builder --region us-central1 --project ce-builder
fi

# Set the kubectl context to gke_ce-builder_us-central1_ce-builder
kubectl config use-context gke_ce-builder_us-central1_ce-builder

# Ensure Argo CLI is installed locally
if ! command -v argo &> /dev/null; then
    echo "Please install Argo CLI to manually submit workflows."
    echo "See https://argoproj.github.io/argo-workflows/cli/ for more information."
    echo "or https://github.com/argoproj/argo-workflows/releases for the latest release."
    exit 1
fi

argo submit -n argo --log py-spfi-api-build-wf.yaml

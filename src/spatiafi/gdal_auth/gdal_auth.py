"""
Setting up GDAL to authenticate to GCS can be a pain if you don't use a downloaded service account key file,
which is a pretty bad security practice. This module sets up GDAL to authenticate to GCS using the
Google Application Default Credentials (ADC) strategy. This means that if you're running on GCP, GDAL will
authenticate using the instance's service account. If you're running locally, GDAL will authenticate using
the credentials in your local user's Application Default Credentials (ADC) file (usually this is user
credentials from `gcloud auth application-default login`).
"""

import logging
from typing import Dict, Tuple

import google.auth
import google.auth.credentials
import google.auth.transport.requests
import requests

logger = logging.getLogger(__name__)

_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/devstorage.read_write",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/earthengine",
    "openid",
]

_on_gcp = None


def on_gcp():
    global _on_gcp
    if _on_gcp is not None:
        return _on_gcp
    logger.debug("Checking if on GCP")
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/"
    metadata_headers = {"Metadata-Flavor": "Google"}

    try:
        response = requests.head(metadata_url, headers=metadata_headers, timeout=1)

        if response.status_code == requests.codes.ok:
            _on_gcp = True
            return True

    except requests.exceptions.RequestException:
        # Ignore the exception, connection failed means the attribute does not
        # exist in the metadata server.
        pass

    _on_gcp = False
    return False


def get_user_credentials(
    project=None,
) -> Tuple[google.auth.credentials.Credentials, str]:
    """Get or refresh credentials"""
    credentials, project = google.auth.default(
        quota_project_id=project, scopes=_DEFAULT_SCOPES
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials, project


def get_user_auth_env_vars(project=None):
    """Returns a dictionary of environment variables needed for GDAL to auth to GCS"""
    credentials, project = get_user_credentials(project=None)

    return {
        "EEDA_BEARER": credentials.token,
        "GS_OAUTH2_REFRESH_TOKEN": credentials.refresh_token,
        "GS_OAUTH2_CLIENT_ID": credentials.client_id,
        "GS_OAUTH2_CLIENT_SECRET": credentials.client_secret,
    }


def get_gdal_env_vars(project=None) -> Dict[str, str]:
    if on_gcp():
        logger.info("Running on GCP, using instance service account")
        env = {"CPL_MACHINE_IS_GCE": "YES"}
    else:
        logger.info("Running outside GCP, using ADC")
        env = get_user_auth_env_vars(project=project)

    return env

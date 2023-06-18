"""
Setting up GDAL to authenticate to GCS can be a pain if you don't use a downloaded service account key file,
which is a pretty bad security practice. This module sets up GDAL to authenticate to GCS using the
Google Application Default Credentials (ADC) strategy. This means that if you're running on GCP, GDAL will
authenticate using the instance's service account. If you're running locally, GDAL will authenticate using
the credentials in your local user's Application Default Credentials (ADC) file (usually this is user
credentials from `gcloud auth application-default login`).
"""
import json
import logging
import os
from typing import Dict, Tuple

import google.auth
import google.auth.credentials
import google.auth.transport.requests
import requests
from google.oauth2.credentials import Credentials as UserCredentials
from platformdirs import user_config_dir

logger = logging.getLogger(__name__)

_GDAL_SCOPES = [
    "https://www.googleapis.com/auth/devstorage.read_write",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/earthengine",
    "openid",
]

_on_gcp = None

on_gcp_file = os.path.join(
    user_config_dir("spatiafi", ensure_exists=True), "on_gcp.txt"
)

user_credentials_file = os.path.join(
    user_config_dir("spatiafi", ensure_exists=True), "gcp_user_credentials.json"
)


def on_gcp():
    global _on_gcp
    if _on_gcp is not None:
        return _on_gcp

    if os.path.exists(on_gcp_file):
        with open(on_gcp_file, "r") as f:
            _on_gcp = f.read().strip() == "True"
        return _on_gcp

    logger.debug("Checking if on GCP")
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/"
    metadata_headers = {"Metadata-Flavor": "Google"}

    try:
        response = requests.head(metadata_url, headers=metadata_headers, timeout=1)

        if response.status_code == requests.codes.ok:
            with open(on_gcp_file, "w") as f:
                f.write("True")
            _on_gcp = True
            return True

    except requests.exceptions.RequestException:
        # Ignore the exception, connection failed means the attribute does not
        # exist in the metadata server.
        pass

    with open(on_gcp_file, "w") as f:
        f.write("False")
    _on_gcp = False
    return False


def get_user_credentials(
    project=None,
) -> Tuple[google.auth.credentials.Credentials, str]:
    """Get or refresh credentials"""

    if os.path.exists(user_credentials_file):
        with open(user_credentials_file, "r") as f:
            info = json.load(f)

        quota_project_id = info.get("quota_project_id", None)
        credentials = UserCredentials.from_authorized_user_info(
            info=info, scopes=_GDAL_SCOPES
        )

        if project and project != quota_project_id:
            credentials = credentials.with_quota_project(quota_project_id=project)
        if credentials.expired:
            credentials.refresh(google.auth.transport.requests.Request())
        return credentials, project

    credentials, project = google.auth.default(
        quota_project_id=project, scopes=_GDAL_SCOPES
    )
    credentials.refresh(
        google.auth.transport.requests.Request()
    )  # need to call once to get token

    if isinstance(credentials, UserCredentials):
        with open(user_credentials_file, "w") as f:
            credentials_dict = json.loads(credentials.to_json())
            if project:
                credentials_dict["quota_project_id"] = project
            f.write(json.dumps(credentials_dict))

    return credentials, project


def get_user_auth_env_vars(project=None):
    """Returns a dictionary of environment variables needed for GDAL to auth to GCS"""
    credentials, project = get_user_credentials(project=project)

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


def get_credentials(project=None) -> Tuple[google.auth.credentials.Credentials, str]:
    if on_gcp():
        return google.auth.default(quota_project_id=project)
    else:
        return get_user_credentials(project=project)


if __name__ == "__main__":
    import pprint

    pprint.pprint(get_gdal_env_vars())

import getpass
import json
import os

import requests
from platformdirs import user_config_dir

app_credentials_file = os.path.join(
    user_config_dir("spatiafi", ensure_exists=True), "app_credentials.json"
)


def get_basic_auth_token(username, password):
    """Get an access token using HTTP Basic Authentication."""
    url = "https://auth.spatiafi.com/api/v1/auth/jwt/token/basic"
    response = requests.get(url, auth=(username, password))
    response_data = response.json()
    return response_data["access_token"]


def prompt_for_basic_auth_token():
    """Prompt for username and password and get an access token using HTTP Basic Authentication."""
    print(
        "SpatiaFi App Credentials not found. Please authenticate to get new credentials."
    )
    print(
        "Note: You can also set the environment variables SPATIAFI_CLIENT_ID and SPATIAFI_CLIENT_SECRET."
    )
    print("")
    print("Enter your SpatiaFi username and password:")
    username = input("Username: ")
    password = getpass.getpass()
    token = get_basic_auth_token(username, password)
    return token


def get_new_app_credentials(access_token=None):
    """Get new app credentials from the SpatiaFI Auth API."""

    if access_token is None:
        access_token = prompt_for_basic_auth_token()

    headers = {"Authorization": "Bearer " + access_token}

    response = requests.post(
        "https://auth.spatiafi.com/api/v1/clients/", headers=headers
    )
    response_data = response.json()
    store_app_credentials(response_data)
    print(f"Got new App Credentials and saved them to: {app_credentials_file}")
    return response_data


def store_app_credentials(app_credentials):
    """Store app credentials to a file."""
    with open(app_credentials_file, "w") as f:
        json.dump(app_credentials, f)


def load_app_credentials_from_file():
    """Load app credentials from a file."""
    with open(app_credentials_file, "r") as f:
        app_credentials = json.load(f)
    return app_credentials


def load_app_credentials_into_env(app_credentials):
    """Load SpatiaFI app credentials into environment variables."""
    os.environ["SPATIAFI_CLIENT_ID"] = app_credentials["client_id"]
    os.environ["SPATIAFI_CLIENT_SECRET"] = app_credentials["client_secret"]


def authenticate():
    """Try to load app credentials from env var, or disk, otherwise get new app credentials."""
    if os.environ.get("SPATIAFI_CLIENT_ID") and os.environ.get(
        "SPATIAFI_CLIENT_SECRET"
    ):
        return {
            "client_id": os.environ["SPATIAFI_CLIENT_ID"],
            "client_secret": os.environ["SPATIAFI_CLIENT_SECRET"],
        }
    try:
        app_credentials = load_app_credentials_from_file()
    except FileNotFoundError:
        app_credentials = get_new_app_credentials()
    load_app_credentials_into_env(app_credentials)
    return app_credentials


if __name__ == "__main__":
    authenticate()

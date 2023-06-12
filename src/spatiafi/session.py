import os

from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7523 import ClientSecretJWT

from spatiafi import authenticate


def get_session(app_credentials=None):
    """Get an automatically-refreshing OAuth2 session for the SpatiaFI API."""

    if app_credentials is not None:
        client_id = app_credentials["client_id"]
        client_secret = app_credentials["client_secret"]

    elif os.environ.get("SPATIAFI_CLIENT_ID") and os.environ.get(
        "SPATIAFI_CLIENT_SECRET"
    ):
        client_id = os.environ["SPATIAFI_CLIENT_ID"]
        client_secret = os.environ["SPATIAFI_CLIENT_SECRET"]

    else:
        app_credentials = authenticate()
        client_id = app_credentials["client_id"]
        client_secret = app_credentials["client_secret"]

    client = OAuth2Session(
        client_id,
        client_secret,
        token_endpoint="https://auth.spatiafi.com/api/v1/auth/jwt/token",
        grant_type="client_credentials",
        token_endpoint_auth_method=ClientSecretJWT(
            "https://auth.spatiafi.com/api/v1/auth/jwt/token"
        ),
    )
    client.fetch_token()
    return client

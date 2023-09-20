import os

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7523 import ClientSecretJWT

from spatiafi import authenticate


def load_or_authenticate():
    """Load credentials from environment variables or authenticate to get them."""
    if os.environ.get("SPATIAFI_CLIENT_ID") and os.environ.get(
        "SPATIAFI_CLIENT_SECRET"
    ):
        return {
            "client_id": os.environ["SPATIAFI_CLIENT_ID"],
            "client_secret": os.environ["SPATIAFI_CLIENT_SECRET"],
        }
    else:
        return authenticate()


def get_session(app_credentials=None):
    """
    Get an automatically-refreshing OAuth2 session (requests, sync) for the SpatiaFI API.

    If app_credentials are provided, they should be a dict with keys "client_id" and "client_secret".
    If app_credentials are not provided,

      * First attempt to load them from the environment variables SPATIAFI_CLIENT_ID and SPATIAFI_CLIENT_SECRET
      * Check if they are stored in the default location ~/.spatiafi/app_credentials.json
      * If not, authenticate to get new app credentials and store them in the default location
    """

    if app_credentials is None:
        app_credentials = load_or_authenticate()

    client_id = app_credentials["client_id"]
    client_secret = app_credentials["client_secret"]

    session = OAuth2Session(
        client_id,
        client_secret,
        token_endpoint="https://auth.spatiafi.com/api/v1/auth/jwt/token",
        grant_type="client_credentials",
        token_endpoint_auth_method=ClientSecretJWT(
            "https://auth.spatiafi.com/api/v1/auth/jwt/token"
        ),
    )
    session.fetch_token()
    return session


async def get_async_session(app_credentials=None):
    """
    Get an automatically-refreshing async OAuth2 session for the SpatiaFI API.

    If app_credentials are provided, they should be a dict with keys "client_id" and "client_secret".
    If app_credentials are not provided,

      * First attempt to load them from the environment variables SPATIAFI_CLIENT_ID and SPATIAFI_CLIENT_SECRET
      * Check if they are stored in the default location ~/.spatiafi/app_credentials.json
      * If not, authenticate to get new app credentials and store them in the default location
    """

    if app_credentials is None:
        app_credentials = load_or_authenticate()

    client_id = app_credentials["client_id"]
    client_secret = app_credentials["client_secret"]

    session = AsyncOAuth2Client(
        client_id,
        client_secret,
        token_endpoint="https://auth.spatiafi.com/api/v1/auth/jwt/token",
        grant_type="client_credentials",
        token_endpoint_auth_method=ClientSecretJWT(
            "https://auth.spatiafi.com/api/v1/auth/jwt/token"
        ),
        limits=httpx.Limits(max_connections=None),
        timeout=httpx.Timeout(5.0),
        transport=httpx.AsyncHTTPTransport(retries=3),
    )
    await session.fetch_token()
    return session


if __name__ == "__main__":
    get_session()

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7523 import ClientSecretJWT
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from spatiafi import authenticate


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
        app_credentials = authenticate()

    client_id = app_credentials["client_id"]
    client_secret = app_credentials["client_secret"]

    # Define the retry strategy
    retry_strategy = Retry(
        total=3,  # Maximum number of retries
        status_forcelist=[500, 502, 503, 504],  # HTTP status codes to retry on
    )
    # Create an HTTP adapter with the retry strategy and mount it to session
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # Create a new session object
    session = OAuth2Session(
        client_id,
        client_secret,
        token_endpoint="https://auth.spatiafi.com/api/v1/auth/jwt/token",
        grant_type="client_credentials",
        token_endpoint_auth_method=ClientSecretJWT(
            "https://auth.spatiafi.com/api/v1/auth/jwt/token"
        ),
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
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
        app_credentials = authenticate()

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

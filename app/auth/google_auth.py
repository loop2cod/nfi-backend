from authlib.integrations.base_client import OAuthError
from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.core.config import settings


def get_google_oauth_client():
    return AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


async def get_google_user_info(access_token: str):
    async with AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token={"access_token": access_token, "token_type": "Bearer"},
    ) as client:
        resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo")
        resp.raise_for_status()
        return resp.json()
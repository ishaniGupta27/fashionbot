# YouTube API Refresh Token Guide

Use this guide whenever you need to regenerate the YouTube API refresh token for
Fashionbot.

## Quick Links

- Google Cloud Console: https://console.cloud.google.com/
- OAuth 2.0 Playground: https://developers.google.com/oauthplayground

## One-Time Cloud Console Check

1. Open the Google Cloud project that owns your OAuth client.
2. Make sure **YouTube Data API v3** is enabled.
3. Open **OAuth consent screen**.
4. Add your Google account as a test user if the app is still in testing mode.
5. Open **Credentials**.
6. Open your OAuth 2.0 client.
7. Confirm **Authorized redirect URIs** contains:

```text
https://developers.google.com/oauthplayground
```

If the app stays in testing mode, Google may expire refresh tokens periodically.
If you want longer-lived tokens, move the app to production when your consent
screen is ready.

## Generate A New Refresh Token

1. Open https://developers.google.com/oauthplayground.
2. Click the settings gear in the top-right corner.
3. Check **Use your own OAuth credentials**.
4. Paste your OAuth client id and client secret.
5. Close settings.
6. In **Step 1**, paste this scope:

```text
https://www.googleapis.com/auth/youtube.upload
```

7. Click **Authorize APIs**.
8. Sign in with the Google account that owns or manages the target YouTube
   channel.
9. If Google shows an unverified-app warning, click **Advanced**, continue to
   your app, and allow access.
10. In **Step 2**, click **Exchange authorization code for tokens**.
11. Copy the `refresh_token` from the JSON response.

## Save Locally

Put the token in:

```text
secrets/fashionbot.secrets.json
```

```json
{
  "YOUTUBE_CLIENT_ID": "your-client-id",
  "YOUTUBE_CLIENT_SECRET": "your-client-secret",
  "YOUTUBE_REFRESH_TOKEN": "your-refresh-token"
}
```

## Save In GitHub Actions

Add or update this repository secret:

```text
YOUTUBE_REFRESH_TOKEN
```

The client id and client secret also belong in GitHub Actions secrets:

```text
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
```

## Validate

Run:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.validate_secrets --youtube
```

Expected success:

```text
OK YOUTUBE_CLIENT_ID: present
OK YOUTUBE_CLIENT_SECRET: present
OK YOUTUBE_REFRESH_TOKEN: present
OK YouTube refresh token exchanged: present
DONE secrets validation
```

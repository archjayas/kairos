# Use your real Google Calendar

By default, events go to a mock calendar that only prints them. This guide connects
the agents to your primary Google Calendar.

> Events created this way are real and **send invites to the attendees**. The
> confirmation step still applies: nothing is created without `y`.

## 1. Install the Google client libraries

These are already in `requirements.txt`. If you installed manually, run:

```bash
pip install google-api-python-client google-auth-oauthlib
```

## 2. Create an OAuth client

1. In the [Google Cloud console](https://console.cloud.google.com), create or pick a
   project.
2. Enable the **Google Calendar API** for that project.
3. Configure the **OAuth consent screen**. For personal use, choose **External** and
   add your own Google account as a **test user**.
4. Under **Credentials**, create an **OAuth client ID** of type **Desktop app**.
5. Download the JSON file and save it as `credentials.json` in the folder you run
   Kairos from (the repo root, in these docs).

`credentials.json` is git-ignored. Never commit it or paste its contents anywhere.

## 3. Switch the backend

```bash
export CALENDAR_BACKEND=google
python claude_agent.py
```

The first time, a browser window asks you to grant access to your calendar. After you
approve, a `token.json` is saved in the folder you run from, so you won't be asked
again until the token expires or is revoked. `token.json` is also git-ignored.

The app asks only for the `calendar.events` scope: it can create and edit events, not
change your calendar settings.

## Keep the files somewhere else

To keep credentials outside the repo, point to them with environment variables:

```bash
export GOOGLE_CREDENTIALS_FILE="$HOME/.config/kairos/credentials.json"
export GOOGLE_TOKEN_FILE="$HOME/.config/kairos/token.json"
```

## Go back to the mock

```bash
export CALENDAR_BACKEND=mock     # or: unset CALENDAR_BACKEND
```

## Revoke access

Remove the app at [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
and delete `token.json`.

## Related

- [Troubleshooting: Google Calendar](../troubleshooting.md#google-calendar)
- [Change your timezone](change-timezone.md)
- [Use Kairos over MCP](use-mcp.md) (works with the real calendar too)

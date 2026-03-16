#!/usr/bin/env python3
"""
Fetch a Google Doc template by its document ID.
Usage: python3 fetch_template.py <google_doc_id>

Returns the plain-text content of the template to stdout.
Requires: Google Drive OAuth token in macOS keychain (mcp_google_drive / oauth_token_gdrive)
          and GOOGLE_DRIVE_OAUTH_CONFIG in Goose secrets (goose / secrets).
"""

import json
import subprocess
import sys
import urllib.request
import urllib.parse
import urllib.error


def get_access_token():
    """Refresh and return a valid Google Drive access token."""
    # Get stored token
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "mcp_google_drive", "-a", "oauth_token_gdrive", "-w"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("No Google Drive OAuth token found in keychain.")
    token_data = json.loads(result.stdout.strip())

    # Get OAuth config from Goose secrets
    result2 = subprocess.run(
        ["security", "find-generic-password", "-s", "goose", "-a", "secrets", "-w"],
        capture_output=True, text=True
    )
    if result2.returncode != 0:
        raise RuntimeError("No Goose secrets found in keychain.")
    secrets = json.loads(result2.stdout.strip())
    oauth_config = json.loads(secrets["GOOGLE_DRIVE_OAUTH_CONFIG"])
    installed = oauth_config.get("installed", oauth_config.get("web", {}))

    # Refresh the token
    refresh_data = urllib.parse.urlencode({
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request(installed["token_uri"], data=refresh_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode())["access_token"]


def fetch_template(doc_id, access_token):
    """Export a Google Doc as plain text."""
    url = f"https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    resp = urllib.request.urlopen(req)
    return resp.read().decode("utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_template.py <google_doc_id>", file=sys.stderr)
        sys.exit(1)

    doc_id = sys.argv[1]
    try:
        token = get_access_token()
        content = fetch_template(doc_id, token)
        print(content)
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} — {e.reason}", file=sys.stderr)
        print(e.read().decode(), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

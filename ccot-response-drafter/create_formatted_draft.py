#!/usr/bin/env python3
"""
create_formatted_draft.py — Create a fully formatted Google Doc draft response
by copying the selected template and replacing ZZZ placeholders in-place.

This preserves ALL formatting from the original template:
- Cash App logo in header
- Montserrat font (11pt body, 10pt footnotes)
- Bold/italic/underline styling on each placeholder
- Page margins, line spacing, indentation
- Footer (1955 Broadway, Suite 600 / Oakland, CA 94612)
- Footnotes with approved definitions
- Section headers (I. Introduction, II. Your Complaint, etc.)

Usage:
    python3 create_formatted_draft.py <TEMPLATE_DOC_ID> <REPLACEMENTS_JSON_FILE> [--folder-id ID] [--folder-url URL]

Arguments:
    TEMPLATE_DOC_ID         Google Doc ID of the template to copy
    REPLACEMENTS_JSON_FILE  Path to a JSON file with placeholder replacements

Options:
    --folder-id ID          Google Drive folder ID to place the draft in
    --folder-url URL        Google Drive folder URL (folder ID will be extracted)
                            Supports formats:
                              https://drive.google.com/drive/folders/FOLDER_ID
                              https://drive.google.com/drive/u/0/folders/FOLDER_ID

    If neither --folder-id nor --folder-url is provided, the script checks the
    replacements JSON for a "destination_folder_id" or "destination_folder_url" field.
    If none are found, the draft is created in the authenticated user's My Drive root.

The replacements JSON file should have this structure:
{
    "document_title": "CFPB 240115-9876543 - Jane Doe - Response Draft",
    "destination_folder_id": "1AbCdEfGhIjKlMnOpQrStUvWxYz",
    "destination_folder_url": "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz",
    "replacements": {
        "ZZZDATEZZZ": "March 16, 2026",
        "ZZZNameZZZ": "Jane Doe",
        ...
    },
    "sections_to_replace": { ... },
    "optional_sections_to_remove": [ ... ],
    "optional_sections_to_keep": [ ... ]
}

Output:
    Prints the URL of the new draft document to stdout.
    Prints status messages to stderr.
"""

import json
import subprocess
import sys
import os
import re
import argparse


def extract_folder_id_from_url(url):
    """Extract a Google Drive folder ID from various URL formats.
    
    Supports:
        https://drive.google.com/drive/folders/FOLDER_ID
        https://drive.google.com/drive/folders/FOLDER_ID?...
        https://drive.google.com/drive/u/0/folders/FOLDER_ID
        https://drive.google.com/open?id=FOLDER_ID
    """
    if not url:
        return None

    # Pattern 1: /folders/FOLDER_ID
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    # Pattern 2: ?id=FOLDER_ID
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    return None


def get_token():
    """Get a fresh OAuth token from the macOS keychain, refreshing if needed."""
    result = subprocess.run(
        ['security', 'find-generic-password', '-s', 'mcp_google_drive',
         '-a', 'oauth_token_gdrive', '-w'],
        capture_output=True, text=True
    )
    token_data = json.loads(result.stdout.strip())
    token = token_data.get('token', '')

    # Check if token is still valid
    import urllib.request
    req = urllib.request.Request(
        'https://www.googleapis.com/drive/v3/about?fields=user',
        headers={'Authorization': f'Bearer {token}'}
    )
    try:
        urllib.request.urlopen(req)
        return token
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return refresh_token(token_data)
        raise


def refresh_token(token_data):
    """Refresh the OAuth token using the refresh_token."""
    result = subprocess.run(
        ['security', 'find-generic-password', '-s', 'goose',
         '-a', 'secrets', '-w'],
        capture_output=True, text=True
    )
    secrets = json.loads(result.stdout.strip())
    oauth_config = json.loads(secrets.get('GOOGLE_DRIVE_OAUTH_CONFIG', '{}'))
    client_config = oauth_config.get('installed', {})

    import urllib.request
    import urllib.parse

    data = urllib.parse.urlencode({
        'client_id': client_config['client_id'],
        'client_secret': client_config['client_secret'],
        'refresh_token': token_data['refresh_token'],
        'grant_type': 'refresh_token'
    }).encode()

    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    resp = urllib.request.urlopen(req)
    new_tokens = json.loads(resp.read().decode())

    new_token = new_tokens['access_token']

    token_data['token'] = new_token
    subprocess.run(
        ['security', 'add-generic-password', '-s', 'mcp_google_drive',
         '-a', 'oauth_token_gdrive', '-w', json.dumps(token_data), '-U'],
        capture_output=True, text=True
    )

    return new_token


def api_request(method, url, token, body=None):
    """Make a Google API request."""
    import urllib.request
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)


def verify_folder_access(token, folder_id):
    """Verify the folder exists and we have write access. Returns folder name or None."""
    try:
        result = api_request(
            'GET',
            f'https://www.googleapis.com/drive/v3/files/{folder_id}?fields=id,name,mimeType,capabilities&supportsAllDrives=true',
            token
        )
        mime = result.get('mimeType', '')
        if mime != 'application/vnd.google-apps.folder':
            print(f"WARNING: {folder_id} is not a folder (type: {mime})", file=sys.stderr)
            return None
        can_edit = result.get('capabilities', {}).get('canEdit', False)
        can_add = result.get('capabilities', {}).get('canAddChildren', False)
        if not (can_edit or can_add):
            print(f"WARNING: No write access to folder '{result.get('name')}'", file=sys.stderr)
            return None
        return result.get('name')
    except SystemExit:
        print(f"WARNING: Could not access folder {folder_id}", file=sys.stderr)
        return None


def copy_template(token, template_id, title, folder_id=None):
    """Copy a Google Doc template, preserving all formatting.
    
    If folder_id is provided, the copy is created directly in that folder.
    Otherwise, it is created in the authenticated user's My Drive root.
    """
    body = {"name": title}
    if folder_id:
        body["parents"] = [folder_id]

    result = api_request(
        'POST',
        f'https://www.googleapis.com/drive/v3/files/{template_id}/copy?supportsAllDrives=true',
        token,
        body
    )
    return result['id']


def replace_placeholders(token, doc_id, replacements):
    """Replace ZZZ placeholders in the copied doc using batchUpdate.
    
    The replacement text inherits the exact formatting of the placeholder
    it replaces — font, size, bold, italic, underline, color, etc.
    """
    requests = []
    for placeholder, replacement in replacements.items():
        requests.append({
            "replaceAllText": {
                "containsText": {
                    "text": placeholder,
                    "matchCase": True
                },
                "replaceText": replacement
            }
        })

    if requests:
        result = api_request(
            'POST',
            f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
            token,
            {"requests": requests}
        )
        return result
    return None


def remove_optional_sections(token, doc_id, sections_to_remove):
    """Remove ZZZZ-delimited optional sections from the document."""
    if not sections_to_remove:
        return

    requests = []
    for section_text in sections_to_remove:
        requests.append({
            "replaceAllText": {
                "containsText": {
                    "text": section_text,
                    "matchCase": False
                },
                "replaceText": ""
            }
        })

    if requests:
        api_request(
            'POST',
            f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
            token,
            {"requests": requests}
        )


def clean_option_markers(token, doc_id, sections_to_keep):
    """Remove ZZZZ option markers from kept sections, leaving just the content."""
    if not sections_to_keep:
        return

    requests = []
    for section_text in sections_to_keep:
        inner = section_text.strip()
        if inner.startswith("ZZZZ"):
            inner = inner[4:]
        if inner.endswith("ZZZZ"):
            inner = inner[:-4]
        inner = inner.strip()

        requests.append({
            "replaceAllText": {
                "containsText": {
                    "text": section_text,
                    "matchCase": False
                },
                "replaceText": inner
            }
        })

    if requests:
        api_request(
            'POST',
            f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
            token,
            {"requests": requests}
        )


def main():
    parser = argparse.ArgumentParser(
        description='Create a formatted Google Doc draft from a CCOT template'
    )
    parser.add_argument('template_id', help='Google Doc ID of the template to copy')
    parser.add_argument('replacements_file', help='Path to JSON file with replacements')
    parser.add_argument('--folder-id', help='Google Drive folder ID for the draft')
    parser.add_argument('--folder-url', help='Google Drive folder URL for the draft')
    args = parser.parse_args()

    # Load replacements config
    with open(args.replacements_file) as f:
        config = json.load(f)

    title = config.get('document_title', 'Draft Response')
    replacements = config.get('replacements', {})
    sections_replace = config.get('sections_to_replace', {})
    sections_remove = config.get('optional_sections_to_remove', [])
    sections_keep = config.get('optional_sections_to_keep', [])

    # Resolve destination folder ID (priority: CLI args > JSON config)
    folder_id = None

    if args.folder_id:
        folder_id = args.folder_id
        print(f"Destination folder (from --folder-id): {folder_id}", file=sys.stderr)
    elif args.folder_url:
        folder_id = extract_folder_id_from_url(args.folder_url)
        if folder_id:
            print(f"Destination folder (from --folder-url): {folder_id}", file=sys.stderr)
        else:
            print(f"WARNING: Could not extract folder ID from URL: {args.folder_url}", file=sys.stderr)
    elif config.get('destination_folder_id'):
        folder_id = config['destination_folder_id']
        print(f"Destination folder (from JSON config): {folder_id}", file=sys.stderr)
    elif config.get('destination_folder_url'):
        folder_id = extract_folder_id_from_url(config['destination_folder_url'])
        if folder_id:
            print(f"Destination folder (from JSON config URL): {folder_id}", file=sys.stderr)
        else:
            print(f"WARNING: Could not extract folder ID from config URL: {config['destination_folder_url']}", file=sys.stderr)

    # Merge all replacements
    all_replacements = {**replacements, **sections_replace}

    # Get token
    token = get_token()

    # Verify folder access if we have a folder ID
    if folder_id:
        folder_name = verify_folder_access(token, folder_id)
        if folder_name:
            print(f"Verified write access to folder: \"{folder_name}\"", file=sys.stderr)
        else:
            print(f"WARNING: Cannot write to folder {folder_id}. Draft will be created in My Drive.", file=sys.stderr)
            folder_id = None
    else:
        print("No destination folder specified. Draft will be created in My Drive.", file=sys.stderr)

    # Step 1: Copy the template
    print(f"Copying template {args.template_id}...", file=sys.stderr)
    new_doc_id = copy_template(token, args.template_id, title, folder_id)
    print(f"Created draft document: {new_doc_id}", file=sys.stderr)

    # Step 2: Replace all ZZZ placeholders
    if all_replacements:
        print(f"Replacing {len(all_replacements)} placeholder(s)...", file=sys.stderr)
        result = replace_placeholders(token, new_doc_id, all_replacements)
        if result:
            total = sum(
                r.get('replaceAllText', {}).get('occurrencesChanged', 0)
                for r in result.get('replies', [])
            )
            print(f"Replaced {total} occurrence(s) across document", file=sys.stderr)

    # Step 3: Remove optional sections that don't apply
    if sections_remove:
        print(f"Removing {len(sections_remove)} optional section(s)...", file=sys.stderr)
        remove_optional_sections(token, new_doc_id, sections_remove)

    # Step 4: Clean ZZZZ markers from kept sections
    if sections_keep:
        print(f"Cleaning {len(sections_keep)} kept section marker(s)...", file=sys.stderr)
        clean_option_markers(token, new_doc_id, sections_keep)

    # Output results
    doc_url = f"https://docs.google.com/document/d/{new_doc_id}/edit"
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else "My Drive (root)"

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Draft created successfully!", file=sys.stderr)
    print(f"  Document: {doc_url}", file=sys.stderr)
    print(f"  Location: {folder_url}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Print just the URL to stdout for programmatic use
    print(doc_url)


if __name__ == '__main__':
    main()

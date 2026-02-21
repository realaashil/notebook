"""Shared configuration and helpers for OAuth scope test scripts and app creation."""
import os
import time
import requests

# --- Configuration (from environment) ---
ADMIN_JWT_TOKEN = os.getenv('ADMIN_JWT_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:3000').rstrip('/')


def get_org_id():
    """Fetches the Organization ID from the backend. Returns None on failure (no print)."""
    if not ADMIN_JWT_TOKEN:
        return None
    try:
        url = f"{BACKEND_URL}/api/v1/org"
        headers = {"Authorization": f"Bearer {ADMIN_JWT_TOKEN}"}
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        return data.get("id") or data.get("_id")
    except requests.exceptions.RequestException:
        return None


def get_org_context():
    """Fetches the Organization ID needed for multi-tenant API calls. Prints and raises on failure."""
    print("🏢 [Setup] Fetching Organization context...")
    org_id = get_org_id()
    if not org_id:
        raise Exception("Could not find Organization ID in response.")
    return org_id


def get_app_internal_id():
    """Finds the internal UUID for the given Client ID using Admin access."""
    url = f"{BACKEND_URL}/api/v1/oauth-clients"
    headers = {"Authorization": f"Bearer {ADMIN_JWT_TOKEN}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()

    apps_list = res.json().get('data', res.json()) if isinstance(res.json(), dict) else res.json()
    for app in apps_list:
        if app.get('clientId') == CLIENT_ID:
            return app.get('id') or app.get('_id')
    raise Exception(f"App with Client ID {CLIENT_ID} not found on server.")


def update_remote_app_config(app_uuid, scopes):
    """Updates the allowedScopes on the server via PUT."""
    print(f"🛠️  [Admin] Updating app allowedScopes: {scopes}")
    url = f"{BACKEND_URL}/api/v1/oauth-clients/{app_uuid}"
    headers = {
        "Authorization": f"Bearer {ADMIN_JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "allowedScopes": scopes + ["offline_access", "openid"],
        "allowedGrantTypes": ["authorization_code", "refresh_token", "client_credentials"]
    }
    res = requests.put(url, json=payload, headers=headers)
    res.raise_for_status()
    return True


def get_fresh_token(requested_scopes):
    """Requests a brand new Access Token for the client."""
    url = f"{BACKEND_URL}/api/v1/oauth2/token"
    scope_str = " ".join(sorted(list(set(requested_scopes + ["offline_access"]))))

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": scope_str
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    res = requests.post(url, data=data, headers=headers)
    if res.status_code != 200:
        print(f"🛑 Token Request Failed: {res.text}")
        return None

    return res.json().get('access_token')


def verify_endpoint(token, test_config, org_id):
    """Hits the target API using the token and the Organization context."""
    url = f"{BACKEND_URL}{test_config['path']}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-org-id": org_id,
        "Content-Type": "application/json"
    }
    method = test_config.get('method', 'GET')
    body = test_config.get('body')

    try:
        if method == 'POST':
            res = requests.post(url, headers=headers, json=body)
        elif method == 'PUT':
            res = requests.put(url, headers=headers, json=body)
        else:
            res = requests.get(url, headers=headers)
        return res.status_code, res.text
    except Exception as e:
        return 500, str(e)


def run_scope_tests(test_suite):
    """
    Runs the sequential scope test cycle: for each test in test_suite,
    updates app scopes, gets a token, and verifies the endpoint.
    """
    if not all([ADMIN_JWT_TOKEN, CLIENT_ID, CLIENT_SECRET]):
        print("❌ Error: Missing environment variables. Please set ADMIN_JWT_TOKEN, CLIENT_ID, and CLIENT_SECRET.")
        return

    try:
        org_id = get_org_context()
        app_uuid = get_app_internal_id()
        print(f"✅ Context ready. Org: {org_id} | App Internal ID: {app_uuid}")

        active_scopes = []
        last_token = None

        for test in test_suite:
            print(f"\n" + "=" * 50)
            print(f"🚀 TESTING SCOPE: {test['scope']}")
            print("=" * 50)

            active_scopes.append(test['scope'])
            update_remote_app_config(app_uuid, active_scopes)

            print("⏳ Waiting for server-side cache to refresh...")
            time.sleep(2)

            new_token = get_fresh_token(active_scopes)
            if not new_token:
                print("⏭️ Skipping test - Could not get token.")
                continue

            if new_token == last_token:
                print("⚠️ Warning: Received the same token as the previous step. Server might be caching.")
            else:
                print("🔑 Fresh token generated.")
            last_token = new_token

            status, response_text = verify_endpoint(new_token, test, org_id)

            if 200 <= status < 300:
                print(f"✨ SUCCESS: Access GRANTED to {test['path']} (Status: {status})")
            elif status in [401, 403]:
                print(f"🚫 DENIED: Scope '{test['scope']}' was not recognized by the backend (Status: {status})")
            else:
                print(f"🛑 ERROR: Server returned Status {status}")
                print(f"📝 Detail: {response_text[:200]}")

            time.sleep(0.5)

        print("\n" + "=" * 50)
        print("🏁 Full Test Cycle Completed.")
        print("=" * 50)

    except Exception as e:
        print(f"💥 Runtime Failure: {e}")

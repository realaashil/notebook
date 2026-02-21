"""Shared configuration and helpers for OAuth scope test scripts and app creation."""
import os
import time
import secrets
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# --- Configuration (from environment) ---
ADMIN_JWT_TOKEN = os.getenv('ADMIN_JWT_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:3000').rstrip('/')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8888/callback').rstrip('/')


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


# --- User-delegated (authorization code) flow ---

def build_authorize_url(scopes, state=None):
    """Build the OAuth2 authorize URL for user consent. User must be logged in (e.g. in browser)."""
    if state is None:
        state = secrets.token_urlsafe(16)
    scope_str = " ".join(sorted(list(set(scopes + ["offline_access", "openid"]))))
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": scope_str,
        "state": state,
    }
    return f"{BACKEND_URL}/api/v1/oauth2/authorize?{urllib.parse.urlencode(params)}", state


def _run_callback_server(state, timeout=300):
    """
    Start a one-shot HTTP server to receive the redirect with ?code=...&state=...
    Returns (code, state) or (None, None) on error/timeout.
    """
    parsed = urlparse(REDIRECT_URI)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path

    result = {"code": None, "state": None, "error": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if "?" in self.path:
                req_path, qs = self.path.split("?", 1)
            else:
                req_path, qs = self.path, ""
            if req_path != path and req_path != path.rstrip("/"):
                self.send_response(404)
                self.end_headers()
                return
            params = parse_qs(qs)
            result["code"] = (params.get("code") or [None])[0]
            result["state"] = (params.get("state") or [None])[0]
            result["error"] = (params.get("error") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if result["error"]:
                body = f"<p>Authorization failed: {result['error']}</p><p>You can close this window.</p>"
            else:
                body = "<p>Authorization successful. You can close this window and return to the script.</p>"
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = HTTPServer((host, port), CallbackHandler)
    server.timeout = 1
    deadline = time.time() + timeout
    while time.time() < deadline and result["code"] is None and result["error"] is None:
        server.handle_request()
    return result.get("code"), result.get("state"), result.get("error")


def exchange_code_for_token(code, redirect_uri=None):
    """Exchange authorization code for access token (and optionally refresh token)."""
    url = f"{BACKEND_URL}/api/v1/oauth2/token"
    redirect = redirect_uri or REDIRECT_URI
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url, data=data, headers=headers)
    if res.status_code != 200:
        print(f"🛑 Token exchange failed: {res.text}")
        return None
    return res.json()


def get_token_via_user_consent(scopes, open_browser=True):
    """
    Run the user-delegated OAuth flow: build authorize URL, optionally open browser,
    run local callback server to receive code, exchange for token.
    Returns access_token (and stores refresh_token in returned dict if present).
    """
    authorize_url, state = build_authorize_url(scopes)
    print("🌐 Open this URL in your browser (log in and approve consent if needed):")
    print(f"   {authorize_url}")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(authorize_url)
        except Exception as e:
            print(f"   (Could not open browser: {e})")
    print(f"\n⏳ Waiting for callback on {REDIRECT_URI} (approve in browser)...")
    code, state_back, error = _run_callback_server(state)
    if error:
        print(f"🛑 Authorization denied or error: {error}")
        return None
    if not code:
        print("🛑 No authorization code received (timeout or no callback).")
        return None
    token_data = exchange_code_for_token(code)
    if not token_data:
        return None
    access = token_data.get("access_token")
    if access:
        print("🔑 User-delegated access token obtained.")
    if token_data.get("refresh_token"):
        print("   (Refresh token also received.)")
    return token_data


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


def run_scope_tests(test_suite, use_user_delegated=False):
    """
    Runs the scope test cycle.

    - use_user_delegated=False (default): client_credentials flow per scope (no user interaction).
    - use_user_delegated=True: one user consent for all scopes, then run tests with that token.
      Requires REDIRECT_URI to be registered for your app (e.g. http://localhost:8888/callback).
    """
    if not all([ADMIN_JWT_TOKEN, CLIENT_ID, CLIENT_SECRET]):
        print("❌ Error: Missing environment variables. Please set ADMIN_JWT_TOKEN, CLIENT_ID, and CLIENT_SECRET.")
        return

    try:
        org_id = get_org_context()
        app_uuid = get_app_internal_id()
        print(f"✅ Context ready. Org: {org_id} | App Internal ID: {app_uuid}")

        if use_user_delegated:
            # Collect all scopes, update app once, get one user-delegated token
            all_scopes = list(dict.fromkeys(t["scope"] for t in test_suite))
            update_remote_app_config(app_uuid, all_scopes)
            print("⏳ Waiting for server-side config to refresh...")
            time.sleep(2)
            print("\n👤 User-delegated flow: you will be asked to approve access in the browser.\n")
            token_data = get_token_via_user_consent(all_scopes, open_browser=True)
            if not token_data:
                print("💥 Could not obtain user-delegated token. Aborting.")
                return
            user_token = token_data.get("access_token")
            if not user_token:
                print("💥 No access_token in response. Aborting.")
                return
            # Run all tests with the same token
            for test in test_suite:
                print(f"\n" + "=" * 50)
                print(f"🚀 TESTING SCOPE: {test['scope']}")
                print("=" * 50)
                status, response_text = verify_endpoint(user_token, test, org_id)
                if 200 <= status < 300:
                    print(f"✨ SUCCESS: Access GRANTED to {test['path']} (Status: {status})")
                elif status in [401, 403]:
                    print(f"🚫 DENIED (Status: {status})")
                else:
                    print(f"🛑 ERROR: Server returned Status {status}")
                    print(f"📝 Detail: {response_text[:200]}")
                time.sleep(0.5)
        else:
            # Original: client_credentials, one token per scope step
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

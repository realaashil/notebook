import argparse
import requests
from datetime import datetime

from common import ADMIN_JWT_TOKEN, BACKEND_URL, get_org_id

# --- App Definitions Mapping (Based on your provided scope list) ---
APP_SCHEMAS = {
    "mgmt": {
        "name": "Identity & Org Management",
        "description": "Full access to Org, Users, Teams, and UserGroups.",
        "allowedScopes": [
            "org:read", "org:write", "org:admin",
            "user:read", "user:write", "user:invite", "user:delete",
            "usergroup:read", "usergroup:write",
            "team:read", "team:write",
            "openid", "profile", "email", "offline_access"
        ]
    },
    "kb": {
        "name": "Knowledge Base Manager",
        "description": "App for managing KB records, uploads, and sharing.",
        "allowedScopes": [
            "kb:read", "kb:write", "kb:delete", "kb:upload", "kb:share", 
            "offline_access"
        ]
    },
    "search": {
        "name": "Search Engine App",
        "description": "App for standard and semantic search queries.",
        "allowedScopes": ["search:query", "search:semantic", "offline_access"]
    },
    "conv": {
        "name": "Conversations & Chat App",
        "description": "App for reading, managing, and chatting in conversations.",
        "allowedScopes": [
            "conversation:read", "conversation:write", "conversation:chat", 
            "offline_access"
        ]
    },
    "conn": {
        "name": "Integration Connectors",
        "description": "App for managing and syncing external connectors.",
        "allowedScopes": [
            "connector:read", "connector:write", "connector:sync", "connector:delete", 
            "offline_access"
        ]
    },
    "agent": {
        "name": "AI Agents Workspace",
        "description": "App for defining and executing AI agents.",
        "allowedScopes": ["agent:read", "agent:write", "agent:execute", "offline_access"]
    },
    "infra": {
        "name": "Infrastructure Admin",
        "description": "Advanced app for System Config, Storage, and Crawling.",
        "allowedScopes": [
            "config:read", "config:write", 
            "document:read", "document:write", "document:delete",
            "crawl:read", "crawl:write", "offline_access"
        ]
    }
}

def create_oauth_app(config, org_id=None):
    """Sends POST request to create the OAuth application."""
    if not ADMIN_JWT_TOKEN:
        print("❌ Error: ADMIN_JWT_TOKEN environment variable is required.")
        return None

    payload = {
        "name": config["name"],
        "description": config["description"],
        "redirectUris": ["http://localhost:8888/callback"],
        "allowedGrantTypes": ["authorization_code", "refresh_token"],
        "allowedScopes": config["allowedScopes"],
        "isConfidential": True,
        "accessTokenLifetime": 3600,
        "refreshTokenLifetime": 2592000,
    }

    url = f"{BACKEND_URL}/api/v1/oauth-clients"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ADMIN_JWT_TOKEN}"
    }
    if org_id:
        headers["x-org-id"] = str(org_id)

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create app: {e}")
        if 'response' in locals() and response is not None:
             print(f"Response Data: {response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description="PipesHub OAuth App Generator")
    parser.add_argument(
        "type", 
        choices=APP_SCHEMAS.keys(), 
        help="Type of app to create: mgmt, kb, search, conv, conn, agent, or infra"
    )
    
    args = parser.parse_args()
    selected_config = APP_SCHEMAS[args.type]

    print(f"\n🚀 Initiating creation for: {selected_config['name']}")
    print(f"📡 Scopes: {', '.join(selected_config['allowedScopes'])}")

    org_id = get_org_id()
    if org_id:
        print(f"🏢 Using Organisation ID: {org_id}")
    else:
        print("⚠️ No org ID from backend; request may fail if endpoint requires it.")

    result = create_oauth_app(selected_config, org_id=org_id)

    if result:
        # Compatibility check for response structure
        app_data = result.get('app', result)
        client_id = app_data.get('clientId')
        client_secret = app_data.get('clientSecret')

        print("\n" + "═"*50)
        print("✨ OAUTH APPLICATION CREATED")
        print("═"*50)
        print(f"NAME:          {selected_config['name']}")
        print(f"CLIENT ID:     {client_id}")
        print(f"CLIENT SECRET: {client_secret}")
        print("═"*50)
        
        # Save to a dedicated .env file
        env_filename = f".env.{args.type}"
        with open(env_filename, "w") as f:
            f.write(f"# Generated: {datetime.now()}\n")
            f.write(f"PIPES_CLIENT_ID={client_id}\n")
            f.write(f"PIPES_CLIENT_SECRET={client_secret}\n")
            f.write(f"PIPES_SCOPES={','.join(selected_config['allowedScopes'])}\n")
            f.write(f"PIPES_BACKEND_URL={BACKEND_URL}\n")
        
        print(f"📂 Credentials exported to {env_filename}\n")

if __name__ == "__main__":
    main()

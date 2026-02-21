import argparse
import time

from common import run_scope_tests

# Define the scopes and endpoints for testing
TEST_SUITE = [
    # 1. List AI Agents (agent:read)
    {
        "scope": "agent:read",
        "path": "/api/v1/agents",
        "method": "GET",
        "cat": "Agents"
    },
    # 2. Create AI Agent (agent:write)
    {
        "scope": "agent:write",
        "path": "/api/v1/agents/create",
        "method": "POST",
        "cat": "Agents",
        "body": {
            "name": f"Support Assistant {int(time.time())}",
            "agentKey": f"test-agent-{int(time.time())}",
            "description": "Automated test agent",
            "systemPrompt": "You are a helpful assistant specialized in technical support.",
            "isPublic": False
        }
    },
    # 3. List Agent Templates (agent:read)
    {
        "scope": "agent:read",
        "path": "/api/v1/agents/template",
        "method": "GET",
        "cat": "Agents"
    }
]


def main():
    parser = argparse.ArgumentParser(description="Test OAuth scopes for Agents API")
    parser.add_argument(
        "--user-delegated",
        action="store_true",
        help="Use user consent flow (authorization code). Opens browser for user to approve; requires REDIRECT_URI (e.g. http://localhost:8888/callback) registered for your app.",
    )
    args = parser.parse_args()
    run_scope_tests(TEST_SUITE, use_user_delegated=args.user_delegated)


if __name__ == "__main__":
    main()

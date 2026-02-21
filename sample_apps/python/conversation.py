import argparse

from common import run_scope_tests

# Define the scopes and endpoints for testing
TEST_SUITE = [
    # 1. List Conversations (Read)
    {
        "scope": "conversation:read",
        "path": "/api/v1/conversations",
        "method": "GET"
    },
    # 2. Create a New Conversation (Write)
    {
        "scope": "conversation:write",
        "path": "/api/v1/conversations/create",
        "method": "POST",
        "body": {
            "query": "What is the organization's policy on remote work?",
            "chatMode": "standard"
        }
    },
    # 3. List Archived Conversations (Read)
    {
        "scope": "conversation:read",
        "path": "/api/v1/conversations/show/archives",
        "method": "GET"
    }
]


def main():
    parser = argparse.ArgumentParser(description="Test OAuth scopes for Conversations API")
    parser.add_argument(
        "--user-delegated",
        action="store_true",
        help="Use user consent flow (authorization code). Opens browser for user to approve; requires REDIRECT_URI (e.g. http://localhost:8888/callback) registered for your app.",
    )
    args = parser.parse_args()
    run_scope_tests(TEST_SUITE, use_user_delegated=args.user_delegated)


if __name__ == "__main__":
    main()

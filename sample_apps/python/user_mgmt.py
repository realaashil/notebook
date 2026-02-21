import argparse
import time

from common import run_scope_tests

# Define the scopes and endpoints for testing
TEST_SUITE = [
    # 1. Organization Management
    {"scope": "org:read", "path": "/api/v1/org", "method": "GET"},
    {"scope": "org:write", "path": "/api/v1/org", "method": "PUT",
     "body": {"shortName": "PipesTest", "registeredName": "PipesHub Testing Ltd"}},
    # 2. User Management
    {"scope": "user:read", "path": "/api/v1/users", "method": "GET"},
    {"scope": "user:invite", "path": "/api/v1/users", "method": "POST",
     "body": {"fullName": "New Tester", "email": "testuser@example.com", "sendInvite": False}},
    # 3. User Groups
    {"scope": "usergroup:read", "path": "/api/v1/userGroups", "method": "GET"},
    {"scope": "usergroup:write", "path": "/api/v1/userGroups", "method": "POST",
     "body": {"name": f"Test Group {int(time.time())}", "type": "standard"}},
    # 4. Teams
    {"scope": "team:read", "path": "/api/v1/teams", "method": "GET"},
    {"scope": "team:write", "path": "/api/v1/teams", "method": "POST",
     "body": {"name": f"Team Alpha {int(time.time())}", "description": "Sequential test team"}}
]


def main():
    parser = argparse.ArgumentParser(description="Test OAuth scopes for User/Org Management API")
    parser.add_argument(
        "--user-delegated",
        action="store_true",
        help="Use user consent flow (authorization code). Opens browser for user to approve; requires REDIRECT_URI (e.g. http://localhost:8888/callback) registered for your app.",
    )
    args = parser.parse_args()
    run_scope_tests(TEST_SUITE, use_user_delegated=args.user_delegated)


if __name__ == "__main__":
    main()

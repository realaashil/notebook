import argparse
import time

from common import run_scope_tests

# Define the scopes and endpoints for testing
TEST_SUITE = [
    # 1. Connector Registry (Read)
    {
        "scope": "connector:read",
        "path": "/api/v1/connectors/registry",
        "method": "GET"
    },
    # 2. List Connector Instances (Read)
    {
        "scope": "connector:read",
        "path": "/api/v1/connectors?scope=team",
        "method": "GET"
    },
    # 3. Create Connector Instance (Write)
    {
        "scope": "connector:write",
        "path": "/api/v1/connectors",
        "method": "POST",
        "body": {
            "connectorType": "web",
            "instanceName": f"Test Web Connector {int(time.time())}",
            "scope": "personal",
            "authType": "NONE"
        }
    }
]


def main():
    parser = argparse.ArgumentParser(description="Test OAuth scopes for Connectors API")
    parser.add_argument(
        "--user-delegated",
        action="store_true",
        help="Use user consent flow (authorization code). Opens browser for user to approve; requires REDIRECT_URI (e.g. http://localhost:8888/callback) registered for your app.",
    )
    args = parser.parse_args()
    run_scope_tests(TEST_SUITE, use_user_delegated=args.user_delegated)


if __name__ == "__main__":
    main()

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
    run_scope_tests(TEST_SUITE)


if __name__ == "__main__":
    main()

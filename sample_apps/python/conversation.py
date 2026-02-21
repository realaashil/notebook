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
    run_scope_tests(TEST_SUITE)


if __name__ == "__main__":
    main()

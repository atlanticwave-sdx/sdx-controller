"""
controller generated to handled auth operation described at:
https://connexion.readthedocs.io/en/latest/security.html
"""

import os

MASTER_API_KEY = os.getenv("MASTER_API_KEY")


def check_api_key(api_key, required_scopes):
    # Perform the necessary logic to check the validity of the API key
    # and determine if it has the required scopes
    if api_key == MASTER_API_KEY:
        return {"user": "admin"}
    else:
        error = "Invalid API key"
        return f"Failed, reason: {error}", 400


def check_topology_auth(token):
    return {"scopes": ["read:topology", "write:topology"], "uid": "test_value"}


def validate_scope_topology_auth(required_scopes, token_scopes):
    return set(required_scopes).issubset(set(token_scopes))

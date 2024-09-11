import json
import logging
import secrets
import uuid

import connexion
from flask import current_app

from sdx_controller.db_utils import DbUtils
from sdx_controller.models.user import User  # noqa: E501

# Get DB connection and tables set up.
db_instance = DbUtils()
db_instance.initialize_db()
collection_name = "users"


def create_user(body):  # noqa: E501
    """Create user

    This can only be done by the logged in user. # noqa: E501

    :param body: Created user object
    :type body: dict | bytes

    :rtype: None
    """
    logger.info(f"Creating a user: {body}")
    if not connexion.request.is_json:
        return "Request body must be JSON", 400

    body = connexion.request.get_json()
    user_id = body.get("id")
    if user_id is None:
        user_id_id = str(uuid.uuid4())
        body["id"] = user_id
        logger.info(f"User has no ID. Generated ID: {user_id}")

    user = User.from_dict(body)  # noqa: E501

    logger.info(f"Gathered connexion JSON: {body}")

    db_instance.add_key_value_pair_to_db(collection_name, user_id, json.dumps(body))

    logger.info("Saving to database complete.")


def create_users_with_array_input(body):  # noqa: E501
    """Creates list of users with given input array

     # noqa: E501

    :param body: List of user object
    :type body: list | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        body = [User.from_dict(d) for d in connexion.request.get_json()]  # noqa: E501
    return "do some magic!"


def create_users_with_list_input(body):  # noqa: E501
    """Creates list of users with given input array

     # noqa: E501

    :param body: List of user object
    :type body: list | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        body = [User.from_dict(d) for d in connexion.request.get_json()]  # noqa: E501
    return "do some magic!"


def delete_user(username):  # noqa: E501
    """Delete user

    This can only be done by the logged in user. # noqa: E501

    :param username: The name that needs to be deleted
    :type username: str

    :rtype: None
    """
    return "do some magic!"


def get_user_by_name(username):  # noqa: E501
    """Get user by user name

     # noqa: E501

    :param username: The name that needs to be fetched. Use user1 for testing.
    :type username: str

    :rtype: User
    """
    return "do some magic!"


def login_user(username, password):  # noqa: E501
    """Logs user into the system

     # noqa: E501

    :param username: The user name for login
    :type username: str
    :param password: The password for login in clear text
    :type password: str

    :rtype: str
    """
    return "do some magic!"


def logout_user():  # noqa: E501
    """Logs out current logged in user session

     # noqa: E501


    :rtype: None
    """
    return "do some magic!"


def update_user(body, username):  # noqa: E501
    """Updated user

    This can only be done by the logged in user. # noqa: E501

    :param body: Updated user object
    :type body: dict | bytes
    :param username: name that need to be updated
    :type username: str

    :rtype: None
    """
    if connexion.request.is_json:
        body = User.from_dict(connexion.request.get_json())  # noqa: E501
    return "do some magic!"


def generate_api_key(username):  # noqa: E501
    """Generate API key for a user

    This can only be done by the logged in user. # noqa: E501

    :param username: The name of the user for generating API key
    :type username: str
    """  # Generate the API key using secrets.token_hex()
    api_key = secrets.token_hex(16)
    return api_key

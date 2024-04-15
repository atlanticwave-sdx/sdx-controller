import json
import logging
import uuid

import connexion
from flask import current_app

from sdx_controller.handlers.connection_handler import ConnectionHandler
from sdx_controller.utils.db_utils import DbUtils

LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
logger.setLevel(logging.DEBUG)

# Get DB connection and tables set up.
db_instance = DbUtils()
db_instance.initialize_db()
connection_handler = ConnectionHandler(db_instance)


def delete_connection(connection_id):
    """
    Delete connection order by ID.

    :param connection_id: ID of the connection that needs to be
        deleted
    :type connection_id: int

    :rtype: None
    """
    return "do some magic!"


def getconnection_by_id(connection_id):
    """
    Find connection by ID.

    :param connection_id: ID of connection that needs to be fetched
    :type connection_id: int

    :rtype: Connection
    """
    value = db_instance.read_from_db(f"{connection_id}")
    return value


def place_connection(body):
    """
    Place an connection request from the SDX-Controller.

    :param body: order placed for creating a connection
    :type body: dict | bytes

    :rtype: Connection
    """
    logger.info(f"Placing connection: {body}")
    if not connexion.request.is_json:
        return "Request body must be JSON", 400

    body = connexion.request.get_json()
    logger.info(f"Gathered connexion JSON: {body}")

    logger.info("Placing connection. Saving to database.")
    db_instance.add_key_value_pair_to_db(
        body["id"] if "id" in body else str(uuid.uuid4()), json.dumps(body)
    )
    logger.info("Saving to database complete.")

    logger.info(f"Handling request with te_manager: {current_app.te_manager}")

    reason, code = connection_handler.place_connection(current_app.te_manager, body)
    logger.info(f"place_connection result: reason='{reason}', code={code}")

    return reason, code

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
    logger.info(
        f"Handling delete (connecton id: {connection_id}) "
        f"with te_manager: {current_app.te_manager}"
    )

    try:
        # TODO: pce's unreserve_vlan() method silently returns even if the
        # connection_id is not found.  This should in fact be an error.
        #
        # https://github.com/atlanticwave-sdx/pce/issues/180
        current_app.te_manager.unreserve_vlan(connection_id)
    except Exception as e:
        logger.info(f"Delete failed (connection id: {connection_id}): {e}")

    return "OK", 200


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
    request_id = uuid.uuid4()
    logger.info(f"Placing connection: request: {body}, request_id: {request_id}")

    if connexion.request.is_json:
        body = connexion.request.get_json()
        logger.info(f"Gathered connexion JSON: {body}")

    logger.info("Placing connection. Saving to database.")
    db_instance.add_key_value_pair_to_db("connection_data", json.dumps(body))
    logger.info("Saving to database complete.")

    logger.info(
        f"Handling request {request_id} with te_manager: {current_app.te_manager}"
    )

    reason, code = connection_handler.place_connection(current_app.te_manager, body)
    logger.info(
        f"place_connection result: request_id: {request_id} reason='{reason}', code={code}"
    )

    result = {
        "request_id": request_id,
        "status": "OK" if code == 200 else "Failure",
        "reason": reason,
    }

    return result, code

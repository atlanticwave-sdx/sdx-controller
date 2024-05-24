import json
import logging

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

    # # Looking up by UUID do not seem work yet.  Will address in
    # # https://github.com/atlanticwave-sdx/sdx-controller/issues/252.
    #
    # value = db_instance.read_from_db(f"{connection_id}")
    # print(f"value: {value}")
    # if not value:
    #     return "Not found", 404

    try:
        # TODO: pce's unreserve_vlan() method silently returns even if the
        # connection_id is not found.  This should in fact be an error.
        #
        # https://github.com/atlanticwave-sdx/pce/issues/180
        connection_handler.remove_connection(current_app, connection_id)
        deleted = db_instance.mark_deleted("connections", f"{connection_id}")
        if not deleted:
            return "Did not find connection", 404
    except Exception as e:
        logger.info(f"Delete failed (connection id: {connection_id}): {e}")
        return "Failed, reason: {e}", 500

    return "OK", 200


def getconnection_by_id(connection_id):
    """
    Find connection by ID.

    :param connection_id: ID of connection that needs to be fetched
    :type connection_id: int

    :rtype: Connection
    """
    value = db_instance.read_from_db("connections", f"{connection_id}")
    if not value:
        return "Connection not found", 404
    return json.loads(value[connection_id])


def getconnections():  # noqa: E501
    """List all connections

    connection details # noqa: E501

    :rtype: Connection
    """
    values = db_instance.get_all_entries_in_collection("connections")
    if not values:
        return "No connection was found", 404
    return_values = {}
    for connection in values:
        connection_id = next(iter(connection))
        return_values[connection_id] = json.loads(connection[connection_id])
    return return_values


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

    connection_id = body["id"]

    db_instance.add_key_value_pair_to_db("connections", connection_id, json.dumps(body))
    logger.info("Saving to database complete.")

    logger.info(
        f"Handling request {connection_id} with te_manager: {current_app.te_manager}"
    )

    reason, code = connection_handler.place_connection(current_app.te_manager, body)
    logger.info(
        f"place_connection result: ID: {connection_id} reason='{reason}', code={code}"
    )

    response = {
        "connection_id": connection_id,
        "status": "OK" if code == 200 else "Failure",
        "reason": reason,
    }

    # # TODO: our response is supposed to be shaped just like request
    # # ('#/components/schemas/connection'), and in that case the below
    # # code would be a quick implementation.
    # #
    # # https://github.com/atlanticwave-sdx/sdx-controller/issues/251
    # response = body

    # response["id"] = connection_id
    # response["status"] = "success" if code == 200 else "failure"
    # response["reason"] = reason # `reason` is not present in schema though.

    return response, code

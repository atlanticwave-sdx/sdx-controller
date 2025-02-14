import json
import logging
import uuid

import connexion
from flask import current_app

from sdx_controller import util
from sdx_controller.handlers.connection_handler import (
    ConnectionHandler,
    get_connection_status,
)
from sdx_controller.models.connection import Connection  # noqa: E501
from sdx_controller.models.l2vpn_body import L2vpnBody  # noqa: E501
from sdx_controller.models.l2vpn_service_id_body import L2vpnServiceIdBody  # noqa: E501
from sdx_controller.utils.db_utils import DbUtils
from sdx_controller.utils.constants import MongoCollections

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


def delete_connection(service_id):
    """
    Delete connection order by ID.

    :param service_id: ID of the connection that needs to be
        deleted
    :type service_id: str

    :rtype: None
    """
    logger.info(
        f"Handling delete (service id: {service_id}) "
        f"with te_manager: {current_app.te_manager}"
    )

    # # Looking up by UUID do not seem work yet.  Will address in
    # # https://github.com/atlanticwave-sdx/sdx-controller/issues/252.
    #
    # value = db_instance.read_from_db(f"{service_id}")
    # print(f"value: {value}")
    # if not value:
    #     return "Not found", 404

    try:
        # TODO: pce's unreserve_vlan() method silently returns even if the
        # service_id is not found.  This should in fact be an error.
        #
        # https://github.com/atlanticwave-sdx/pce/issues/180
        connection = db_instance.read_from_db(
            MongoCollections.CONNECTIONS.value, f"{service_id}"
        )
        if not connection:
            return "Did not find connection", 404
        connection_handler.remove_connection(current_app.te_manager, service_id)
        db_instance.mark_deleted(MongoCollections.CONNECTIONS.value, f"{service_id}")
        db_instance.mark_deleted("breakdowns", f"{service_id}")
    except Exception as e:
        logger.info(f"Delete failed (connection id: {service_id}): {e}")
        return f"Failed, reason: {e}", 500

    return "OK", 200


def get_connection_by_id(service_id):
    """
    Find connection by ID.

    :param service_id: ID of connection that needs to be fetched
    :type service_id: str

    :rtype: Connection
    """

    value = get_connection_status(db_instance, service_id)

    if not value:
        return "Connection not found", 404

    return value


def get_connections():  # noqa: E501
    """List all connections

    connection details # noqa: E501

    :rtype: Connection
    """
    values = db_instance.get_all_entries_in_collection(
        MongoCollections.CONNECTIONS.value
    )
    if not values:
        return "No connection was found", 404
    return_values = {}
    for connection in values:
        service_id = next(iter(connection))
        return_values[service_id] = get_connection_status(db_instance, service_id)[
            service_id
        ]
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

    service_id = body.get("id")

    if service_id is None:
        service_id = str(uuid.uuid4())
        body["id"] = service_id
        logger.info(f"Request has no ID. Generated ID: {service_id}")

    logger.info("Saving to database complete.")

    logger.info(
        f"Handling request {service_id} with te_manager: {current_app.te_manager}"
    )
    reason, code = connection_handler.place_connection(current_app.te_manager, body)

    if code // 100 == 2:
        db_instance.add_key_value_pair_to_db(
            MongoCollections.CONNECTIONS.value, service_id, json.dumps(body)
        )
        # Service created successfully
        code = 201

    logger.info(
        f"place_connection result: ID: {service_id} reason='{reason}', code={code}"
    )

    response = {
        "service_id": service_id,
        "status": "OK" if code // 100 == 2 else "Failure",
        "reason": reason,
    }

    # # TODO: our response is supposed to be shaped just like request
    # # ('#/components/schemas/connection'), and in that case the below
    # # code would be a quick implementation.
    # #
    # # https://github.com/atlanticwave-sdx/sdx-controller/issues/251
    # response = body

    # response["id"] = service_id
    # response["status"] = "success" if code == 2xx else "failure"
    # response["reason"] = reason # `reason` is not present in schema though.

    return response, code


def patch_connection(service_id, body=None):  # noqa: E501
    """Edit and change an existing L2vpn connection by ID from the SDX-Controller

     # noqa: E501

    :param service_id: ID of l2vpn connection that needs to be changed
    :type service_id: dict | bytes'
    :param body:
    :type body: dict | bytes

    :rtype: Connection
    """
    value = db_instance.read_from_db(
        MongoCollections.CONNECTIONS.value, f"{service_id}"
    )
    if not value:
        return "Connection not found", 404

    if not connexion.request.is_json:
        return "Request body must be JSON", 400

    body = L2vpnServiceIdBody.from_dict(connexion.request.get_json())  # noqa: E501

    logger.info(f"Gathered connexion JSON: {body}")

    body["id"] = service_id
    logger.info(f"Request has no ID. Generated ID: {service_id}")

    try:
        logger.info("Removing connection")
        # Get roll back connection before removing connection
        rollback_conn_body = db_instance.read_from_db(
            MongoCollections.CONNECTIONS.value, service_id
        )
        remove_conn_reason, remove_conn_code = connection_handler.remove_connection(
            current_app.te_manager, service_id
        )

        if remove_conn_code // 100 != 2:
            response = {
                "service_id": service_id,
                "status": "Failure",
                "reason": remove_conn_reason,
            }
            return response, remove_conn_code

        logger.info(f"Removed connection: {service_id}")
    except Exception as e:
        logger.info(f"Delete failed (connection id: {service_id}): {e}")
        return f"Failed, reason: {e}", 500

    logger.info(
        f"Placing new connection {service_id} with te_manager: {current_app.te_manager}"
    )

    reason, code = connection_handler.place_connection(current_app.te_manager, body)

    if code // 100 == 2:
        db_instance.add_key_value_pair_to_db(
            MongoCollections.CONNECTIONS.value, service_id, json.dumps(body)
        )
        # Service created successfully
        code = 201
        logger.info(f"Placed: ID: {service_id} reason='{reason}', code={code}")
        response = {
            "service_id": service_id,
            "status": "OK",
            "reason": reason,
        }
        return response, code

    logger.info(
        f"Failed to place new connection. ID: {service_id} reason='{reason}', code={code}"
    )
    logger.info("Rolling back to old connection.")

    if not rollback_conn_body:
        response = {
            "service_id": service_id,
            "status": "Failure, unable to rollback to last successful L2VPN connection",
            "reason": reason,
        }
        return response, code

    conn_request = json.loads(rollback_conn_body[service_id])
    conn_request["id"] = service_id

    try:
        rollback_conn_reason, rollback_conn_code = connection_handler.place_connection(
            current_app.te_manager, conn_request
        )
        if rollback_conn_code // 100 == 2:
            db_instance.add_key_value_pair_to_db(
                MongoCollections.CONNECTIONS.value, service_id, json.dumps(conn_request)
            )
        logger.info(
            f"Roll back connection result: ID: {service_id} reason='{rollback_conn_reason}', code={rollback_conn_code}"
        )
    except Exception as e:
        logger.info(f"Rollback failed (connection id: {service_id}): {e}")
        return f"Rollback failed, reason: {e}", 500

    response = {
        "service_id": service_id,
        "status": "Failure, rolled back to last successful L2VPN connection",
        "reason": reason,
    }
    return response, code


def get_archived_connections_by_id(service_id):
    """
    List archived connection by ID.

    :param service_id: ID of connection that needs to be fetched
    :type service_id: str

    :rtype: Connection
    """

    value = get_connection_status(db_instance, service_id)

    if not value:
        return "Connection not found", 404

    return value

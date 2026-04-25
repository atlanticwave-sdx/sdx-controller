import copy
import logging
import os
import time
import uuid

import connexion
from flask import current_app
from sdx_datamodel.connection_sm import ConnectionStateMachine
from sdx_datamodel.constants import MongoCollections

from sdx_controller.handlers.connection_handler import (
    ConnectionHandler,
    connection_state_machine,
    get_connection_status,
    parse_conn_status,
)

# from sdx_controller.models.l2vpn_service_id_body import L2vpnServiceIdBody  # noqa: E501
from sdx_controller.utils.db_utils import DbUtils

LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "DEBUG")))
ROLLBACK_SETTLE_TIMEOUT_SECONDS = float(
    os.getenv("ROLLBACK_SETTLE_TIMEOUT_SECONDS", "5")
)
ROLLBACK_SETTLE_POLL_SECONDS = float(os.getenv("ROLLBACK_SETTLE_POLL_SECONDS", "0.2"))

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
        connection = db_instance.get_value_from_db(
            MongoCollections.CONNECTIONS, f"{service_id}"
        )

        if not connection:
            return "Did not find connection", 404

        logger.info(f"connection: {connection} {type(connection)}")
        logger.info(f"Removing connection: {service_id} {connection.get('status')}")

        remove_reason, remove_code = connection_handler.remove_connection(
            current_app.te_manager, service_id, "API"
        )
        if remove_code // 100 != 2:
            logger.info(
                f"Delete failed (connection id: {service_id}): "
                f"reason='{remove_reason}', code={remove_code}"
            )
            # return remove_reason, remove_code
        db_instance.mark_deleted(MongoCollections.CONNECTIONS, f"{service_id}")
        db_instance.mark_deleted(MongoCollections.BREAKDOWNS, f"{service_id}")
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
    """
    List all connections

    connection details # noqa: E501

    :rtype: Connection
    """
    values = db_instance.get_all_entries_in_collection(MongoCollections.CONNECTIONS)
    if not values:
        return "No connection was found", 404
    return_values = {}
    for connection in values:
        service_id = next(iter(connection))
        logger.info(f"service_id: {service_id}")
        connection_status = get_connection_status(db_instance, service_id)
        if connection_status:
            return_values[service_id] = connection_status.get(service_id)
    return return_values


def get_archived_connections():
    """
    List all archived connections.

    :rtype: dict
    """
    values = db_instance.get_all_entries_in_collection(
        MongoCollections.HISTORICAL_CONNECTIONS
    )
    if not values:
        return "No archived connection was found", 404

    return_values = {}
    for archived_connection in values:
        service_id = next(iter(archived_connection))
        archived_events = connection_handler.get_archived_connections(service_id)
        if archived_events:
            return_values[service_id] = archived_events

    if not return_values:
        return "No archived connection was found", 404
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

    conn_status = ConnectionStateMachine.State.REQUESTED
    body["status"] = str(conn_status)

    # used in lc_message_handler to count the oxp success response
    body["oxp_success_count"] = 0
    body["partial_cleanup_requested"] = False
    body["provisioning_timeout_handled"] = False
    body["provisioning_started_at"] = time.time()
    body.pop("timeout_reason", None)

    db_instance.add_key_value_pair_to_db(MongoCollections.CONNECTIONS, service_id, body)

    logger.info(
        f"Handling request {service_id} with te_manager: {current_app.te_manager}"
    )
    reason, code = connection_handler.place_connection(current_app.te_manager, body)

    if code // 100 == 2:
        # conn_status = ConnectionStateMachine.State.UNDER_PROVISIONING
        # body, _ = connection_state_machine(body, conn_status)
        # db_instance.update_field_in_json(
        #    MongoCollections.CONNECTIONS,
        #    service_id,
        #    "status",
        #    str(conn_status),
        # )
        logger.info(f"place_connection succeeds: ID: {service_id} body='{body}'")
    else:
        conn_status = ConnectionStateMachine.State.REJECTED
        body, _ = connection_state_machine(body, conn_status)
        db_instance.update_field_in_json(
            MongoCollections.CONNECTIONS,
            service_id,
            "status",
            str(conn_status),
        )
    logger.info(
        f"place_connection result: ID: {service_id} reason='{reason}', code={code}"
    )

    current_conn = db_instance.get_value_from_db(
        MongoCollections.CONNECTIONS, f"{service_id}"
    )
    response = {
        "service_id": service_id,
        "status": parse_conn_status(
            current_conn.get("status", str(conn_status))
            if current_conn
            else str(conn_status)
        ),
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
    body = db_instance.get_value_from_db(MongoCollections.CONNECTIONS, f"{service_id}")
    if not body:
        return "Connection not found", 404

    if not connexion.request.is_json:
        return "Request body must be JSON", 400

    new_body = connexion.request.get_json()

    logger.info(f"Gathered connexion JSON: {new_body}")

    if "id" not in new_body:
        new_body["id"] = service_id

    # Validate the new request body before making any change to the existing connection.
    # This is to avoid the case where we have already removed the original connection but the new request body is invalid, which will cause the connection to be deleted but not re-created.
    # We can reuse the same validation function used in place_connection since the request body for patch_connection has the same schema as place_connection.
    #
    te_manager = current_app.te_manager  # Assuming te_manager is accessible like this
    try:
        # Validate the new request body
        te_manager.generate_traffic_matrix(connection_request=new_body)
    except Exception as request_err:
        logger.error("ERROR: invalid patch request: " + str(request_err))
        error_code = getattr(request_err, "request_code", None)
        if not isinstance(error_code, int):
            # Backward-compatible fallback for exception strings like "... (Code: 400)".
            error_code = 400
            err_text = str(request_err)
            if "Code:" in err_text:
                candidate = err_text.split("Code:")[-1].replace(")", "").strip()
                try:
                    error_code = int(candidate)
                except (TypeError, ValueError):
                    logger.warning(
                        f"Could not parse error code from patch validation error: {err_text}"
                    )
        return f"Error: patch request is not valid: {request_err}", error_code

    logger.info("Modifying connection")
    # Preserve the last successful request so rollback can recreate it cleanly.
    rollback_conn_body = copy.deepcopy(body)
    body.update(new_body)

    conn_status = ConnectionStateMachine.State.MODIFYING
    body, _ = connection_state_machine(body, conn_status)
    db_instance.update_field_in_json(
        MongoCollections.CONNECTIONS,
        service_id,
        "status",
        str(conn_status),
    )

    try:
        logger.info("Removing connection")
        remove_conn_reason, remove_conn_code = connection_handler.remove_connection(
            current_app.te_manager, service_id, "API"
        )

        if remove_conn_code // 100 != 2:
            conn_status = ConnectionStateMachine.State.DOWN
            body, _ = connection_state_machine(body, conn_status)
            db_instance.update_field_in_json(
                MongoCollections.CONNECTIONS,
                service_id,
                "status",
                str(conn_status),
            )
            response = {
                "service_id": service_id,
                "status": parse_conn_status(body["status"]),
                "reason": f"Failure to modify L2VPN during removal: {remove_conn_reason}",
            }
            return response, remove_conn_code

        logger.info(f"Removed connection: {service_id}")
    except Exception as e:
        logger.info(f"Delete failed (connection id: {service_id}): {e}")
        conn_status = ConnectionStateMachine.State.DOWN
        body, _ = connection_state_machine(body, conn_status)
        db_instance.update_field_in_json(
            MongoCollections.CONNECTIONS,
            service_id,
            "status",
            str(conn_status),
        )
        return f"Failed, reason: {e}", 500
    time.sleep(10)
    logger.info(
        f"Modifying: Placing new connection {service_id} with te_manager: {current_app.te_manager}"
    )
    # Reset: remove_connection archives/deletes the original entry,
    # so persist the patched request before re-placement.
    conn_status = ConnectionStateMachine.State.REQUESTED
    body["status"] = str(conn_status)
    body["oxp_success_count"] = 0
    body["oxp_response"] = {}
    db_instance.add_key_value_pair_to_db(MongoCollections.CONNECTIONS, service_id, body)
    reason, code = connection_handler.place_connection(current_app.te_manager, body)

    if code // 100 == 2:
        # Service created successfully
        # conn_status = ConnectionStateMachine.State.UNDER_PROVISIONING
        # body, _ = connection_state_machine(body, conn_status)
        # db_instance.add_key_value_pair_to_db(
        #    MongoCollections.CONNECTIONS, service_id, body
        # )
        code = 201
        logger.info(f"Placed: ID: {service_id} reason='{reason}', code={code}")
        response = {
            "service_id": service_id,
            "status": parse_conn_status(body["status"]),
            "reason": reason,
        }
        return response, code

    logger.info(
        f"Modifying: Failed to place new connection. ID: {service_id} reason='{reason}', code={code}"
    )
    logger.info("Rolling back to old connection.")

    # because above placement failed, so re-place the original connection request.

    rollback_conn_body["status"] = str(ConnectionStateMachine.State.REQUESTED)
    # used in lc_message_handler to count the oxp success response
    rollback_conn_body["oxp_success_count"] = 0
    rollback_conn_body["oxp_response"] = {}

    conn_request = rollback_conn_body
    conn_request["id"] = service_id
    conn_request["status"] = str(ConnectionStateMachine.State.REQUESTED)
    conn_request["oxp_success_count"] = 0
    conn_request["oxp_response"] = {}
    conn_request["late_cleanup_domains"] = []
    conn_request["partial_cleanup_requested"] = False
    conn_request["provisioning_timeout_handled"] = False
    conn_request["provisioning_started_at"] = time.time()
    conn_request.pop("timeout_reason", None)
    conn_request, _ = connection_state_machine(
        conn_request, ConnectionStateMachine.State.UNDER_PROVISIONING
    )
    db_instance.add_key_value_pair_to_db(
        MongoCollections.CONNECTIONS, service_id, conn_request
    )

    rollback_conn_reason = "Rollback attempt did not complete"
    try:
        rollback_conn_reason, rollback_conn_code = connection_handler.place_connection(
            current_app.te_manager, conn_request
        )
        if rollback_conn_code // 100 == 2:
            # conn_status = ConnectionStateMachine.State.UNDER_PROVISIONING
            # rollback_conn_body, _ = connection_state_machine(
            #    rollback_conn_body, conn_status
            # )
            # db_instance.update_field_in_json(
            #    MongoCollections.CONNECTIONS,
            #    service_id,
            #    "status",
            #    str(conn_status),
            # )
            # still return 400 to indicate the patch request is not successful, since we have already rolled back to original connection, which is under provisioning state, so the connection is not down and not failed.
            rollback_conn_code = code
        else:
            conn_status = ConnectionStateMachine.State.REJECTED
            body, _ = connection_state_machine(body, conn_status)
            db_instance.update_field_in_json(
                MongoCollections.CONNECTIONS,
                service_id,
                "status",
                str(conn_status),
            )
            deadline = time.time() + ROLLBACK_SETTLE_TIMEOUT_SECONDS
            while time.time() < deadline:
                current_conn = db_instance.get_value_from_db(
                    MongoCollections.CONNECTIONS, service_id
                )
                current_status = current_conn.get("status") if current_conn else None
                if current_status != str(
                    ConnectionStateMachine.State.UNDER_PROVISIONING
                ):
                    break
                time.sleep(ROLLBACK_SETTLE_POLL_SECONDS)
        logger.info(
            f"Roll back connection result: ID: {service_id} reason='{rollback_conn_reason}', code={rollback_conn_code}"
        )
    except Exception as e:
        conn_status = ConnectionStateMachine.State.REJECTED
        db_instance.update_field_in_json(
            MongoCollections.CONNECTIONS,
            service_id,
            "status",
            str(conn_status),
        )
        logger.info(f"Rollback failed (connection id: {service_id}): {e}")
        rollback_conn_reason = f"Rollback failed: {e}"
        rollback_conn_code = 500

    response_code = code if rollback_conn_code // 100 == 2 else rollback_conn_code
    current_conn = db_instance.get_value_from_db(
        MongoCollections.CONNECTIONS, f"{service_id}"
    )
    response = {
        "service_id": service_id,
        "reason": f"Failure, rolled back to last successful L2VPN: {reason}",
        "status": parse_conn_status(
            current_conn.get("status", "") if current_conn else ""
        ),
    }
    return response, response_code


def get_archived_connections_by_id(service_id):
    """
    List archived connection by ID.

    :param service_id: ID of connection that needs to be fetched
    :type service_id: str

    :rtype: Connection
    """

    value = connection_handler.get_archived_connections(service_id)

    if not value:
        return "Archived connection not found", 404

    return {service_id: value}

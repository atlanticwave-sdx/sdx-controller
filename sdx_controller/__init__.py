import logging
import os
import threading
import time
from queue import Queue

import connexion
from sdx_datamodel.connection_sm import ConnectionStateMachine
from sdx_datamodel.constants import MongoCollections
from sdx_pce.topology.temanager import TEManager

from sdx_controller import encoder
from sdx_controller.handlers.connection_handler import (
    ConnectionHandler,
    connection_state_machine,
)
from sdx_controller.messaging.rpc_queue_consumer import RpcConsumer
from sdx_controller.utils.db_utils import DbUtils

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOG_FILE = os.environ.get("LOG_FILE")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
OXP_RESPONSE_TIMEOUT = int(os.getenv("OXP_RESPONSE_TIMEOUT", 60))
PROVISIONING_MONITOR_INTERVAL = int(os.getenv("PROVISIONING_MONITOR_INTERVAL", 5))


def create_rpc_thread(app):
    """
    Start a thread to get items off the message queue.
    """
    thread_queue = Queue()

    app.rpc_consumer = RpcConsumer(thread_queue, "", app.te_manager)
    rpc_thread = threading.Thread(
        target=app.rpc_consumer.start_sdx_consumer,
        kwargs={"thread_queue": thread_queue, "db_instance": app.db_instance},
        daemon=True,
    )

    rpc_thread.start()


def create_provisioning_timeout_thread(app):
    """
    Start a background monitor for connections stuck in
    UNDER_PROVISIONING longer than the configured timeout.
    """
    if OXP_RESPONSE_TIMEOUT <= 0:
        logger.info("[ProvisioningTimeout] Disabled.")
        app.provisioning_timeout_thread = None
        return

    connection_handler = ConnectionHandler(app.db_instance)

    def monitor_loop():
        logger.info(
            f"[ProvisioningTimeout] Started monitoring with timeout={OXP_RESPONSE_TIMEOUT}s interval={PROVISIONING_MONITOR_INTERVAL}s."
        )
        while True:
            try:
                now = time.time()
                connections = app.db_instance.get_all_entries_in_collection(
                    MongoCollections.CONNECTIONS
                )
                for connection_entry in connections:
                    service_id = next(iter(connection_entry), None)
                    connection = connection_entry.get(service_id) if service_id else None
                    if not isinstance(connection, dict):
                        continue
                    if (
                        connection.get("status")
                        != str(ConnectionStateMachine.State.UNDER_PROVISIONING)
                    ):
                        continue

                    started_at = connection.get("provisioning_started_at")
                    if not isinstance(started_at, (int, float)):
                        continue
                    if connection.get("provisioning_timeout_handled"):
                        continue
                    if now - started_at < OXP_RESPONSE_TIMEOUT:
                        continue

                    logger.warning(
                        f"[ProvisioningTimeout] Connection {service_id} timed out after {int(now - started_at)}s waiting for OXP responses."
                    )

                    connection["provisioning_timeout_handled"] = True
                    connection["partial_cleanup_requested"] = True
                    connection["timeout_reason"] = (
                        f"OXP response timeout after {OXP_RESPONSE_TIMEOUT} seconds"
                    )
                    connection, _ = connection_state_machine(
                        connection, ConnectionStateMachine.State.DOWN
                    )
                    app.db_instance.add_key_value_pair_to_db(
                        MongoCollections.CONNECTIONS, service_id, connection
                    )
                    cleanup_status, cleanup_code = (
                        connection_handler.cleanup_partial_connection(
                            app.te_manager, service_id, connection
                        )
                    )
                    logger.info(
                        f"[ProvisioningTimeout] Cleanup result for {service_id}: {cleanup_status}, code={cleanup_code}"
                    )
            except Exception as e:
                logger.exception(
                    f"[ProvisioningTimeout] Error while monitoring connections: {e}"
                )
            time.sleep(PROVISIONING_MONITOR_INTERVAL)

    provisioning_thread = threading.Thread(target=monitor_loop, daemon=True)
    provisioning_thread.start()
    app.provisioning_timeout_thread = provisioning_thread


def create_app(run_listener: bool = True):
    """
    Create a connexion app.

    The object returned is a Connexion App, which in turn contains a
    Flask app, that we can run either with Flask or an ASGI server
    such as uvicorn::

        $ flask run sdx_server.app:app
        $ uvicorn run sdx_server.app:asgi_app

    We also create a thread that subscribes to our message queue.
    Occasionally it might be useful not to start the thread (such as
    when running the test suite, because currently our tests do not
    use the message queue), and we might want to disable those
    threads, which is when run_listener param might be useful.
    """
    if LOG_FILE:
        logging.basicConfig(filename=LOG_FILE, level=logging.getLevelName(LOG_LEVEL))
    else:
        logging.basicConfig(level=logging.getLevelName(LOG_LEVEL))

    logging.getLogger("sdx_pce.topology.temanager").setLevel(logging.INFO)
    app = connexion.App(__name__, specification_dir="./swagger/")
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(
        "swagger.yaml", arguments={"title": "SDX-Controller"}, pythonic_params=True
    )

    # Get DB connection and tables set up.
    app.db_instance = DbUtils()
    app.db_instance.initialize_db()

    # Get a handle to PCE.
    app.te_manager = TEManager(topology_data=None)

    # TODO: This is a hack, until we find a better way to get a handle
    # to TEManager from Flask current_app, which are typically
    # available to request handlers.  There must be a better way to
    # pass this around.
    app.app.te_manager = app.te_manager

    create_provisioning_timeout_thread(app)

    if run_listener:
        create_rpc_thread(app)
    else:
        app.rpc_consumer = None

    return app

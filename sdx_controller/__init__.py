import logging
import os
import threading
from queue import Queue

import connexion
from sdx_pce.topology.manager import TopologyManager

from sdx_controller import encoder
from sdx_controller.messaging.rpc_queue_consumer import RpcConsumer
from sdx_controller.utils.db_utils import DbUtils

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOG_FILE = os.environ.get("LOG_FILE")


def create_rpc_thread(app):
    topology_manager = TopologyManager()
    thread_queue = Queue()

    app.rpc_consumer = RpcConsumer(thread_queue, "", topology_manager)
    rpc_thread = threading.Thread(
        target=app.rpc_consumer.start_sdx_consumer,
        kwargs={"thread_queue": thread_queue, "db_instance": app.db_instance},
        daemon=True,
    )

    app.rpc_thread.start()


def create_app(run_listener: bool = True):
    if LOG_FILE:
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO)

    app = connexion.App(__name__, specification_dir="./swagger/")
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(
        "swagger.yaml", arguments={"title": "SDX-Controller"}, pythonic_params=True
    )

    # Run swagger in a thread
    # threading.Thread(target=lambda: app.run(port=8080)).start()

    # Get DB connection and tables set up.
    app.db_instance = DbUtils()
    app.db_instance.initialize_db()

    if run_listener:
        create_rpc_thread(app, app.db_instance)

    return app

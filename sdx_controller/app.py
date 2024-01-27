#!/usr/bin/env python3

import logging
import os
import signal
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


# TODO: this doesn't seem to work.
def signal_handler(signum, frame):
    logging.info("Running signal handler")
    application.rpc_thread.stop_sdx_consumer()


def create_app():
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
    db_instance = DbUtils()
    db_instance.initialize_db()

    logging.info("Installing signal handler")
    signal.signal(signal.SIGINT, signal_handler)

    topology_manager = TopologyManager()
    thread_queue = Queue()
    rpc_consumer = RpcConsumer(thread_queue, "", topology_manager)

    app.rpc_thread = threading.Thread(
        target=rpc_consumer.start_sdx_consumer,
        kwargs={"thread_queue": thread_queue, "db_instance": db_instance},
    )

    app.rpc_thread.start()

    return app


application = create_app()
app = application.app

if __name__ == "__main__":
    app.run()

#!/usr/bin/env python3

import logging
import os
import threading
from queue import Queue

import connexion
from sdx_pce.topology.manager import TopologyManager

from swagger_server import encoder
from swagger_server.messaging.rpc_queue_consumer import RpcConsumer
from swagger_server.utils.db_utils import DbUtils

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOG_FILE = os.environ.get("LOG_FILE")


def main():
    if LOG_FILE:
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    # Run swagger service
    app = connexion.App(__name__, specification_dir="./swagger/")
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(
        "swagger.yaml", arguments={"title": "SDX-Controller"}, pythonic_params=True
    )

    # Run swagger in a thread
    threading.Thread(target=lambda: app.run(port=8080)).start()

    # Get DB connection and tables set up.
    db_instance = DbUtils()
    db_instance.initialize_db()

    topology_manager = TopologyManager()

    thread_queue = Queue()
    rpc = RpcConsumer(thread_queue, "", topology_manager)
    rpc.start_sdx_consumer(thread_queue, db_instance)


if __name__ == "__main__":
    main()

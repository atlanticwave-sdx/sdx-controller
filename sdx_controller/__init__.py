import logging
import os
import threading
from queue import Queue

import connexion
from sdx_pce.topology.temanager import TEManager

from sdx_controller import encoder
from sdx_controller.messaging.rpc_queue_consumer import RpcConsumer
from sdx_controller.utils.db_utils import DbUtils

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOG_FILE = os.environ.get("LOG_FILE")


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
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

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

    if run_listener:
        create_rpc_thread(app)
    else:
        app.rpc_consumer = None

    return app

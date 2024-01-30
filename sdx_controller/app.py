import atexit
import logging

from sdx_controller import create_app

application = create_app()
app = application.app


@atexit.register
def on_app_exit():
    logging.info("Stopping RPC threads")
    application.rpc_consumer.stop_threads()


if __name__ == "__main__":
    app.run()

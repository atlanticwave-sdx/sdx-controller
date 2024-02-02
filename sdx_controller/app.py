import atexit

from asgiref.wsgi import WsgiToAsgi

from sdx_controller import create_app

application = create_app()
app = application.app
asgi_app = WsgiToAsgi(app)

@atexit.register
def on_app_exit():
    """
    Do some cleanup on exit.

    We run a message queue consumer in a separate thread, and here we
    signal the thread that we're exiting.
    """
    application.rpc_consumer.stop_threads()


if __name__ == "__main__":
    app.run()

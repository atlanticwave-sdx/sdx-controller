import atexit

from asgiref.wsgi import WsgiToAsgi

from sdx_controller import create_app

# This is a `connexion.apps.flask_app.FlaskApp` that we created using
# connexion.App().
application = create_app()

# This is a `flask.app.Flask` object.
app = application.app

# We use WsgiToAsgi adapter so that we can use an ASGI server (such as
# uvicorn or hypercorn).
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

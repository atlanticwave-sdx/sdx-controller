import atexit

from asgiref.wsgi import WsgiToAsgi
from flask import redirect

from sdx_controller import create_app

# This is a `connexion.apps.flask_app.FlaskApp` that we created using
# connexion.App().
application = create_app()

# The application above contains a `flask.app.Flask` object.  We can
# run the app using flask, like so:
#
#     $ flask --app sdx_controller.app:app run --debug
#
app = application.app

# We use WsgiToAsgi adapter so that we can use an ASGI server (such as
# uvicorn or hypercorn), like so:
#
#     $ uvicorn sdx_controller.app:asgi_app --host 0.0.0.0 --port 8080
#
asgi_app = WsgiToAsgi(app)


@app.route("/", methods=["GET"])
def index():
    return redirect("/SDX-Controller/ui/")


@atexit.register
def on_app_exit():
    """
    Do some cleanup on exit.

    We run a message queue consumer in a separate thread, and here we
    signal the thread that we're exiting.
    """
    if application.rpc_consumer:
        application.rpc_consumer.stop_threads()


if __name__ == "__main__":
    app.run()

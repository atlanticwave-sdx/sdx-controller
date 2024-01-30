import logging
import os

import connexion
from flask_testing import TestCase

from sdx_controller import create_app


class BaseTestCase(TestCase):

    def create_app(self):
        # Do not use the message queue if MQ_HOST is not set.  This is
        # a useful work-around when we do not want to spin up a
        # RabbitMQ insteance just for testing, since the test suite
        # doesn't use a message queue right now.
        app = create_app(run_listener=True if os.getenv("MQ_HOST") else False)
        return app.app

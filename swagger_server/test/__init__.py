import logging

import connexion
from flask_testing import TestCase

from swagger_server.encoder import JSONEncoder
from swagger_server.__main__ import create_app


class BaseTestCase(TestCase):
    def create_app(self):
        logging.getLogger("connexion.operation").setLevel("ERROR")

        app = create_app()

        # TODO: we need a handle to TEManager in tests, so we will use
        # this.  There must be a better way to accesss this though.
        self.te_manager = app.te_manager

        return app.app

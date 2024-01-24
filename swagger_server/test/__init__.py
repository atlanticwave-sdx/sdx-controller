import logging

import connexion
from flask_testing import TestCase

from swagger_server.encoder import JSONEncoder
from swagger_server.__main__ import create_app


class BaseTestCase(TestCase):
    def create_app(self):
        logging.getLogger("connexion.operation").setLevel("ERROR")

        app = create_app()

        return app.app

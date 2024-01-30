import logging

import connexion
from flask_testing import TestCase

from sdx_controller import create_app


class BaseTestCase(TestCase):

    def create_app(self):
        app = create_app(run_listener=False)
        return app.app

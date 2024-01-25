import logging

import connexion
from flask_testing import TestCase

from swagger_server.__main__ import create_app
from swagger_server.encoder import JSONEncoder

try:
    # Use stdlib modules with Python > 3.8.
    from importlib.resources import files
except ImportError:
    # Use compatibility library with Python 3.8.
    from importlib_resources import files


class BaseTestCase(TestCase):
    def create_app(self):
        logging.getLogger("connexion.operation").setLevel("ERROR")

        app = create_app()

        # TODO: we need a handle to TEManager in tests, so we will use
        # this.  There must be a better way to accesss this though.
        self.te_manager = app.te_manager

        return app.app


class TestData:
    TOPOLOGY_DIR = files("sdx_datamodel") / "data" / "topologies"
    TOPOLOGY_FILE_ZAOXI = TOPOLOGY_DIR / "zaoxi.json"
    TOPOLOGY_FILE_SAX = TOPOLOGY_DIR / "sax.json"
    TOPOLOGY_FILE_AMLIGHT = TOPOLOGY_DIR / "amlight.json"

    REQUESTS_DIR = files("sdx_datamodel") / "data" / "requests"
    CONNECTION_REQ = REQUESTS_DIR / "test_request.json"

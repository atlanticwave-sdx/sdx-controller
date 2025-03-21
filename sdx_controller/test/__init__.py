import os

from flask_testing import TestCase

try:
    # Use stdlib modules with Python > 3.8.
    from importlib.resources import files
except ImportError:
    # Use compatibility library with Python 3.8.
    from importlib_resources import files

from sdx_controller import create_app


class BaseTestCase(TestCase):
    def create_app(self):
        # Do not use the message queue if MQ_HOST is not set.  This is
        # a useful work-around when we do not want to spin up a
        # RabbitMQ insteance just for testing, since the test suite
        # doesn't use a message queue right now.
        app = create_app(run_listener=True if os.getenv("MQ_HOST") else False)

        # TODO: We need a handle to the TEManager instance in tests,
        # so we add a handle here, although doing it this way feels
        # like a work-around.  There must be a better way to get a
        # handle to TEManager?
        self.te_manager = app.te_manager
        self.db_instance = app.db_instance
        return app.app


class TestData:
    TOPOLOGY_DIR = files("sdx_datamodel") / "data" / "topologies"
    TOPOLOGY_FILE_ZAOXI = TOPOLOGY_DIR / "zaoxi.json"
    TOPOLOGY_FILE_SAX = TOPOLOGY_DIR / "sax.json"
    TOPOLOGY_FILE_AMLIGHT = TOPOLOGY_DIR / "amlight.json"
    TOPOLOGY_FILE_AMLIGHT_USER_PORT = TOPOLOGY_DIR / "amlight_user_port.json"

    REQUESTS_DIR = files("sdx_datamodel") / "data" / "requests"
    CONNECTION_REQ = REQUESTS_DIR / "test_request.json"
    CONNECTION_REQ_V2_L2VPN_P2P = REQUESTS_DIR / "test-l2vpn-p2p-v2.json"
    CONNECTION_REQ_V2_AMLIGHT_ZAOXI = (
        REQUESTS_DIR / "test_request-amlight_zaoxi-p2p-v2.json"
    )

    TOPOLOGY_FILE_AMLIGHT_v2 = TOPOLOGY_DIR / "ampath_v2.json"
    TOPOLOGY_FILE_SAX_v2 = TOPOLOGY_DIR / "sax_v2.json"
    TOPOLOGY_FILE_ZAOXI_v2 = TOPOLOGY_DIR / "zaoxi_v2.json"

# coding: utf-8

from __future__ import absolute_import

from swagger_server.test import BaseTestCase


class TestNodeController(BaseTestCase):
    """NodeController integration test stubs"""

    def test_get_node(self):
        """Test case for get_node

        get an existing node
        """
        response = self.client.open("/SDX-Controller/1.0.0/node", method="GET")
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

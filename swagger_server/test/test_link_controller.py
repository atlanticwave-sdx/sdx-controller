# coding: utf-8

from __future__ import absolute_import

from swagger_server.test import BaseTestCase


class TestLinkController(BaseTestCase):
    """LinkController integration test stubs"""

    def test_get_link(self):
        """Test case for get_link

        get an existing link
        """
        response = self.client.open("/SDX-Controller/1.0.0/link", method="GET")
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

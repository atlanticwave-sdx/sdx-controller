# coding: utf-8

from __future__ import absolute_import

from sdx_controller.test import BaseTestCase


class TestLinkController(BaseTestCase):
    """LinkController integration test stubs"""

    def test_get_link(self):
        """Test case for get_link

        get an existing link
        """
        response = self.client.open("/SDX-Controller/link", method="GET")
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from sdx_controller.models.connection import Connection  # noqa: E501
from sdx_controller.models.l2vpn_body import L2vpnBody  # noqa: E501
from sdx_controller.test import BaseTestCase


class TestL2vpnController(BaseTestCase):
    """L2vpnController integration test stubs"""

    def test_delete_connection(self):
        """Test case for delete_connection

        Delete connection order by ID
        """
        response = self.client.open(
            "/SDX-Controller/1.0.0/l2vpn/{service_id}".format(
                service_id="38400000-8cf0-11bd-b23e-10b96e4ef00d"
            ),
            method="DELETE",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_getconnection_by_id(self):
        """Test case for getconnection_by_id

        Find l2vpn connection by ID
        """
        response = self.client.open(
            "/SDX-Controller/1.0.0/l2vpn/{service_id}".format(
                service_id="38400000-8cf0-11bd-b23e-10b96e4ef00d"
            ),
            method="GET",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_getconnections(self):
        """Test case for getconnections

        List all l2vpn connections
        """
        response = self.client.open("/SDX-Controller/1.0.0/l2vpn", method="GET")
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_place_connection(self):
        """Test case for place_connection

        Place an L2vpn connection request from the SDX-Controller
        """
        body = L2vpnBody()
        response = self.client.open(
            "/SDX-Controller/1.0.0/l2vpn",
            method="POST",
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

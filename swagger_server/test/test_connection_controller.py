# coding: utf-8

from __future__ import absolute_import

import datetime

from flask import json
from six import BytesIO

from swagger_server.models.connection import Connection  # noqa: E501
from swagger_server.models.port import Port
from swagger_server.test import BaseTestCase


class TestConnectionController(BaseTestCase):
    """ConnectionController integration test stubs"""

    def test_delete_connection(self):
        """Test case for delete_connection

        Delete connection order by ID
        """
        response = self.client.open(
            "/SDX-Controller/1.0.0/connection/{connection_id}".format(connection_id=2),
            method="DELETE",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_getconnection_by_id(self):
        """Test case for getconnection_by_id

        Find connection by ID
        """
        response = self.client.open(
            "/SDX-Controller/1.0.0/connection/{connection_id}".format(connection_id=10),
            method="GET",
        )

        # The connection_id we've supplied above should not exist.
        # TODO: test for existing connection_id.  See
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/34.
        self.assertStatus(response, 204)

    def test_place_connection(self):
        """Test case for place_connection

        Place an connection request from the SDX-Controller
        """
        # body = Connection()
        ingress_port = Port(
            id="ingress_port_id",
            name="ingress_port_name",
            node="ingress_node",
            status="unknown",
            state="unknown",
        )

        egress_port = Port(
            id="egress_port_id",
            name="egress_port_name",
            node="egress_node",
            status="unknown",
            state="unknown",
        )

        connection = Connection(
            id="test_place_connection_id",
            name="test_place_connection_name",
            ingress_port=ingress_port,
            egress_port=egress_port,
            quantity=0,
            start_time=datetime.datetime.fromtimestamp(0),
            end_time=datetime.datetime.fromtimestamp(0),
            status="fail",
            complete=False,
        )

        response = self.client.open(
            "/SDX-Controller/1.0.0/conection",
            method="POST",
            data=json.dumps(connection),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

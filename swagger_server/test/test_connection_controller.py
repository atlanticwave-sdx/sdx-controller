# coding: utf-8

from __future__ import absolute_import

import datetime

from flask import json

from sdxdatamodel.models.connection import Connection
# from sdxdatamodel.models.location import Location
# from sdxdatamodel.models.node import Node
from sdxdatamodel.models.port import Port
from swagger_server.test import BaseTestCase


class TestConnectionControllerBasic(BaseTestCase):
    """Some basic tests for ConnectionController."""

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


class TestPlaceConnectionFailures(BaseTestCase):
    """
    Additional tests for ConnectionController.

    In order to place a connection successfully, we'll need to do some
    setup.  There are several places placing a connection can go
    wrong, both during setup and during connection placement.  We
    should be testing all of that as much as possible.  Hence this
    separate class with a different setup step.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass   

    def test_place_connection(self):
        """Test case for place_connection

        Place an connection request from the SDX-Controller
        """
        # location = Location(
        #     address="Unknown",
        #     latitude=0.0,
        #     longitude=0.0,
        # )

        # # location validator expects JSON
        # location = {
        #     "address": "Unknown",
        #     "latitude": "latitude",
        #     "longitude": "longitude",
        # }

        # ingress_port = Port(
        #     id="ingress_port_id",
        #     name="ingress_port_name",
        #     # node="ingress_node_name",
        #     # status="unknown",
        #     # state="unknown",
        # )

        # # Port validator expects JSON
        # ingress_port = {
        #     "id": "ingress_port_id",
        #     "name": "ingress_port_name",
        #     "node": "ingress_node_name",
        #     "status": "unknown",
        # }

        ingress_port = {
            "id": "ingress_port_id",
            "name": "ingress_port_name",
            "node": "ingress_node_name",
            "status": "unknown",
        }

        # ingress_node = Node(
        #     id="ingress_node_id",
        #     name="ingress_node_name",
        #     location=location,
        #     ports=[ingress_port],
        # )

        # egress_port = Port(
        #     id="egress_port_id",
        #     name="egress_port_name",
        #     # node="egress_node_name",
        #     # status="unknown",
        #     # state="unknown",
        # )

        egress_port = {
            "id": "egress_port_id",
            "name": "egress_port_name",
            "node": "egress_node_name",
            "status": "unknown",            
        }

        # Port validator expects JSON?
        # egress_port = {
        #     "id": "egress_port_id",
        #     "name": "egress_port_name",
        #     "node": "egress_node_name",
        #     "status": "unknown",
        #     # "state": "unknown",
        # }

        # egress_node = Node(
        #     id="egress_node_id",
        #     name="egress_node_name",
        #     location=location,
        #     ports=[egress_port],
        # )

        # connection = Connection(
        #     id="test_place_connection_id",
        #     name="test_place_connection_name",
        #     ingress_port=ingress_port,
        #     egress_port=egress_port,
        #     quantity=0,
        #     start_time=datetime.datetime.fromtimestamp(0),
        #     end_time=datetime.datetime.fromtimestamp(0),
        #     status="fail",
        #     complete=False,
        # )

        # payload = json.dumps(connection)

        connection = {
            "id": "test_place_connection_id",
            "name": "test_place_connection_name",
            "ingress_port": ingress_port,
            "egress_port": egress_port,
            "quantity": 1,
            # "start_time": stdatetime.datetime.fromtimestamp(0),
            # "end_time": datetime.datetime.fromtimestamp(0),
            "status": "scheduled",
            # "complete": False,
        }

        # payload = connection
        print(connection)
        
        payload = json.dumps(connection)
        print(f"payload: {payload}")
        
        response = self.client.open(
            "/SDX-Controller/1.0.0/conection",
            method="POST",
            data=payload,
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

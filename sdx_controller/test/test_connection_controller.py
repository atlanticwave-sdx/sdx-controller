# coding: utf-8

from __future__ import absolute_import

import unittest

from flask import json

from sdx_controller.models.connection import Connection  # noqa: E501
from sdx_controller.test import BaseTestCase, TestData

BASE_PATH = "/SDX-Controller/1.0.0"


class TestConnectionController(BaseTestCase):
    """ConnectionController integration test stubs"""

    def test_delete_connection(self):
        """
        Test case for delete_connection.

        Delete connection order by ID.
        """
        connection_id = 2
        response = self.client.open(
            f"{BASE_PATH}/connection/{connection_id}",
            method="DELETE",
        )
        self.assert200(response, f"Response body is : {response.data.decode('utf-8')}")

    def test_getconnection_by_id(self):
        """
        Test case for getconnection_by_id.

        Find connection by ID.
        """
        connection_id = 10
        response = self.client.open(
            f"{BASE_PATH}/connection/{connection_id}",
            method="GET",
        )

        # The connection_id we've supplied above should not exist.
        # TODO: test for existing connection_id.  See
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/34.
        self.assertStatus(response, 204)

    def test_place_connection_no_topology(self):
        """
        Test case for place_connection.

        Place a connection request with no topology present.
        """
        body = Connection()

        response = self.client.open(
            f"{BASE_PATH}/connection",
            method="POST",
            data=json.dumps(body),
            content_type="application/json",
        )
        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect 400 failure because the request is incomplete: the
        # bare minimum connection request we sent does not have
        # ingress port data, etc., for example.
        self.assertStatus(response, 400)

    def __test_with_one_topology(self, topology_file):
        """
        A helper method to test place_connection() with just one topology.
        """
        topology = json.loads(topology_file.read_text())
        self.te_manager.add_topology(topology)

        request = TestData.CONNECTION_REQ.read_text()

        response = self.client.open(
            f"{BASE_PATH}/connection",
            method="POST",
            data=request,
            content_type="application/json",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect 400 failure, because TEManager do not have enough
        # topology data.
        self.assertStatus(response, 400)

    def test_place_connection_with_amlight(self):
        """
        Test place_connection() with just Amlight topology.
        """
        self.__test_with_one_topology(TestData.TOPOLOGY_FILE_AMLIGHT)

    def test_place_connection_with_sax(self):
        """
        Test place_connection() with just SAX topology.
        """
        self.__test_with_one_topology(TestData.TOPOLOGY_FILE_SAX)

    def test_place_connection_with_zaoxi(self):
        """
        Test place_connection() with just ZAOXI topology.
        """
        self.__test_with_one_topology(TestData.TOPOLOGY_FILE_ZAOXI)

    def test_place_connection_with_three_topologies(self):
        """
        Test case for place_connection.

        Place a connection request when some topologies are known.
        """
        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ]:
            topology = json.loads(topology_file.read_text())
            self.te_manager.add_topology(topology)

        request = TestData.CONNECTION_REQ.read_text()

        response = self.client.open(
            f"{BASE_PATH}/connection",
            method="POST",
            data=request,
            content_type="application/json",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect 200 success because TEManager now should be properly
        # set up with all the expected topology data.
        self.assertStatus(response, 200)

    def test_place_connection_with_three_topologies_added_in_sequence(self):
        """
        Test case for place_connection.

        Place the same connection request while adding topologies.
        """
        for idx, topology_file in enumerate(
            [
                TestData.TOPOLOGY_FILE_AMLIGHT,
                TestData.TOPOLOGY_FILE_SAX,
                TestData.TOPOLOGY_FILE_ZAOXI,
            ]
        ):
            topology = json.loads(topology_file.read_text())
            self.te_manager.add_topology(topology)

            request = TestData.CONNECTION_REQ.read_text()

            response = self.client.open(
                f"{BASE_PATH}/connection",
                method="POST",
                data=request,
                content_type="application/json",
            )

            print(f"Response body is : {response.data.decode('utf-8')}")

            if idx in [0, 1]:
                # Expect 400 failure because TEManager do not have all
                # the topologies yet.
                self.assertStatus(response, 400)
            if idx == 200:
                # Expect 200 success now that TEManager should be set
                # up with all the expected topology data.
                self.assertStatus(response, 200)


if __name__ == "__main__":
    unittest.main()

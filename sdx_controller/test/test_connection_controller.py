# coding: utf-8

from __future__ import absolute_import

import unittest
import uuid
from unittest.mock import patch

from flask import json

from sdx_controller.models.connection import Connection
from sdx_controller.test import BaseTestCase, TestData

BASE_PATH = "/SDX-Controller/1.0.0"


class TestConnectionController(BaseTestCase):
    """ConnectionController integration test stubs"""

    def test_delete_connection_no_setup(self):
        """
        Test case for delete_connection().

        Delete connection order by ID.
        """
        connection_id = 2
        response = self.client.open(
            f"{BASE_PATH}/connection/{connection_id}",
            method="DELETE",
        )
        self.assert404(response, f"Response body is : {response.data.decode('utf-8')}")

    def __add_the_three_topologies(self):
        """
        A helper to add the three known topologies.
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

    def test_delete_connection_with_setup(self):
        """
        Test case for delete_connection()

        Set up a connection request, get the connection ID from the
        response, and then do `DELETE /connection/:connection_id`
        """
        # set up temanager connection first
        self.__add_the_three_topologies()

        request_body = TestData.CONNECTION_REQ.read_text()

        connection_response = self.client.open(
            f"{BASE_PATH}/connection",
            method="POST",
            data=request_body,
            content_type="application/json",
        )

        print(f"Response body: {connection_response.data.decode('utf-8')}")

        self.assertStatus(connection_response, 200)

        connection_id = connection_response.get_json().get("connection_id")
        print(f"Deleting request_id: {connection_id}")

        delete_response = self.client.open(
            f"{BASE_PATH}/connection/{connection_id}",
            method="DELETE",
        )

        self.assert200(
            delete_response,
            f"Response body is : {delete_response.data.decode('utf-8')}",
        )

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
        self.assertStatus(response, 404)

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

    def test_place_connection_no_id(self):
        """
        Test place_connection() with a request that has no ID field.
        """
        # Remove ID
        request = json.loads(TestData.CONNECTION_REQ.read_text())
        request.pop("id")
        request = json.dumps(request)

        print(f"request: {request} {type(request)}")

        response = self.client.open(
            f"{BASE_PATH}/connection",
            method="POST",
            data=request,
            content_type="application/json",
        )

        print(f"response: {response}")
        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect a 400 response because the required ID field is
        # missing from the request.
        self.assertStatus(response, 400)

        # JSON response should have a body like:
        #
        # {
        #   "detail": "'id' is a required property",
        #   "status": 400,
        #   "title": "Bad Request",
        #   "type": "about:blank"
        # }

        response = response.get_json()
        self.assertEqual(response["status"], 400)
        self.assertEqual(response["detail"], "'id' is a required property")

    def test_place_connection_with_three_topologies(self):
        """
        Test case for place_connection.

        Place a connection request when some topologies are known.
        """
        self.__add_the_three_topologies()

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

        Keep placing the same connection request while adding
        topologies.  The first few requests should fail, and the final
        one eventually succeed.
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

    def test_z100_getconnection_by_id_expect_404(self):
        """
        Test getconnection_by_id with a non-existent connection ID.
        """
        # Generate a random ID.
        connection_id = uuid.uuid4()
        response = self.client.open(
            f"{BASE_PATH}/connection/{connection_id}",
            method="GET",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")

        self.assertStatus(response, 404)

    def test_z100_getconnection_by_id_expect_200(self):
        """
        Test getconnection_by_id with a non-existent connection ID.
        """

        self.__add_the_three_topologies()

        request_body = TestData.CONNECTION_REQ.read_text()

        post_response = self.client.open(
            f"{BASE_PATH}/connection",
            method="POST",
            data=request_body,
            content_type="application/json",
        )

        print(f"Response body: {post_response.data.decode('utf-8')}")

        self.assertStatus(post_response, 200)

        connection_id = post_response.get_json().get("connection_id")
        print(f"Got connection_id: {connection_id}")

        # Now try `GET /connection/{connection_id}`
        get_response = self.client.open(
            f"{BASE_PATH}/connection/{connection_id}",
            method="GET",
        )

        print(f"Response body: {get_response.data.decode('utf-8')}")

        self.assertStatus(get_response, 200)

    @patch("sdx_controller.utils.db_utils.DbUtils.get_all_entries_in_collection")
    def test_z105_getconnections_fail(self, mock_get_all_entries):
        """Test case for getconnections."""
        mock_get_all_entries.return_value = {}
        response = self.client.open(
            f"{BASE_PATH}/connections",
            method="GET",
        )
        self.assertStatus(response, 404)

    def test_z105_getconnections_success(self):
        """Test case for getconnections."""
        response = self.client.open(
            f"{BASE_PATH}/connections",
            method="GET",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")
        self.assertStatus(response, 200)

        assert len(response.json) == 1


if __name__ == "__main__":
    unittest.main()

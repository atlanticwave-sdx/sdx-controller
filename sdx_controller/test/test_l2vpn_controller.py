# coding: utf-8

from __future__ import absolute_import

import unittest
import uuid
from unittest.mock import patch

from flask import json
from six import BytesIO

from sdx_controller.models.connection import Connection
from sdx_controller.models.connection_v2 import ConnectionV2
from sdx_controller.models.l2vpn_body import L2vpnBody  # noqa: E501
from sdx_controller.test import BaseTestCase, TestData

BASE_PATH = "/SDX-Controller"


class TestL2vpnController(BaseTestCase):
    """L2vpnController integration test stubs"""

    def test_delete_connection_no_setup(self):
        """
        Test case for delete_connection().

        Delete connection order by ID.
        """
        service_id = 2
        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0/{service_id}",
            method="DELETE",
        )
        self.assert404(response, f"Response body is : {response.data.decode('utf-8')}")

    def __add_the_three_topologies(self):
        """
        A helper to add the three known topologies.
        """
        for idx, topology_file in enumerate(
            [
                TestData.TOPOLOGY_FILE_AMLIGHT_USER_PORT,
                TestData.TOPOLOGY_FILE_SAX,
                TestData.TOPOLOGY_FILE_ZAOXI,
            ]
        ):
            topology = json.loads(topology_file.read_text())
            print(f"Adding topology: {topology.get('id')}")
            self.te_manager.add_topology(topology)

    def test_delete_connection_with_setup(self):
        """
        Test case for delete_connection()

        Set up a connection request, get the connection ID from the
        response, and then do `DELETE /l2vpn/1.0/:service_id`
        """
        # set up temanager connection first
        self.__add_the_three_topologies()

        request_body = TestData.CONNECTION_REQ.read_text()

        connection_response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="POST",
            data=request_body,
            content_type="application/json",
        )

        print(f"Response body: {connection_response.data.decode('utf-8')}")

        self.assertStatus(connection_response, 200)

        service_id = connection_response.get_json().get("service_id")
        print(f"Deleting request_id: {service_id}")

        delete_response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0/{service_id}",
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
        service_id = 10
        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0/{service_id}",
            method="GET",
        )

        # The service_id we've supplied above should not exist.
        # TODO: test for existing service_id.  See
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/34.
        self.assertStatus(response, 404)

    def test_place_connection_no_topology(self):
        """
        Test case for place_connection.

        Place a connection request with no topology present.
        """
        body = Connection()

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="POST",
            data=json.dumps(body),
            content_type="application/json",
        )
        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect 400 failure because the request is incomplete: the
        # bare minimum connection request we sent does not have
        # ingress port data, etc., for example.
        self.assertStatus(response, 400)

    def test_place_connection_v2_no_topology(self):
        """
        Test case for place_connection.

        Place a connection request with no topology present.
        """
        body = ConnectionV2()

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
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
            f"{BASE_PATH}/l2vpn/1.0",
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
            f"{BASE_PATH}/l2vpn/1.0",
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
        self.assertIn("is not valid under any of the given schemas", response["detail"])

    def test_place_connection_with_three_topologies(self):
        """
        Test case for place_connection.

        Place a connection request when some topologies are known.
        """
        self.__add_the_three_topologies()

        request = TestData.CONNECTION_REQ.read_text()

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
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
                f"{BASE_PATH}/l2vpn/1.0",
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

    def test_place_connection_v2_with_three_topologies_400_response(self):
        """
        Test case for connection request format v2.
        """
        self.__add_the_three_topologies()

        # No solution for this request.
        request = TestData.CONNECTION_REQ_V2_L2VPN_P2P.read_text()

        # The example connection request ("test-l2vpn-p2p-v2.json")
        # carries an ID field for testing purposes, but the actual v2
        # format does not have an ID field.  So we remove the ID from
        # the request.
        request_json = json.loads(request)
        original_request_id = request_json.pop("id")
        print(f"original_request_id: {original_request_id}")

        new_request = json.dumps(request_json)
        print(f"new_request: {new_request}")

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="POST",
            data=new_request,
            content_type="application/json",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect a 400 response because PCE would not be able to find
        # a solution for the connection request.
        self.assertStatus(response, 400)
        self.assertEqual(
            response.get_json().get("status"),
            "Failure",
        )
        self.assertEqual(
            response.get_json().get("reason"), "Could not generate a traffic matrix"
        )

        # Returned connection ID should be different from the original
        # request ID.
        service_id = response.get_json().get("service_id")
        self.assertNotEqual(service_id, original_request_id)

    def test_place_connection_v2_with_three_topologies_200_response(self):
        """
        Test case for connection request format v2.  This request
        should be able to find a path.
        """
        self.__add_the_three_topologies()

        # There should be solution for this request.
        request = json.loads(TestData.CONNECTION_REQ_V2_AMLIGHT_ZAOXI.read_text())

        # Remove any existing request ID.
        original_request_id = request.pop("id")
        print(f"original_request_id: {original_request_id}")

        # TODO: As a temporary workaround until the original
        # connection request is corrected in datamodel, we modify the
        # connection request for this test so that we have a solvable
        # one. The original one asks for (1) a VLAN that is not
        # present on the ingress port (777), and (2) a range ("55:90")
        # on the egress port.  This is an unsolvable request because
        # of (1), and an invalid one because of (2) since both ports
        # have to ask for either a range or a single VLAN.
        request["endpoints"][0]["vlan"] = "100"
        request["endpoints"][1]["vlan"] = "100"

        new_request = json.dumps(request)
        print(f"new_request: {new_request}")

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="POST",
            data=new_request,
            content_type="application/json",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")

        # Expect a 200 response because PCE should be able to find a
        # solution for the connection request.
        self.assertStatus(response, 200)
        self.assertEqual(
            response.get_json().get("status"),
            "OK",
        )
        self.assertEqual(
            response.get_json().get("reason"),
            "Connection published",
        )

        # Returned connection ID should be different from the original
        # request ID.
        service_id = response.get_json().get("service_id")
        self.assertNotEqual(service_id, original_request_id)

    def test_place_connection_v2_with_any_vlan_in_request(self):
        """
        Test that we get a valid response when the VLAN requested for
        is "any".
        """
        self.__add_the_three_topologies()

        connection_request = """
            {
                "name": "new-connection",
                "endpoints": [
                    {
                        "port_id": "urn:sdx:port:amlight.net:A1:1",
                        "vlan": "any"
                    },
                    {
                        "port_id": "urn:sdx:port:amlight:B1:1",
                        "vlan": "any"
                    }
                ]
            }
        """

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="POST",
            data=connection_request,
            content_type="application/json",
        )

        print(f"POST response body is : {response.data.decode('utf-8')}")
        print(f"POST Response JSON is : {response.get_json()}")

        self.assertStatus(response, 200)

        service_id = response.get_json().get("service_id")

        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0/{service_id}",
            method="GET",
        )

        print(f"GET response body is : {response.data.decode('utf-8')}")
        print(f"GET response JSON is : {response.get_json()}")

        self.assertStatus(response, 200)

        # Expect a response like this:
        #
        # {
        #     "c73da8e1-5d03-4620-a1db-7cdf23e8978c": {
        #         "service_id": "c73da8e1-5d03-4620-a1db-7cdf23e8978c",
        #         "name": "new-connection",
        #         "endpoints": [
        #          {
        #             "port_id": "urn:sdx:port:amlight.net:A1:1",
        #             "vlan": "150"
        #          },
        #          {
        #             "port_id": "urn:sdx:port:amlight:B1:1",
        #             "vlan": "300"}
        #         ],
        #     }
        # }
        #
        # See https://sdx-docs.readthedocs.io/en/latest/specs/provisioning-api-1.0.html#request-format-2

        blob = response.get_json()
        service = blob.get(service_id)

        self.assertIsNotNone(service)
        self.assertEqual(service_id, service.get("service_id"))

        endpoints = service.get("endpoints")
        print(f"response endpoints: {endpoints}")

        self.assertEqual(len(endpoints), 2)

        # What were the original port_ids now?
        request_dict = json.loads(connection_request)
        requested_port0 = request_dict.get("endpoints")[0].get("port_id")
        requested_port1 = request_dict.get("endpoints")[1].get("port_id")

        # print(f"requested_port0: {requested_port0}")
        # print(f"requested_port1: {requested_port1}")

        # # TODO: There seems to be a little bit of inconsistency in
        # # port names in amlight "user" topology file, present in
        # # datamodel repository. Some ports have IDs like
        # # `"urn:sdx:port:amlight:B1:1"` - note the missing ".net".
        # # Just skip the assertion for now.
        # self.assertEqual(endpoints[0].get("port_id"), requested_port0)
        # self.assertEqual(endpoints[1].get("port_id"), requested_port1)

        def is_integer(s: str):
            """
            Retrun True if `s` wraps a number as a string.
            """
            try:
                int(s)
                return True
            except:
                return False

        vlan0 = endpoints[0].get("vlan")
        vlan1 = endpoints[1].get("vlan")

        self.assertIsInstance(vlan0, str)
        self.assertTrue(is_integer(vlan0))

        self.assertIsInstance(vlan1, str)
        self.assertTrue(is_integer(vlan1))

    def test_z100_getconnection_by_id_expect_404(self):
        """
        Test getconnection_by_id with a non-existent connection ID.
        """
        # Generate a random ID.
        service_id = uuid.uuid4()
        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0/{service_id}",
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
            f"{BASE_PATH}/l2vpn/1.0",
            method="POST",
            data=request_body,
            content_type="application/json",
        )

        print(f"Response body: {post_response.data.decode('utf-8')}")

        self.assertStatus(post_response, 200)

        service_id = post_response.get_json().get("service_id")
        print(f"Got service_id: {service_id}")

        # Now try `GET /l2vpn/1.0/{service_id}`
        get_response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0/{service_id}",
            method="GET",
        )

        print(f"Response body: {get_response.data.decode('utf-8')}")

        self.assertStatus(get_response, 200)

    @patch("sdx_controller.utils.db_utils.DbUtils.get_all_entries_in_collection")
    def test_z105_getconnections_fail(self, mock_get_all_entries):
        """Test case for getconnections."""
        mock_get_all_entries.return_value = {}
        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="GET",
        )
        self.assertStatus(response, 404)

    def test_z105_getconnections_success(self):
        """Test case for getconnections."""
        response = self.client.open(
            f"{BASE_PATH}/l2vpn/1.0",
            method="GET",
        )

        print(f"Response body is : {response.data.decode('utf-8')}")
        self.assertStatus(response, 200)

        assert len(response.get_json()) != 0


if __name__ == "__main__":
    unittest.main()

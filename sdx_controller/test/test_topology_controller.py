# coding: utf-8

from __future__ import absolute_import

from sdx_datamodel.constants import Constants, MongoCollections

from sdx_controller.test import BaseTestCase


class TestTopologyController(BaseTestCase):
    """TopologyController integration test stubs"""

    def test_get_topology(self):
        """Test case for get_topology
        get an existing topology
        """
        self.te_manager.topology_manager.clear_topology()
        self.db_instance.delete_one_entry(
            (MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY)
        )
        response = self.client.open("/SDX-Controller/topology", method="GET")
        # There's nothing corresponding to `latest_topo` in DB at this
        # point, so we get a 204 No Content response.  We should
        # probably get a 404 Not Found response though.  See
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/37
        self.assertStatus(response, 204)

    def test_get_topologyby_version(self):
        """Test case for get_topologyby_version

        Find topology by version
        """
        query_string = [("topology_id", 789)]
        response = self.client.open(
            "/SDX-Controller/topology/{version}".format(version=789),
            method="GET",
            query_string=query_string,
        )
        # No topology exists; we should get a 404.
        self.assertStatus(response, 404)

    def test_topology_version(self):
        """Test case for topology_version

        Finds topology version
        """
        query_string = [("topology_id", "test:topology:test_topology.net")]
        response = self.client.open(
            "/SDX-Controller/topology/version",
            method="GET",
            query_string=query_string,
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()

import json
import os
import unittest

import networkx as nx
from networkx import Graph, MultiGraph
from sdx.datamodel.parsing import *
from sdx.datamodel.parsing.exceptions import DataModelException
from sdx.datamodel.topologymanager.temanager import TEManager
from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.utils.random_connection_generator import RandomConnectionGenerator
from sdx.pce.models import ConnectionRequest, TrafficMatrix, ConnectionSolution

# Topology = GetNetworkToplogy(25,0.4)
# Connection = GetConnection('./tests/data/test_connection.json')
# Solution = './tests/data/test_MC_solution.json'

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TOPOLOGY = os.path.join(TEST_DATA_DIR, "sdx.json")
CONNECTION = os.path.join(TEST_DATA_DIR, "test_request.json")

TOPOLOGY_AMLIGHT = os.path.join(TEST_DATA_DIR, "amlight.json")
TOPOLOGY_SAX = os.path.join(TEST_DATA_DIR, "sax.json")
TOPOLOGY_ZAOXI = os.path.join(TEST_DATA_DIR, "zaoxi.json")

TOPOLOGY_FILE_LIST = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]
TOPOLOGY_FILE_LIST_UPDATE = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]

def make_traffic_matrix(requests: list) -> TrafficMatrix:
    """
    Take the old-style list of lists and make a traffic matrix.
    """
    assert isinstance(requests, list)
    
    new_requests: list(ConnectionRequest) = []

    for request in requests:
        assert isinstance(request, list)
        assert len(request) == 4

        new_requests.append(ConnectionRequest(
            source = request[0],
            destination = request[1],
            required_bandwidth = request[2],
            required_latency = request[3]
        ))

    return TrafficMatrix(connection_requests=new_requests)

class Test_Solver(unittest.TestCase):
    def setUp(self):
        with open(TOPOLOGY, "r", encoding="utf-8") as t:
            topology_data = json.load(t)
        with open(CONNECTION, "r", encoding="utf-8") as c:
            connection_data = json.load(c)

        self.temanager = TEManager(topology_data, connection_data)
        self.graph = self.temanager.generate_graph_te()
        self.connection = self.temanager.generate_connection_te()

    def test_computation(self):
        print(f"Number of nodes: {self.graph.number_of_nodes()}")
        print(f"Graph edges: {self.graph.edges}")
        print(f"Connection[0]: {self.connection[0]}")

        tm = make_traffic_matrix(self.connection)
        print(f"TM: {tm}")

        path, value = TESolver(self.graph, tm).solve()
        print(f"TESolver result: path: {path}, value: {value}")
        self.assertIsInstance(path, ConnectionSolution)
        self.assertEqual(value, 5.0)

        # breakdown = self.temanager.generate_connection_breakdown(result)
        # print(f"Breakdown: {breakdown}")

    def test_computation_breakdown(self):
        try:
            for topology_file in TOPOLOGY_FILE_LIST:
                print(f"Adding Topology: {topology_file}")
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                    self.temanager.manager.add_topology(data)
        except DataModelException as e:
            print(e)
            return False

        self.graph = self.temanager.generate_graph_te()
        self.connection = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(self.connection)
        print(f"Graph connectivity: {conn}")
        num_nodes = self.graph.number_of_nodes()

        path, value = TESolver(self.graph, self.connection).solve()
        print(f"TESolver result: path: {path}, value: {value}")

        self.assertNotEqual(path, None, "No path was computed")

        # TODO: what do we break down here?
        breakdown = self.temanager.generate_connection_breakdown(path)
        print(f"Breakdown: {breakdown}")

    def test_computation_update(self):
        try:
            for topology_file in TOPOLOGY_FILE_LIST:
                print(f"Adding Topology: {topology_file}")
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                    self.temanager.manager.add_topology(data)
        except DataModelException as e:
            print(e)
            return False

        try:
            for topology_file in TOPOLOGY_FILE_LIST_UPDATE:
                print(f"Updating Topology: {topology_file}")
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                    self.temanager.manager.update_topology(data)
        except DataModelException as e:
            print(e)
            return False

        self.graph = self.temanager.generate_graph_te()
        self.connection = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(self.connection)
        print(f"Graph connectivity: {conn}")

        path, value = TESolver(self.graph, self.connection).solve()
        print(f"TESolver result: path: {path}, value: {value}")

        self.assertNotEqual(path, None, "No path was computed")

        # TODO: determine correct input to breakdown method.
        breakdown = self.temanager.generate_connection_breakdown(path)
        print(f"Breakdown: {breakdown}")


if __name__ == "__main__":
    unittest.main()

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

        path, value = TESolver(self.graph, self.connection).solve()
        print(f"TESolver result: path: {path}, value: {value}")
        
        self.assertEqual(value, 5.0)
        # self.assertIsInstance(path, numpy.ndarray)

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
        num_nodes = self.graph.number_of_nodes()

        result = TESolver(self.graph, self.connection).solve()

        print(result)
        breakdown = self.temanager.generate_connection_breakdown(result)
        print(breakdown)


if __name__ == "__main__":
    unittest.main()

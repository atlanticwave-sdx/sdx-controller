import json
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

TOPOLOGY = "./tests/data/sdx.json"
CONNECTION = "./tests/data/test_request.json"

TOPOLOGY_AMLIGHT = "./tests/data/amlight.json"
TOPOLOGY_SAX = "./tests/data/sax.json"
TOPOLOGY_ZAOXI = "./tests/data/zaoxi.json"

topology_file_list_3 = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]
topology_file_list_update = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]


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
        num_nodes = self.graph.number_of_nodes()
        print("num of nodes:" + str(num_nodes))
        print(self.graph.edges)
        print(self.connection[0])

        result = TESolver(self.graph, self.connection).solve()
        print(result)
        # self.assertEqual(self.solution, result)

    def test_computation_breakdown(self):
        try:
            for topology_file in topology_file_list_3:
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                print("Adding Topology:" + topology_file)
                self.temanager.manager.add_topology(data)
        except DataModelException as e:
            print(e)
            return False

        self.graph = self.temanager.generate_graph_te()
        self.connection = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(self.connection)
        print("Graph connectivity:" + str(conn))
        num_nodes = self.graph.number_of_nodes()

        result = TESolver(self.graph, self.connection).solve()

        print(result)
        breakdown = self.temanager.generate_connection_breakdown(result)
        print(breakdown)

    def test_computation_update(self):
        try:
            for topology_file in topology_file_list_3:
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                print("Adding Topology:" + topology_file)
                self.temanager.manager.add_topology(data)
        except DataModelException as e:
            print(e)
            return False

        try:
            for topology_file in topology_file_list_update:
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                print("Updating Topology:" + topology_file)
                self.temanager.manager.update_topology(data)
        except DataModelException as e:
            print(e)
            return False

        self.graph = self.temanager.generate_graph_te()
        self.connection = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(self.connection)
        print("Graph connectivity:" + str(conn))
        num_nodes = self.graph.number_of_nodes()

        result = TESolver(self.graph, self.connection).solve()

        print(result)
        breakdown = self.temanager.generate_connection_breakdown(result)
        print(breakdown)


if __name__ == "__main__":
    unittest.main()

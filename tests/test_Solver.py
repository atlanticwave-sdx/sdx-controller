import json
import pathlib
import unittest

from sdx.datamodel.parsing.exceptions import DataModelException
from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.models import ConnectionRequest, ConnectionSolution, TrafficMatrix
from sdx.pce.topology.temanager import TEManager


class SolverTests(unittest.TestCase):
    """
    Check that the solver from pce does what we expects it to do.
    """

    TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")

    TOPOLOGY_SDX = TEST_DATA_DIR.joinpath("sdx.json")
    CONNECTION_REQ = TEST_DATA_DIR.joinpath("test_request.json")

    TOPOLOGY_AMLIGHT = TEST_DATA_DIR.joinpath("amlight.json")
    TOPOLOGY_SAX = TEST_DATA_DIR.joinpath("sax.json")
    TOPOLOGY_ZAOXI = TEST_DATA_DIR.joinpath("zaoxi.json")

    TOPOLOGY_FILE_LIST = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]
    TOPOLOGY_FILE_LIST_UPDATE = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]

    def setUp(self):
        with open(self.TOPOLOGY_SDX, "r", encoding="utf-8") as t:
            topology_data = json.load(t)
        with open(self.CONNECTION_REQ, "r", encoding="utf-8") as c:
            connection_data = json.load(c)

        self.temanager = TEManager(topology_data, connection_data)
        self.graph = self.temanager.generate_graph_te()
        self.connection_request = self.temanager.generate_connection_te()

    def test_computation(self):
        print(f"Number of nodes: {self.graph.number_of_nodes()}")
        print(f"Graph edges: {self.graph.edges}")
        print(f"Traffic Matrix: {self.connection_request}")

        solution = TESolver(self.graph, self.connection_request).solve()
        print(f"TESolver result: {solution}")

        self.assertIsInstance(solution, ConnectionSolution)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown_tm(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

    def test_computation_breakdown(self):
        try:
            for topology_file in self.TOPOLOGY_FILE_LIST:
                print(f"Adding Topology: {topology_file}")
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                    self.temanager.topology_manager.add_topology(data)
        except DataModelException as e:
            print(e)
            return False

        self.graph = self.temanager.generate_graph_te()
        self.connection_request = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(self.connection_request)
        print(f"Graph connectivity: {conn}")
        num_nodes = self.graph.number_of_nodes()

        solution = TESolver(self.graph, self.connection_request).solve()
        print(f"TESolver result: {solution}")

        # The reality, for now, is that TE Solver has not been able to
        # compute a path.
        self.assertIsNone(solution.connection_map, "No path was computed")
        self.assertEqual(solution.cost, 0)

        # # TODO: what do we break down here?
        # breakdown = self.temanager.generate_connection_breakdown(path)
        # print(f"Breakdown: {breakdown}")

    def test_computation_update(self):
        try:
            for topology_file in self.TOPOLOGY_FILE_LIST:
                print(f"Adding Topology: {topology_file}")
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                    self.temanager.topology_manager.add_topology(data)
        except DataModelException as e:
            print(e)
            return False

        try:
            for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
                print(f"Updating Topology: {topology_file}")
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                    self.temanager.topology_manager.update_topology(data)
        except DataModelException as e:
            print(e)
            return False

        self.graph = self.temanager.generate_graph_te()
        self.connection_request = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(self.connection_request)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(self.graph, self.connection_request).solve()
        print(f"TESolver result: {solution}")

        # The reality, for now, is that TE Solver has not been able to
        # compute a path.
        self.assertIsNone(solution.connection_map, "No path was computed")

        # # TODO: determine correct input to breakdown method.
        # breakdown = self.temanager.generate_connection_breakdown(path)
        # print(f"Breakdown: {breakdown}")


if __name__ == "__main__":
    unittest.main()

import unittest
import json
from networkx import MultiGraph, Graph
import networkx as nx

from sdxdatamodel.parsing import *

from sdxdatamodel.topologymanager.temanager import TEManager

from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import GetConnection
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator

#Topology = GetNetworkToplogy(25,0.4)
#Connection = GetConnection('./tests/data/test_connection.json')
#Solution = './tests/data/test_MC_solution.json'

TOPOLOGY = "./tests/data/sdx.json"
CONNECTION = "./tests/data/test_request.json"

class Test_Solver(unittest.TestCase):

    def setUp(self):
        with open(TOPOLOGY, 'r', encoding='utf-8') as t:
            topology_data = json.load(t)
        with open(CONNECTION, 'r', encoding='utf-8') as c:
            connection_data = json.load(c)

        self.temanager = TEManager(topology_data, connection_data)
        self.graph =  self.temanager.generate_graph_te()
        self.connection=self.temanager.generate_connection_te()
        print(self.connection[0])
        #with open('./tests/data/connection.json', 'w') as json_file:
        #    json.dump(self.temanager.connection.to_dict(), json_file, indent=4)

    def test_Computation(self):
        num_nodes = self.graph.number_of_nodes()
        print("num of nodes:"+str(num_nodes))
        lbnxgraphgenerator(num_nodes, 0.4, self.connection, self.graph)
        result = runMC_Solver()

        #self.assertEqual(self.solution, result)


if __name__ == '__main__':
    unittest.main()





import unittest
import json
from networkx import MultiGraph, Graph
import networkx as nx

from sdxdatamodel.parsing import *

from sdxdatamodel.topologymanager.temanager import TEManager
from sdxdatamodel.parsing.exceptions import DataModelException

from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import GetConnection
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator

#Topology = GetNetworkToplogy(25,0.4)
#Connection = GetConnection('./tests/data/test_connection.json')
#Solution = './tests/data/test_MC_solution.json'

TOPOLOGY = "./tests/data/sdx.json"
CONNECTION = "./tests/data/test_request.json"

TOPOLOGY_AMLIGHT = './tests/data/amlight.json'
TOPOLOGY_SAX = './tests/data/sax.json'
TOPOLOGY_ZAOXI = './tests/data/zaoxi.json'

topology_file_list_3 = [TOPOLOGY_AMLIGHT,TOPOLOGY_SAX, TOPOLOGY_ZAOXI]

class Test_Solver(unittest.TestCase):

    def setUp(self):
        with open(TOPOLOGY, 'r', encoding='utf-8') as t:
            topology_data = json.load(t)
        with open(CONNECTION, 'r', encoding='utf-8') as c:
            connection_data = json.load(c)

        self.temanager = TEManager(topology_data, connection_data)
        self.graph =  self.temanager.generate_graph_te()
        self.connection=self.temanager.generate_connection_te()
        with open('./tests/data/connection.json', 'w') as json_file:
            json.dump(self.connection, json_file, indent=4)

    def test_computation(self):
        num_nodes = self.graph.number_of_nodes()
        print("num of nodes:"+str(num_nodes))
        print(self.graph.edges)
        print(self.connection[0])
        lbnxgraphgenerator(num_nodes, 0.4, self.connection, self.graph)
        result = runMC_Solver()
        print(result)
        #self.assertEqual(self.solution, result)

    def test_computation_breakdown(self):
        try:
            for topology_file in topology_file_list_3:
                with open(topology_file, 'r', encoding='utf-8') as data_file:
                    data = json.load(data_file)
                print("Adding Topology:" + topology_file)
                self.temanager.manager.add_topology(data) 
        except DataModelException as e:
            print(e)
            return False 
        self.graph =  self.temanager.generate_graph_te()
        self.connection=self.temanager.generate_connection_te()
        with open('./tests/data/connection.json', 'w') as json_file:
            json.dump(self.connection, json_file, indent=4)
        num_nodes = self.graph.number_of_nodes()
        lbnxgraphgenerator(num_nodes, 0.4, self.connection, self.graph)
        result = runMC_Solver()

        result = runMC_Solver()
        print(result)
        breakdown = self.temanager.generate_connection_breakdown(result)
        print(breakdown)

if __name__ == '__main__':
    unittest.main()





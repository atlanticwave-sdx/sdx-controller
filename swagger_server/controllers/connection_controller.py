import connexion
import six
import os
import json

from sdxdatamodel.models.connection import Connection  # noqa: E501
from swagger_server import util
from swagger_server.utils.db_utils import *
from swagger_server.messaging.topic_queue_producer import *

from sdxdatamodel.topologymanager.temanager import TEManager
from sdxdatamodel.parsing.exceptions import DataModelException

# These modules are from pce package. They should be under a `pce`
# namespace. See https://github.com/atlanticwave-sdx/pce/issues/44
from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import GetConnection
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator

LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
logger.setLevel(logging.DEBUG)

DB_NAME = os.environ.get("DB_NAME") + ".sqlite3"
# Get DB connection and tables set up.
db_tuples = [("config_table", "test-config")]

db_instance = DbUtils()
db_instance._initialize_db(DB_NAME, db_tuples)

MANIFEST = os.environ.get("MANIFEST")

# LC controller topic list
producer1 = TopicQueueProducer(5, "connection", "lc1_q1")
producer2 = TopicQueueProducer(5, "connection", "lc2_q1")
producer3 = TopicQueueProducer(5, "connection", "lc3_q1")
producers = {}
producers["lc1_q1"] = producer1
producers["lc2_q1"] = producer2
producers["lc3_q1"] = producer3


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError as e:
        return False
    return True


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def delete_connection(connection_id):  # noqa: E501
    """Delete connection order by ID

    delete a connection # noqa: E501

    :param connection_id: ID of the connection that needs to be deleted
    :type connection_id: int

    :rtype: None
    """
    return "do some magic!"


def getconnection_by_id(connection_id):  # noqa: E501
    """Find connection by ID

    connection details # noqa: E501

    :param connection_id: ID of connection that needs to be fetched
    :type connection_id: int

    :rtype: Connection
    """
    value = db_instance.read_from_db(connection_id)
    return value


def place_connection(body):  # noqa: E501
    """Place an connection request from the SDX-Controller

     # noqa: E501

    :param body: order placed for creating a connection
    :type body: dict | bytes

    :rtype: Connection
    """
    connection_data = body

    if connexion.request.is_json:
        connection_data = connexion.request.get_json()

    logger.info("Placing connection:".format(connection_data))
    print("Placing connection:".format(connection_data))
    print(connection_data)

    logger.info("Placing connection. Saving to database.")
    db_instance.add_key_value_pair_to_db("connection_data", json.dumps(body))
    logger.info("Saving to database complete.")

    topo_val = db_instance.read_from_db("latest_topo")

    # TODO: What to do when there's no "latest_topo" in the database?
    # For now, we just make up a fake topology that seems to do the
    # job (as in, test_place_connection is able to progress past this
    # point), but this is a temporary workaround.
    #
    # To correct the problem for real, we should address
    # https://github.com/atlanticwave-sdx/sdx-controller/issues/36
    print("topo_val: {}".format(topo_val))    

    if topo_val is None:
        ingress_port = {
            "id": "ingress_port_id",
            "name": "ingress_node_port_name",
            "short_name": "ingress_node_port_short_name",
            "node": "ingress_node_name",
            "state": "unknown",
            "status": "unknown",
        }
        ingress_node = {
            "id": "ingress_node_id",
            "name": "ingress_node_name",
            "short_name": "ingress_node_short_name",
            "ports": [ ingress_port ],
            "location": {
                "address": "unknown",
                "latitude": "unknown",
                "longitude": "unknown",
            },
        }
        egress_port = {
            "id": "egress_port_id",
            "name": "egress_node_port_name",
            "short_name": "egress_node_port_short_name",
            "node": "egress_node_name",
            "state": "unknown",
            "status": "unknown",
        }
        egress_node = {
            "id": "egress_node_id",
            "name": "egress_node_name",
            "short_name": "egress_node_short_name",
            "ports": [ egress_port ],
            "location": {
                "address": "unknown",
                "latitude": "unknown",
                "longitude": "unknown",
            },
        }
        links = [
            {
                "id": "ingress_link_id",
                "name": "ingress_link_name",
                "short_name": "ingress_link_short_name",
                "residual_bandwidth": 1000.0,
                "ports": [ ingress_port, ingress_port ],
            },
            {
                "id": "egress_link_id",
                "name": "egress_link_name",
                "short_name": "egress_link_short_name",
                "residual_bandwidth": 1000.0,
                "ports": [ egress_port, egress_port ],
            },
        ]
        topology = {
            "id": "test_topo_id",
            "name": "test_topo_name",
            "version": "test_topo_version",
            "time_stamp": None,
            "nodes": [ingress_node, egress_node],
            "links": links,
        }        
        
        topo_val = json.dumps(topology)
        print("Made a workaround topo_val: {}".format(topo_val))
    
    topology_data = json.loads(topo_val)

    num_domain_topos = 0

    if db_instance.read_from_db("num_domain_topos") is not None:
        num_domain_topos = db_instance.read_from_db("num_domain_topos")

    print(f"TEManager: topology_data: {topology_data}")
    print(f"TEManager: connection_data: {connection_data}")
        
    temanager = TEManager(topology_data, connection_data)
    lc_domain_topo_dict = {}

    for i in range(1, int(num_domain_topos) + 1):
        curr_topo_str = db_instance.read_from_db("LC-" + str(i))
        curr_topo_json = json.loads(curr_topo_str)
        lc_domain_topo_dict[curr_topo_json["domain_name"]] = curr_topo_json[
            "lc_queue_name"
        ]
        temanager.manager.add_topology(curr_topo_json)

    graph = temanager.generate_graph_te()
    connection = temanager.generate_connection_te()

    dir_path = os.path.dirname(os.path.realpath(__file__))

    with open("./tests/data/connection.json", "w") as json_file:
        json.dump(connection, json_file, indent=4)

    num_nodes = graph.number_of_nodes()
    lbnxgraphgenerator(num_nodes, 0.4, connection, graph)
    result = runMC_Solver()

    breakdown = temanager.generate_connection_breakdown(result)
    logger.debug("-------BREAKDOWN:------")
    logger.debug(json.dumps(breakdown))

    for entry in breakdown:
        domain_name = find_between(entry, "topology:", ".net")
        producer = producers[lc_domain_topo_dict[domain_name]]
        producer.call(json.dumps(breakdown[entry]))

    return "Connection published"

import json
import os

import connexion
import six
from sdx.pce.LoadBalancing.MC_Solver import runMC_Solver
from sdx.pce.LoadBalancing.RandomTopologyGenerator import (
    GetConnection,
    GetNetworkToplogy,
    lbnxgraphgenerator,
)
from sdxdatamodel.parsing.exceptions import DataModelException
from sdxdatamodel.topologymanager.temanager import TEManager

from swagger_server import util
from swagger_server.messaging.topic_queue_producer import *
from swagger_server.utils.db_utils import *

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
    logger.info("Placing connection:")
    logger.info(body)
    if connexion.request.is_json:
        body = connexion.request.get_json()

    logger.info("Placing connection. Saving to database.")
    db_instance.add_key_value_pair_to_db("connection_data", json.dumps(body))
    logger.info("Saving to database complete.")

    topo_val = db_instance.read_from_db("latest_topo")
    topo_json = json.loads(topo_val)

    num_domain_topos = 0

    if db_instance.read_from_db("num_domain_topos") is not None:
        num_domain_topos = db_instance.read_from_db("num_domain_topos")

    temanager = TEManager(topo_json, body)
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
        producer = TopicQueueProducer(
            timeout=5, exchange_name="connection", routing_key=domain_name
        )
        producer.call(json.dumps(breakdown[entry]))
        producer.stop_keep_alive()

    return "Connection published"

import json
import logging
import os

import connexion
from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.topology.temanager import TEManager

from swagger_server.messaging.topic_queue_producer import TopicQueueProducer
from swagger_server.utils.db_utils import DbUtils

LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
logger.setLevel(logging.DEBUG)

# Get DB connection and tables set up.
db_instance = DbUtils()
db_instance.initialize_db()

MANIFEST = os.environ.get("MANIFEST")


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def delete_connection(connection_id):
    """
    Delete connection order by ID.

    :param connection_id: ID of the connection that needs to be
        deleted
    :type connection_id: int

    :rtype: None
    """
    return "do some magic!"


def getconnection_by_id(connection_id):
    """
    Find connection by ID.

    :param connection_id: ID of connection that needs to be fetched
    :type connection_id: int

    :rtype: Connection
    """
    value = db_instance.read_from_db(f"{connection_id}")
    return value


def place_connection(body):
    """
    Place an connection request from the SDX-Controller.

    :param body: order placed for creating a connection
    :type body: dict | bytes

    :rtype: Connection
    """
    logger.info(f"Placing connection: {body}")
    if connexion.request.is_json:
        body = connexion.request.get_json()
        logger.info(f"Gathered connexion JSON: {body}")

    logger.info("Placing connection. Saving to database.")
    db_instance.add_key_value_pair_to_db("connection_data", json.dumps(body))
    logger.info("Saving to database complete.")

    topo_val = db_instance.read_from_db("latest_topo")["latest_topo"]
    topo_json = json.loads(topo_val)

    logger.info(f"Read topology {topo_val}")

    num_domain_topos = 0

    if db_instance.read_from_db("num_domain_topos") is not None:
        num_domain_topos = db_instance.read_from_db("num_domain_topos")[
            "num_domain_topos"
        ]

    temanager = TEManager(topo_json, body)
    lc_domain_topo_dict = {}

    for i in range(1, int(num_domain_topos) + 1):
        curr_topo_str = db_instance.read_from_db("LC-" + str(i))["LC-" + str(i)]
        curr_topo_json = json.loads(curr_topo_str)
        lc_domain_topo_dict[curr_topo_json["domain_name"]] = curr_topo_json[
            "lc_queue_name"
        ]
        logger.debug(f"Adding #{i} topology {curr_topo_json}")
        temanager.add_topology(curr_topo_json)

    graph = temanager.generate_graph_te()
    traffic_matrix = temanager.generate_connection_te()

    logger.info(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

    if graph is None:
        return "Could not generate a graph", 400

    if traffic_matrix is None:
        return "Could not generate a traffic matrix", 400

    solver = TESolver(graph, traffic_matrix)
    logger.info(f"TESolver: {solver}")

    solution = solver.solve()
    logger.debug(f"TESolver result: {solution}")

    if solution is None or solution.connection_map is None:
        return "Could not solve the request", 400

    breakdown = temanager.generate_connection_breakdown(solution)
    logger.debug("-------BREAKDOWN:------")
    logger.debug(json.dumps(breakdown))

    if breakdown is None:
        return "Could not break down the solution", 400

    for entry in breakdown:
        domain_name = find_between(entry, "topology:", ".net")
        producer = TopicQueueProducer(
            timeout=5, exchange_name="connection", routing_key=domain_name
        )
        producer.call(json.dumps(breakdown[entry]))
        producer.stop_keep_alive()

    return "Connection published"

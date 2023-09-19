import json
import logging

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.topology.temanager import TEManager

from swagger_server.messaging.topic_queue_producer import TopicQueueProducer
from swagger_server.models.simple_link import SimpleLink
from swagger_server.utils.parse_helper import ParseHelper

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)


class ConnectionHandler:
    def __init__(self, db_instance):
        self.db_instance = db_instance
        self.parse_helper = ParseHelper()

    def remove_connection(self, connection):
        # call pce to remove connection
        pass

    def _send_breakdown_to_lc(self, temanager, connection, solution):
        breakdown = temanager.generate_connection_breakdown(solution)
        logger.debug(f"-- BREAKDOWN: {json.dumps(breakdown)}")

        if breakdown is None:
            return "Could not break down the solution", 400

        link_connections_dict_json = (
            self.db_instance.read_from_db("link_connections_dict")[
                "link_connections_dict"
            ]
            if self.db_instance.read_from_db("link_connections_dict")
            else None
        )

        if link_connections_dict_json:
            link_connections_dict = json.loads(link_connections_dict_json)
        else:
            link_connections_dict = {}

        for domain, link in breakdown.items():
            port_list = []
            for key in link.keys():
                if "uni_" in key and "port_id" in link[key]:
                    port_list.append(link[key]["port_id"])

            if port_list:
                simple_link = SimpleLink(port_list).to_string()

                if simple_link not in link_connections_dict:
                    link_connections_dict[simple_link] = []

                if connection not in link_connections_dict[simple_link]:
                    link_connections_dict[simple_link].append(connection)

                self.db_instance.add_key_value_pair_to_db(
                    "link_connections_dict", json.dumps(link_connections_dict)
                )

            logger.debug(f"Attempting to publish domain: {domain}, link: {link}")

            # From "urn:ogf:network:sdx:topology:amlight.net", attempt to
            # extract a string like "amlight".
            domain_name = (
                self.parse_helper.find_between(domain, "topology:", ".net")
                or f"{domain}"
            )
            exchange_name = "connection"

            logger.debug(
                f"Publishing '{link}' with exchange_name: {exchange_name}, "
                f"routing_key: {domain_name}"
            )

            producer = TopicQueueProducer(
                timeout=5, exchange_name=exchange_name, routing_key=domain_name
            )
            producer.call(json.dumps(link))
            producer.stop_keep_alive()

    def place_connection(self, connection):
        # call pce to generate breakdown, and place connection
        num_domain_topos = 0

        if self.db_instance.read_from_db("num_domain_topos"):
            num_domain_topos = self.db_instance.read_from_db("num_domain_topos")[
                "num_domain_topos"
            ]

        # Initializing TEManager with `None` topology data is a
        # work-around for
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/145
        temanager = TEManager(topology_data=None, connection_data=connection)
        lc_domain_topo_dict = {}

        # Read LC-1, LC-2, LC-3, and LC-4 topologies because of
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/152
        for i in range(1, int(num_domain_topos) + 2):
            lc = f"LC-{i}"
            logger.debug(f"Reading {lc} from DB")
            curr_topo = self.db_instance.read_from_db(lc)
            if curr_topo is None:
                logger.debug(f"Read {lc} from DB: {curr_topo}")
                continue
            else:
                # Get the actual thing minus the Mongo ObjectID.
                curr_topo_str = curr_topo.get(lc)
                # Just log a substring, not the whole thing.
                logger.debug(f"Read {lc} from DB: {curr_topo_str[0:50]}...")

            curr_topo_json = json.loads(curr_topo_str)
            lc_domain_topo_dict[curr_topo_json["domain_name"]] = curr_topo_json[
                "lc_queue_name"
            ]
            logger.debug(
                f"Adding #{i} topology {curr_topo_json.get('id')} to TEManager"
            )
            temanager.add_topology(curr_topo_json)

        for num, val in enumerate(temanager.topology_manager.topology_list):
            logger.info(f"TE topology #{num}: {val}")

        graph = temanager.generate_graph_te()
        if graph is None:
            return "Could not generate a graph", 400

        traffic_matrix = temanager.generate_connection_te()
        if traffic_matrix is None:
            return "Could not generate a traffic matrix", 400

        logger.info(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        solver = TESolver(graph, traffic_matrix)
        solution = solver.solve()
        logger.debug(f"TESolver result: {solution}")

        if solution is None or solution.connection_map is None:
            return "Could not solve the request", 400

        self._send_breakdown_to_lc(temanager, connection, solution)

    def handle_link_failure(self, msg_json):
        logger.debug("---Handling connections that contain failed link.---")
        link_connections_dict_str = self.db_instance.read_from_db(
            "link_connections_dict"
        )

        if (
            not link_connections_dict_str
            or not link_connections_dict_str["link_connections_dict"]
        ):
            logger.debug("No connection has been placed yet.")
            return

        link_connections_dict = json.loads(
            link_connections_dict_str["link_connections_dict"]
        )

        for link in msg_json["link_failure"]:
            port_list = []
            if "ports" not in link:
                continue
            for port in link["ports"]:
                if "id" not in port:
                    continue
                port_list.append(port["id"])

            simple_link = SimpleLink(port_list).to_string()

            if simple_link in link_connections_dict:
                logger.debug("Found failed link record!")
                connections = link_connections_dict[simple_link]
                for index, connection in enumerate(connections):
                    self.remove_connection(connection)
                    del link_connections_dict[simple_link][index]
                    logger.debug("Removed connection:")
                    logger.debug(connection)
                    self.place_connection(connection)
                    link_connections_dict[simple_link].append(connection)

        self.db_instance.add_key_value_pair_to_db(
            "link_connections_dict", json.dumps(link_connections_dict)
        )

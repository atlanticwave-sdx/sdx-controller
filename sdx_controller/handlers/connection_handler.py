import json
import logging
import traceback
from typing import Tuple

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.topology.temanager import TEManager

from sdx_controller.messaging.topic_queue_producer import TopicQueueProducer
from sdx_controller.models.simple_link import SimpleLink
from sdx_controller.utils.parse_helper import ParseHelper

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)


class ConnectionHandler:
    def __init__(self, db_instance):
        self.db_instance = db_instance
        self.parse_helper = ParseHelper()

    def _send_breakdown_to_lc(self, breakdown, operation, connection_request):
        logger.debug(f"-- BREAKDOWN: {json.dumps(breakdown)}")

        if breakdown is None:
            return "Could not break down the solution", 400

        link_connections_dict_json = (
            self.db_instance.read_from_db("links", "link_connections_dict")[
                "link_connections_dict"
            ]
            if self.db_instance.read_from_db("links", "link_connections_dict")
            else None
        )

        if link_connections_dict_json:
            link_connections_dict = json.loads(link_connections_dict_json)
        else:
            link_connections_dict = {}

        interdomain_a, interdomain_b = None, None
        for domain, link in breakdown.items():
            port_list = []
            for key in link.keys():
                if "uni_" in key and "port_id" in link[key]:
                    port_list.append(link[key]["port_id"])

            if port_list:
                simple_link = SimpleLink(port_list).to_string()

                if simple_link not in link_connections_dict:
                    link_connections_dict[simple_link] = []

                if (
                    operation == "post"
                    and connection_request not in link_connections_dict[simple_link]
                ):
                    link_connections_dict[simple_link].append(connection_request)

                if (
                    operation == "delete"
                    and connection_request in link_connections_dict[simple_link]
                ):
                    link_connections_dict[simple_link].remove(connection_request)

                self.db_instance.add_key_value_pair_to_db(
                    "links", "link_connections_dict", json.dumps(link_connections_dict)
                )

            if interdomain_a:
                interdomain_b = link.get("uni_a", {}).get("port_id")
            else:
                interdomain_a = link.get("uni_z", {}).get("port_id")

            if interdomain_a and interdomain_b:
                simple_link = SimpleLink([interdomain_a, interdomain_b]).to_string()

                if simple_link not in link_connections_dict:
                    link_connections_dict[simple_link] = []

                if (
                    operation == "post"
                    and connection_request not in link_connections_dict[simple_link]
                ):
                    link_connections_dict[simple_link].append(connection_request)

                if (
                    operation == "delete"
                    and connection_request in link_connections_dict[simple_link]
                ):
                    link_connections_dict[simple_link].remove(connection_request)

                self.db_instance.add_key_value_pair_to_db(
                    "links", "link_connections_dict", json.dumps(link_connections_dict)
                )

                interdomain_a = link.get("uni_z", {}).get("port_id")

            logger.debug(f"Attempting to publish domain: {domain}, link: {link}")

            # From "urn:ogf:network:sdx:topology:amlight.net", attempt to
            # extract a string like "amlight".
            domain_name = self.parse_helper.find_domain_name(domain, ":") or f"{domain}"
            exchange_name = "connection"

            logger.debug(
                f"Doing '{operation}' operation for '{link}' with exchange_name: {exchange_name}, "
                f"routing_key: {domain_name}"
            )
            mq_link = {"operation": operation, "link": link}
            producer = TopicQueueProducer(
                timeout=5, exchange_name=exchange_name, routing_key=domain_name
            )
            producer.call(json.dumps(mq_link))
            producer.stop_keep_alive()

        # We will get to this point only if all the previous steps
        # leading up to this point were successful.
        return "Connection published", 200

    def place_connection(
        self, te_manager: TEManager, connection_request: dict
    ) -> Tuple[str, int]:
        """
        Do the actual work of creating a connection.

        This method will call pce library to generate a breakdown
        across relevant domains, and then send individual connection
        requests to each of those domains.

        Note that we can return early if things fail.  Return value is
        a tuple of the form (reason, HTTP code).
        """
        for num, val in enumerate(te_manager.get_topology_map().values()):
            logger.debug(f"TE topology #{num}: {val}")

        graph = te_manager.generate_graph_te()
        if graph is None:
            return "No SDX topology found", 424

        traffic_matrix = te_manager.generate_traffic_matrix(
            connection_request=connection_request
        )
        if traffic_matrix is None:
            return "Could not generate a traffic matrix", 400

        logger.info(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        solver = TESolver(graph, traffic_matrix)
        solution = solver.solve()
        logger.debug(f"TESolver result: {solution}")

        if solution is None or solution.connection_map is None:
            return "Could not solve the request", 400

        try:
            breakdown = te_manager.generate_connection_breakdown(
                solution, connection_request
            )
            self.db_instance.add_key_value_pair_to_db(
                "breakdowns", connection_request["id"], breakdown
            )
            status, code = self._send_breakdown_to_lc(
                breakdown, "post", connection_request
            )
            logger.debug(f"Breakdown sent to LC, status: {status}, code: {code}")
            return status, code
        except Exception as e:
            err = traceback.format_exc().replace("\n", ", ")
            logger.error(f"Error when generating/publishing breakdown: {e} - {err}")
            return f"Error: {e}", 400

    def remove_connection(self, te_manager, service_id) -> Tuple[str, int]:
        te_manager.unreserve_vlan(service_id)
        connection_request = self.db_instance.read_from_db("connections", service_id)
        if not connection_request:
            return "Did not find connection request, cannot remove connection", 404

        connection_request = connection_request[service_id]

        breakdown = self.db_instance.read_from_db("breakdowns", service_id)
        if not breakdown:
            return "Did not find breakdown, cannot remove connection", 404
        breakdown = breakdown[service_id]

        try:
            status, code = self._send_breakdown_to_lc(
                breakdown, "delete", json.loads(connection_request)
            )
            logger.debug(f"Breakdown sent to LC, status: {status}, code: {code}")
            return status, code
        except Exception as e:
            logger.debug(f"Error when removing breakdown: {e}")
            return f"Error: {e}", 400

    def handle_link_failure(self, te_manager, failed_links):
        logger.debug("---Handling connections that contain failed link.---")
        link_connections_dict_str = self.db_instance.read_from_db(
            "links", "link_connections_dict"
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

        for link in failed_links:
            logger.info(f"Handling link failure on {link['id']} ({link['ports']})")
            port_list = []
            if "ports" not in link:
                continue
            for port in link["ports"]:
                port_id = port if isinstance(port, str) else port.get("id")
                if not port_id:
                    continue
                port_list.append(port_id)

            simple_link = SimpleLink(port_list).to_string()

            if simple_link in link_connections_dict:
                logger.debug("Found failed link record!")
                connections = link_connections_dict[simple_link]
                for index, connection in enumerate(connections):
                    logger.info(
                        f"Connection {connection['id']} affected by link {link['id']}"
                    )
                    if "id" not in connection:
                        continue
                    self.remove_connection(te_manager, connection["id"])
                    del link_connections_dict[simple_link][index]
                    logger.debug("Removed connection:")
                    logger.debug(connection)
                    self.place_connection(te_manager, connection)

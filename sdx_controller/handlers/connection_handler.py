import json
import logging
import time
import traceback
from typing import Tuple

from sdx_datamodel.connection_sm import ConnectionStateMachine
from sdx_datamodel.constants import Constants, MessageQueueNames, MongoCollections
from sdx_datamodel.parsing.exceptions import (
    AttributeNotSupportedException,
    ServiceNotSupportedException,
)
from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.topology.temanager import TEManager
from sdx_pce.utils.exceptions import (
    RequestValidationError,
    SameSwitchRequestError,
    TEError,
)

from sdx_controller.messaging.topic_queue_producer import TopicQueueProducer
from sdx_controller.models.simple_link import SimpleLink
from sdx_controller.utils.parse_helper import ParseHelper

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)

MongoCollections.SOLUTIONS = "solutions"


class ConnectionHandler:
    def __init__(self, db_instance):
        self.db_instance = db_instance
        self.parse_helper = ParseHelper()

    def _process_port(self, temanager, connection_service_id, port_id, operation):
        port_connections_dict_json = self.db_instance.get_value_from_db(
            MongoCollections.PORTS, Constants.PORT_CONNECTIONS_DICT
        )
        port_connections_dict = (
            json.loads(port_connections_dict_json) if port_connections_dict_json else {}
        )

        if port_id not in port_connections_dict:
            port_connections_dict[port_id] = []

        temanager._logger.info(
            f"DB ports in {operation}: {port_id} {connection_service_id} {port_connections_dict}"
        )
        if (
            operation == "post"
            and connection_service_id
            and connection_service_id not in port_connections_dict[port_id]
        ):
            port_connections_dict[port_id].append(connection_service_id)
            temanager._logger.info(f"Save to DB ports: {port_connections_dict}")

        if (
            operation == "delete"
            and connection_service_id
            and connection_service_id in port_connections_dict[port_id]
        ):
            port_connections_dict[port_id].remove(connection_service_id)

        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.PORTS,
            Constants.PORT_CONNECTIONS_DICT,
            json.dumps(port_connections_dict),
        )

    def _process_link_connection_dict(
        self,
        temanager,
        link_connections_dict,
        simple_link,
        connection_service_id,
        operation,
    ):
        if simple_link not in link_connections_dict:
            link_connections_dict[simple_link] = []

        temanager._logger.info(
            f"DB links in {operation}: {simple_link} {connection_service_id} {link_connections_dict}"
        )
        if (
            operation == "post"
            and connection_service_id
            and connection_service_id not in link_connections_dict[simple_link]
        ):
            link_connections_dict[simple_link].append(connection_service_id)
            temanager._logger.info(f"Save to DB links: {link_connections_dict}")

        if (
            operation == "delete"
            and connection_service_id
            and connection_service_id in link_connections_dict[simple_link]
        ):
            link_connections_dict[simple_link].remove(connection_service_id)

        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.LINKS,
            Constants.LINK_CONNECTIONS_DICT,
            json.dumps(link_connections_dict),
        )

    def _process_path_to_db(self, temanager, operation, connection_request):
        link_connections_dict_json = self.db_instance.get_value_from_db(
            MongoCollections.LINKS, Constants.LINK_CONNECTIONS_DICT
        )
        link_connections_dict = (
            json.loads(link_connections_dict_json) if link_connections_dict_json else {}
        )
        connection_service_id = connection_request.get("id")
        links = self.db_instance.get_value_from_db(
            MongoCollections.SOLUTIONS, connection_service_id
        )

        # only save the uni ports
        request_endpoints = connection_request.get("endpoints")  # spec version 2.0.0
        if request_endpoints and len(request_endpoints) > 1:
            request_uni_a = request_endpoints[0]
            request_uni_z = request_endpoints[1]
            request_uni_a_id = request_uni_a.get("port_id")
            if request_uni_a_id is None:
                request_uni_a_id = request_uni_a.get("id")
            request_uni_z_id = request_uni_z.get("port_id")
            if request_uni_z_id is None:
                request_uni_z_id = request_uni_z.get("id")
            self._process_port(
                temanager, connection_service_id, request_uni_a_id, operation
            )
            self._process_port(
                temanager, connection_service_id, request_uni_z_id, operation
            )
        else:
            temanager._logger.warning(f"No endpoints: {connection_request}")

        for ports in links:
            s_port = ports["source"]
            d_port = ports["destination"]
            link = temanager.topology_manager._topology.get_link_by_port_id(
                s_port, d_port
            )
            temanager._logger.info(f"Links on path: {link.id} {s_port} {d_port}")
            simple_link = SimpleLink([s_port, d_port]).to_string()
            self._process_link_connection_dict(
                temanager,
                link_connections_dict,
                simple_link,
                connection_service_id,
                operation,
            )

    def _send_breakdown_to_lc(self, breakdown, operation, connection_request):
        logger.debug(f"BREAKDOWN: {json.dumps(breakdown)}")

        if breakdown is None:
            return "Could not break down the solution", 400

        connection_service_id = connection_request.get("id")

        for domain, link in breakdown.items():
            logger.debug(f"Attempting to publish domain: {domain}, link: {link}")

            # From "urn:ogf:network:sdx:topology:amlight.net", attempt to
            # extract a string like "amlight".
            domain_name = self.parse_helper.find_domain_name(domain, ":") or f"{domain}"
            exchange_name = MessageQueueNames.CONNECTIONS

            logger.debug(
                f"Doing '{operation}' operation for '{link}' with exchange_name: {exchange_name}, "
                f"routing_key: {domain_name}"
            )
            mq_link = {
                "operation": operation,
                "service_id": connection_service_id,
                "link": link,
            }
            producer = TopicQueueProducer(
                timeout=5, exchange_name=exchange_name, routing_key=domain_name
            )
            producer.call(json.dumps(mq_link))
            producer.stop_keep_alive()

        # We will get to this point only if all the previous steps
        # leading up to this point were successful.
        return "Connection published", 201

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
        # for num, val in enumerate(te_manager.get_topology_map().values()):
        #     logger.debug(f"TE topology #{num}: {val}")

        graph = te_manager.generate_graph_te()
        if graph is None:
            return "No SDX topology found", 424
        try:
            traffic_matrix = te_manager.generate_traffic_matrix(
                connection_request=connection_request
            )
        except RequestValidationError as request_err:
            err = traceback.format_exc().replace("\n", ", ")
            logger.error(
                f"Error when parsing and validating request: {request_err} - {err}"
            )
            return f"Error: {request_err}", request_err.request_code
        except ServiceNotSupportedException as service_err:
            err = traceback.format_exc().replace("\n", ", ")
            logger.error(
                f"Error when parsing and validating request: {service_err} - {err}"
            )
            return f"Error: {service_err}", 402
        except AttributeNotSupportedException as attr_err:
            err = traceback.format_exc().replace("\n", ", ")
            logger.error(
                f"Error when parsing and validating request: {attr_err} - {err}"
            )
            return f"Error: {attr_err}", 422
        except SameSwitchRequestError as ctx:
            logger.debug(
                f"{str(ctx)},{ctx.request_id},{ctx.domain_id},{ctx.ingress_port},{ctx.egress_port}, {ctx.ingress_user_port_tag}, {ctx.egress_user_port_tag}"
            )
            try:
                breakdown = te_manager.generate_connection_breakdown_same_switch(
                    ctx.request_id,
                    ctx.domain_id,
                    ctx.ingress_port,
                    ctx.egress_port,
                    ctx.ingress_user_port_tag,
                    ctx.egress_user_port_tag,
                )
                self.db_instance.add_key_value_pair_to_db(
                    MongoCollections.BREAKDOWNS, connection_request["id"], breakdown
                )
                self._process_port(
                    te_manager, connection_request["id"], ctx.ingress_port, "post"
                )
                status, code = self._send_breakdown_to_lc(
                    breakdown, "post", connection_request
                )
                logger.debug(f"Breakdown sent to LC, status: {status}, code: {code}")
                # update topology in DB with updated states (bandwidth and available vlan pool)
                topology_db_update(self.db_instance, te_manager)
                return status, code
            except TEError as te_err:
                # We could probably return te_err.te_code instead of 400,
                # but I don't think PCE should use HTTP error codes,
                # because that violates abstraction boundaries.
                return f"PCE error: {te_err}", te_err.te_code
            except Exception as e:
                err = traceback.format_exc().replace("\n", ", ")
                logger.error(f"Error when generating/publishing breakdown: {e} - {err}")
                return f"Error: {e}", 410

        # General case: traffic_matrix is not None
        if traffic_matrix is None:
            return (
                "Request does not have a valid JSON or body is incomplete/incorrect",
                400,
            )

        logger.info(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")
        try:
            conn = te_manager.requests_connectivity(traffic_matrix)
            if conn is False:
                logger.error(f"Graph connectivity: {conn}")
                raise TEError("No path is available, the graph is not connected", 412)
        except TEError as te_err:
            return f"PCE error: {te_err}", te_err.te_code

        solver = TESolver(graph, traffic_matrix)
        solution = solver.solve()
        logger.debug(f"TESolver result: {solution}")

        if solution is None or solution.connection_map is None:
            return "Could not solve the request", 410

        _, links = te_manager.get_links_on_path(solution)

        try:
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.SOLUTIONS, connection_request["id"], links
            )
            breakdown = te_manager.generate_connection_breakdown(
                solution, connection_request
            )
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.BREAKDOWNS, connection_request["id"], breakdown
            )
            self._process_path_to_db(
                te_manager,
                operation="post",
                connection_request=connection_request,
            )
            status, code = self._send_breakdown_to_lc(
                breakdown, "post", connection_request
            )
            logger.debug(f"Breakdown sent to LC, status: {status}, code: {code}")
            # update topology in DB with updated states (bandwidth and available vlan pool)
            topology_db_update(self.db_instance, te_manager)
            return status, code
        except TEError as te_err:
            # We could probably return te_err.te_code instead of 400,
            # but I don't think PCE should use HTTP error codes,
            # because that violates abstraction boundaries.
            return f"PCE error: {te_err}", te_err.te_code
        except Exception as e:
            err = traceback.format_exc().replace("\n", ", ")
            logger.error(f"Error when generating/publishing breakdown: {e} - {err}")
            return f"Error: {e}", 410

    def archive_connection(self, service_id) -> None:
        connection_request = self.db_instance.get_value_from_db(
            MongoCollections.CONNECTIONS, service_id
        )
        if not connection_request:
            return

        connection_request = connection_request
        self.db_instance.delete_one_entry(MongoCollections.CONNECTIONS, service_id)

        historical_connections_list = self.db_instance.get_value_from_db(
            MongoCollections.HISTORICAL_CONNECTIONS, service_id
        )
        # Current timestamp in seconds
        timestamp = int(time.time())

        if historical_connections_list:
            historical_connections_list.append({timestamp: connection_request})
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.HISTORICAL_CONNECTIONS,
                service_id,
                historical_connections_list,
            )
        else:
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.HISTORICAL_CONNECTIONS,
                service_id,
                [{timestamp: connection_request}],
            )
        logger.debug(f"Archived connection: {service_id}")

    def remove_connection(self, te_manager, service_id) -> Tuple[str, int]:
        connection_request = self.db_instance.get_value_from_db(
            MongoCollections.CONNECTIONS, service_id
        )
        if not connection_request:
            return "Did not find connection request, cannot remove connection", 404

        if connection_request.get("status") != str(ConnectionStateMachine.State.UP):
            logger.info(
                f"Connection {service_id} connection_request.get('status') is not {str(ConnectionStateMachine.State.UP)}, cannot remove connection."
            )
            return "Connection is not UP, Archive", 404

        try:
            te_manager.delete_connection(service_id)
            breakdown = self.db_instance.get_value_from_db(
                MongoCollections.BREAKDOWNS, service_id
            )
            if not breakdown:
                return "Did not find breakdown, cannot remove connection", 404

            status, code = self._send_breakdown_to_lc(
                breakdown, "delete", connection_request
            )
            self._process_path_to_db(
                te_manager, operation="delete", connection_request=connection_request
            )
            self.db_instance.delete_one_entry(MongoCollections.BREAKDOWNS, service_id)
            self.archive_connection(service_id)
            logger.debug(f"Breakdown sent to LC, status: {status}, code: {code}")
            # update topology in DB with updated states (bandwidth and available vlan pool)
            topology_db_update(self.db_instance, te_manager)
            return status, code
        except Exception as e:
            logger.debug(f"Error when removing breakdown: {e}")
            return f"Error when removing breakdown: {e}", 400

    def handle_link_removal(self, te_manager, removed_links):
        logger.debug("Handling connections that contain removed links.")
        failed_links = []
        for link in removed_links:
            failed_links.append({"id": link.id, "ports": link.ports})

        self.handle_link_failure(te_manager, failed_links)

    def handle_link_failure(self, te_manager, failed_links):
        logger.debug("Handling connections that contain failed links.")
        link_connections_dict = self.db_instance.get_value_from_db(
            MongoCollections.LINKS, Constants.LINK_CONNECTIONS_DICT
        )

        if not link_connections_dict:
            logger.debug("No connection has been placed yet.")
            return

        link_connections_dict = json.loads(link_connections_dict)

        for link in failed_links:
            logger.info(f"Handling link failure on {link['id']}")
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
                service_ids = link_connections_dict[simple_link]
                for index, service_id in enumerate(service_ids):
                    logger.info(
                        f"Connection {service_id} affected by link {link['id']}"
                    )
                    connection = self.db_instance.get_value_from_db(
                        MongoCollections.CONNECTIONS, service_id
                    )
                    if not connection:
                        logger.debug(f"Did not find connection from db: {service_id}")
                        continue

                    try:
                        logger.debug(f"Link Failure: Removing connection: {connection}")
                        if connection.get("status") is None:
                            connection["status"] = str(
                                ConnectionStateMachine.State.ERROR
                            )
                        else:
                            connection, _ = connection_state_machine(
                                connection, ConnectionStateMachine.State.ERROR
                            )
                        logger.info(
                            f"Removing connection: {service_id} {connection.get('status')}"
                        )
                        _, code = self.remove_connection(te_manager, connection["id"])
                        if code // 100 != 2:
                            logger.info(
                                f"Do not remove connection, may be already removed: {connection['id']}, code: {code}"
                            )
                        continue
                    except Exception as err:
                        logger.info(
                            f"Encountered error when deleting connection: {err}"
                        )
                        continue

                    logger.debug("Removed connection:")
                    logger.debug(connection)
                    connection, _ = connection_state_machine(
                        connection, ConnectionStateMachine.State.RECOVERING
                    )
                    connection["oxp_success_count"] = 0
                    self.db_instance.add_key_value_pair_to_db(
                        MongoCollections.CONNECTIONS, service_id, connection
                    )
                    _reason, code = self.place_connection(te_manager, connection)
                    if code // 100 != 2:
                        connection, _ = connection_state_machine(
                            connection, ConnectionStateMachine.State.ERROR
                        )
                        self.db_instance.add_key_value_pair_to_db(
                            MongoCollections.CONNECTIONS,
                            service_id,
                            connection,
                        )

                    logger.info(
                        f"place_connection result: ID: {service_id} reason='{_reason}', code={code}"
                    )

    def handle_uni_ports_up_to_down(self, uni_ports_up_to_down):
        """
        Handles the transition of UNI ports from 'up' to 'down' status.
        This function checks all the connections in the database and updates the status
        of connections whose endpoints are in the provided list `uni_ports_up_to_down`.
        The status of these connections will be changed to 'down'.
        Args:
            uni_ports_up_to_down (list): A list of UNI port identifiers whose status
                                         needs to be updated to 'down'.
        Returns:
            None
        """
        port_connections_dict_json = self.db_instance.get_value_from_db(
            MongoCollections.PORTS, Constants.PORT_CONNECTIONS_DICT
        )
        port_connections_dict = (
            json.loads(port_connections_dict_json) if port_connections_dict_json else {}
        )

        for port in uni_ports_up_to_down:
            if port.id in port_connections_dict:
                logger.debug(f"Found the down port record for port {port.id}!")
                service_ids = port_connections_dict[port.id]
                for service_id in service_ids:
                    connection = self.db_instance.get_value_from_db(
                        MongoCollections.CONNECTIONS, service_id
                    )
                    if not connection:
                        logger.debug(f"Cannot find connection {service_id} in DB.")
                        continue
                    logger.info(f"Updating connection {service_id} status to 'down'.")
                    connection["status"] = "DOWN"
                    self.db_instance.add_key_value_pair_to_db(
                        MongoCollections.CONNECTIONS, service_id, connection
                    )
                    logger.debug(f"Connection status updated for {service_id}")
            else:
                logger.warning(
                    f"port not found in db {port.id} in {port_connections_dict}"
                )

    def handle_uni_ports_down_to_up(self, uni_ports_down_to_up):
        """
        Handles the transition of UNI ports from 'down' to 'up' status.
        This function checks all the connections in the database and updates the status
        of connections whose endpoints are in the provided list `uni_ports_down_to_up`.
        The status of these connections will be changed to 'up'.
        Args:
            uni_ports_down_to_up (list): A list of UNI port identifiers whose status
                                         needs to be updated to 'up'.
        Returns:
            None
        """
        port_connections_dict_json = self.db_instance.get_value_from_db(
            MongoCollections.PORTS, Constants.PORT_CONNECTIONS_DICT
        )
        port_connections_dict = (
            json.loads(port_connections_dict_json) if port_connections_dict_json else {}
        )
        for port in uni_ports_down_to_up:
            if port.id in port_connections_dict:
                logger.debug("Found the down port record!")
                service_ids = port_connections_dict[port.id]
                for service_id in service_ids:
                    connection = self.db_instance.get_value_from_db(
                        MongoCollections.CONNECTIONS, service_id
                    )
                    if not connection:
                        logger.debug(f"Cannot find connection {service_id} in DB.")
                        continue

                    logger.info(f"Updating connection {service_id} status to 'up'.")
                    connection["status"] = "UP"
                    self.db_instance.add_key_value_pair_to_db(
                        MongoCollections.CONNECTIONS, service_id, connection
                    )
                    logger.debug(f"Connection status updated for {service_id}")

    def get_archived_connections(self, service_id: str):
        historical_connections = self.db_instance.get_value_from_db(
            MongoCollections.HISTORICAL_CONNECTIONS, service_id
        )
        if not historical_connections:
            return None
        return historical_connections


def topology_db_update(db_instance, te_manager):
    # update OXP topology in DB:
    oxp_topology_map = te_manager.topology_manager.get_topology_map()
    for domain_name, topology in oxp_topology_map.items():
        msg_json = topology.to_dict()
        db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, domain_name, msg_json
        )
    # use 'latest_topo' as PK to save latest full topo to db
    latest_topo = te_manager.topology_manager.get_topology().to_dict()
    db_instance.add_key_value_pair_to_db(
        MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY, latest_topo
    )
    logger.info("Save to database complete.")


def get_connection_status(db, service_id: str):
    """
    Form a response to `GET /l2vpn/1.0/{service_id}`.
    """
    assert db is not None
    assert service_id is not None

    breakdown = db.read_from_db(MongoCollections.BREAKDOWNS, service_id)
    if not breakdown:
        logger.info(f"Could not find breakdown for {service_id}")
        return {}

    logger.info(f"breakdown for {service_id}: {breakdown}")

    # The breakdown we read from DB is in this shape:
    #
    # {
    #     "_id": ObjectId("66ec71770c7022eb0922f41a"),
    #     "5b7df397-2269-489b-8e03-f256461265a0": {
    #         "urn:sdx:topology:amlight.net": {
    #             "name": "AMLIGHT_vlan_1000_10001",
    #             "dynamic_backup_path": True,
    #             "uni_a": {
    #                 "tag": {"value": 1000, "tag_type": 1},
    #                 "port_id": "urn:sdx:port:amlight.net:A1:1",
    #             },
    #             "uni_z": {
    #                 "tag": {"value": 10001, "tag_type": 1},
    #                 "port_id": "urn:sdx:port:amlight.net:B1:3",
    #             },
    #         }
    #     },
    # }
    #
    # We need to shape that into this form, at a minimum:
    #
    # {
    #     "c73da8e1-5d03-4620-a1db-7cdf23e8978c": {
    #         "service_id": "c73da8e1-5d03-4620-a1db-7cdf23e8978c",
    #         "name": "new-connection",
    #         "endpoints": [
    #          {
    #             "port_id": "urn:sdx:port:amlight.net:A1:1",
    #             "vlan": "150"
    #          },
    #          {
    #             "port_id": "urn:sdx:port:amlight:B1:1",
    #             "vlan": "300"}
    #         ],
    #     }
    # }
    #
    # See https://sdx-docs.readthedocs.io/en/latest/specs/provisioning-api-1.0.html#request-format-2
    #

    domains = breakdown.get(service_id)
    logger.info(f"domains for {service_id}: {domains.keys()}")

    # Find the name and description from the original connection
    # request for this service_id.
    name = "unknown"
    description = "unknown"
    status = "unknown"
    qos_metrics = {}
    scheduling = {}
    notifications = {}

    endpoints = list()
    request_endpoints = []
    response_endpoints = []
    request_uni_a_id = None
    request_uni_z_id = None

    request = db.read_from_db(MongoCollections.CONNECTIONS, service_id)
    if not request:
        logger.error(f"Can't find a connection request for {service_id}")
        # TODO: we're in a strange state here. Should we panic?
    else:
        logger.info(f"Found request for {service_id}: {request}")
        # We seem to have saved the original request in the form of a
        # string into the DB, not a record.
        request_dict = request.get(service_id)
        name = request_dict.get("name")
        description = request_dict.get("description")
        status = request_dict.get("status")
        qos_metrics = request_dict.get("qos_metrics")
        scheduling = request_dict.get("scheduling")
        notifications = request_dict.get("notifications")
        oxp_response = request_dict.get("oxp_response")
        status = parse_conn_status(status)
        request_endpoints = request_dict.get("endpoints")  # spec version 2.0.0
        if request_endpoints and len(request_endpoints) > 1:
            request_uni_a = request_endpoints[0]
            request_uni_z = request_endpoints[1]
            request_uni_a_id = request_uni_a.get("port_id")
            if request_uni_a_id is None:
                request_uni_a_id = request_uni_a.get("id")
            request_uni_z_id = request_uni_z.get("port_id")
            if request_uni_z_id is None:
                request_uni_z_id = request_uni_z.get("id")
        else:  # spec version 1.0.0
            request_uni_a = request_dict.get("ingress_port")
            request_uni_a_id = request_uni_a.get("id")
            request_uni_z = request_dict.get("egress_port")
            request_uni_z_id = request_uni_z.get("id")

    response = {}

    for domain, breakdown in domains.items():
        uni_a_port = breakdown.get("uni_a").get("port_id")
        uni_a_vlan = breakdown.get("uni_a").get("tag").get("value")

        endpoint_a = {
            "port_id": uni_a_port,
            "vlan": str(uni_a_vlan),
        }

        endpoints.append(endpoint_a)

        if request_uni_a_id == uni_a_port:
            (
                response_endpoints.append(endpoint_a)
                if endpoint_a not in response_endpoints
                else None
            )
        if request_uni_z_id == uni_a_port:
            (
                response_endpoints.append(endpoint_a)
                if endpoint_a not in response_endpoints
                else None
            )

        uni_z_port = breakdown.get("uni_z").get("port_id")
        uni_z_vlan = breakdown.get("uni_z").get("tag").get("value")

        endpoint_z = {
            "port_id": uni_z_port,
            "vlan": str(uni_z_vlan),
        }

        endpoints.append(endpoint_z)

        if request_uni_a_id == uni_z_port:
            (
                response_endpoints.append(endpoint_z)
                if endpoint_z not in response_endpoints
                else None
            )
        if request_uni_z_id == uni_z_port:
            (
                response_endpoints.append(endpoint_z)
                if endpoint_z not in response_endpoints
                else None
            )
        print(
            f"endpoints info: {request_uni_a_id}, {request_uni_z_id}, {uni_a_port}, {uni_z_port}"
        )

    # TODO: we're missing many of the attributes in the response here
    # which have been specified in the provisioning spec, such as:
    # name, description, qos_metrics, notifications, ownership,
    # creation_date, archived_date, status, state, counters_location,
    # last_modified, current_path, oxp_service_ids.  Implementing each
    # of them would be worth a separate ticket each, so we'll just
    # make do with this minimal response for now.
    response[service_id] = {
        "service_id": service_id,
        "name": name,
        "description": description,
        "status": status,
        "endpoints": response_endpoints,
        "current_path": endpoints,
        "archived_date": 0,
    }
    if qos_metrics:
        response[service_id]["qos_metrics"] = qos_metrics

    if scheduling:
        response[service_id]["scheduling"] = scheduling

    if notifications:
        response[service_id]["notifications"] = notifications

    if oxp_response:
        response[service_id]["oxp_response"] = oxp_response

    logger.info(f"Formed a response: {response}")

    return response


def connection_state_machine(connection, new_state):
    conn_sm = ConnectionStateMachine()
    status = connection.get("status")
    value = conn_sm.State[status]
    conn_sm.set_state(value)
    conn_sm.transition(new_state)
    connection["status"] = str(conn_sm.get_state())
    return connection, conn_sm


def parse_conn_status(conn_state):
    """Parse connection from state to status as specified on the
    Provisioning Data Model Spec 1.0a. As per the spec:
    - up: if the L2VPN is operational
    - down: if the L2VPN is not operational due to topology issues/lack of path, or endpoints being down,
    - error: when there is an error with the L2VPN,
    - under provisioning: when the L2VPN is still being provisioned by the OXPs
    - maintenance: when the L2VPN is being affected by a network maintenance
    """
    state2status = {
        "UP": "up",
        "UNDER_PROVISIONING": "under provisioning",
        "RECOVERING": "down",
        "DOWN": "down",
        "ERROR": "down",
        "MODIFYING": "under provisioning",
    }
    return state2status.get(conn_state, "error")

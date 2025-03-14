import json
import logging
import time
import traceback
from typing import Tuple

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


class ConnectionHandler:
    def __init__(self, db_instance):
        self.db_instance = db_instance
        self.parse_helper = ParseHelper()

    def _send_breakdown_to_lc(self, breakdown, operation, connection_request):
        logger.debug(f"-- BREAKDOWN: {json.dumps(breakdown)}")

        if breakdown is None:
            return "Could not break down the solution", 400

        link_connections_dict_json = (
            self.db_instance.read_from_db(
                MongoCollections.LINKS, Constants.LINK_CONNECTIONS_DICT
            )[Constants.LINK_CONNECTIONS_DICT]
            if self.db_instance.read_from_db(
                MongoCollections.LINKS, Constants.LINK_CONNECTIONS_DICT
            )
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
                    MongoCollections.LINKS,
                    Constants.LINK_CONNECTIONS_DICT,
                    json.dumps(link_connections_dict),
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
                    MongoCollections.LINKS,
                    Constants.LINK_CONNECTIONS_DICT,
                    json.dumps(link_connections_dict),
                )

                interdomain_a = link.get("uni_z", {}).get("port_id")

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
                "service_id": connection_request.get("id"),
                "link": link,
            }
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

        try:
            breakdown = te_manager.generate_connection_breakdown(
                solution, connection_request
            )
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.BREAKDOWNS, connection_request["id"], breakdown
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
        connection_request = self.db_instance.read_from_db(
            MongoCollections.CONNECTIONS, service_id
        )
        if not connection_request:
            return

        connection_request_str = connection_request[service_id]
        self.db_instance.delete_one_entry(MongoCollections.CONNECTIONS, service_id)

        historical_connections = self.db_instance.read_from_db(
            MongoCollections.HISTORICAL_CONNECTIONS, service_id
        )
        # Current timestamp in seconds
        timestamp = int(time.time())

        if historical_connections:
            historical_connections_list = historical_connections[service_id]
            historical_connections_list.append(
                json.dumps({timestamp: json.loads(connection_request_str)})
            )
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.HISTORICAL_CONNECTIONS,
                service_id,
                historical_connections_list,
            )
        else:
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.HISTORICAL_CONNECTIONS,
                service_id,
                [json.dumps({timestamp: json.loads(connection_request_str)})],
            )
        logger.debug(f"Archived connection: {service_id}")

    def remove_connection(self, te_manager, service_id) -> Tuple[str, int]:
        te_manager.delete_connection(service_id)
        connection_request = self.db_instance.read_from_db(
            MongoCollections.CONNECTIONS, service_id
        )
        if not connection_request:
            return "Did not find connection request, cannot remove connection", 404

        connection_request = connection_request[service_id]

        breakdown = self.db_instance.read_from_db(
            MongoCollections.BREAKDOWNS, service_id
        )
        if not breakdown:
            return "Did not find breakdown, cannot remove connection", 404
        breakdown = breakdown[service_id]

        try:
            status, code = self._send_breakdown_to_lc(
                breakdown, "delete", json.loads(connection_request)
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

    def handle_link_failure(self, te_manager, failed_links):
        logger.debug("Handling connections that contain failed link.")
        link_connections_dict_str = self.db_instance.read_from_db(
            MongoCollections.LINKS, Constants.LINK_CONNECTIONS_DICT
        )

        if (
            not link_connections_dict_str
            or not link_connections_dict_str[Constants.LINK_CONNECTIONS_DICT]
        ):
            logger.debug("No connection has been placed yet.")
            return

        link_connections_dict = json.loads(
            link_connections_dict_str[Constants.LINK_CONNECTIONS_DICT]
        )

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
                connections = link_connections_dict[simple_link]
                for index, connection in enumerate(connections):
                    logger.info(
                        f"Connection {connection['id']} affected by link {link['id']}"
                    )
                    if "id" not in connection:
                        continue

                    try:
                        self.remove_connection(te_manager, connection["id"])
                    except Exception as err:
                        logger.info(
                            f"Encountered error when deleting connection: {err}"
                        )
                        continue

                    del link_connections_dict[simple_link][index]
                    logger.debug("Removed connection:")
                    logger.debug(connection)
                    _reason, code = self.place_connection(te_manager, connection)
                    if code // 100 == 2:
                        self.db_instance.add_key_value_pair_to_db(
                            MongoCollections.CONNECTIONS,
                            connection["id"],
                            json.dumps(connection),
                        )

    def get_archived_connections(self, service_id: str):
        historical_connections = self.db_instance.read_from_db(
            MongoCollections.HISTORICAL_CONNECTIONS, service_id
        )
        if not historical_connections:
            return None
        return historical_connections[service_id]


def topology_db_update(db_instance, te_manager):
    # update OXP topology in DB:
    oxp_topology_map = te_manager.topology_manager.get_topology_map()
    for domain_name, topology in oxp_topology_map.items():
        msg_json = topology.to_dict()
        db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, domain_name, json.dumps(msg_json)
        )
    # use 'latest_topo' as PK to save latest full topo to db
    latest_topo = json.dumps(te_manager.topology_manager.get_topology().to_dict())
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
        return None

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
        request_dict = json.loads(request.get(service_id))
        name = request_dict.get("name")
        description = request_dict.get("description")
        qos_metrics = request_dict.get("qos_metrics")
        scheduling = request_dict.get("scheduling")
        notifications = request_dict.get("notifications")
        oxp_response_code = request_dict.get("oxp_response_code")
        oxp_response = request_dict.get("oxp_response")
        if request_dict.get("endpoints") is not None:  # spec version 2.0.0
            request_endpoints = request_dict.get("endpoints")
            request_uni_a = request_endpoints[0]
            request_uni_a_id = request_uni_a.get("port_id")
            if request_uni_a_id is None:
                request_uni_a_id = request_uni_a.get("id")
            request_uni_z = request_endpoints[1]
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

    if oxp_response_code:
        response[service_id]["oxp_response_code"] = oxp_response_code

    if oxp_response:
        response[service_id]["oxp_response"] = oxp_response

    logger.info(f"Formed a response: {response}")

    return response

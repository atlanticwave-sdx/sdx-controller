import json
import logging
from copy import deepcopy

from sdx_datamodel.connection_sm import ConnectionStateMachine
from sdx_datamodel.constants import Constants, DomainStatus, MongoCollections

from sdx_controller.handlers.connection_handler import (
    ConnectionHandler,
    connection_state_machine,
)
from sdx_controller.utils.parse_helper import ParseHelper

logger = logging.getLogger(__name__)


class LcMessageHandler:
    def __init__(self, db_instance, te_manager):
        self.db_instance = db_instance
        self.te_manager = te_manager
        self.parse_helper = ParseHelper()
        self.connection_handler = ConnectionHandler(db_instance)

    def _previous_vlan_ranges_by_port(self, topology):
        vlan_ranges = {}
        if not topology:
            return vlan_ranges

        for node in topology.get("nodes", []):
            for port in node.get("ports", []):
                port_id = port.get("id")
                if not port_id:
                    continue

                services = port.get("services") or {}
                for service_name in ("l2vpn-ptp", "l2vpn_ptp"):
                    service = services.get(service_name)
                    if service and service.get("vlan_range"):
                        vlan_ranges[port_id] = deepcopy(service["vlan_range"])
                        break

        return vlan_ranges

    def _is_valid_vlan_range(self, vlan_range):
        if not vlan_range or not isinstance(vlan_range, list):
            return False

        for item in vlan_range:
            parsed_item = item
            if isinstance(parsed_item, str):
                parsed_item = [
                    int(vlan) for vlan in parsed_item.split("-") if vlan.isdigit()
                ]
                if len(parsed_item) == 1:
                    parsed_item = parsed_item[0]

            if isinstance(parsed_item, int):
                if parsed_item < 0 or parsed_item > 4095:
                    return False
                continue

            if not isinstance(parsed_item, list) or len(parsed_item) != 2:
                return False

            if not all(isinstance(vlan, int) for vlan in parsed_item):
                return False

            if (
                parsed_item[0] > parsed_item[1]
                or parsed_item[0] < 0
                or parsed_item[1] < 0
                or parsed_item[0] > 4095
                or parsed_item[1] > 4095
            ):
                return False

        return True

    def _sanitize_vlan_ranges(self, topology_update, latest_topo):
        previous_vlan_ranges = self._previous_vlan_ranges_by_port(latest_topo)

        for node in topology_update.get("nodes", []):
            for port in node.get("ports", []):
                port_id = port.get("id")
                services = port.get("services") or {}
                previous_vlan_range = previous_vlan_ranges.get(port_id)

                for service_name in ("l2vpn-ptp", "l2vpn_ptp"):
                    service = services.get(service_name)
                    if not service or "vlan_range" not in service:
                        continue

                    vlan_range = service.get("vlan_range")
                    if self._is_valid_vlan_range(vlan_range):
                        continue

                    if previous_vlan_range:
                        logger.warning(
                            "Ignoring invalid VLAN range %s on port %s; keeping %s",
                            vlan_range,
                            port_id,
                            previous_vlan_range,
                        )
                        service["vlan_range"] = deepcopy(previous_vlan_range)
                    else:
                        logger.warning(
                            "Ignoring invalid VLAN range %s on port %s; using the "
                            "default valid range",
                            vlan_range,
                            port_id,
                        )
                        service["vlan_range"] = [[1, 4095]]

    def process_lc_json_msg(
        self,
        msg,
        latest_topo,
        domain_dict,
    ):
        logger.info("MQ received message:" + str(msg))
        msg_json = json.loads(msg)

        if (
            msg_json.get("msg_type")
            and msg_json["msg_type"] == "oxp_conn_status_change"
        ):

            service_id = msg_json.get("service_id")
            new_status = msg_json.get("new_status")
            existing_status = msg_json.get("existing_status")
            logger.info(
                f"Received OXP connection status change. service_id={service_id}, existing_status={existing_status}, new_status={new_status}."
            )

            if not service_id or new_status is None:
                return

            connection = self.db_instance.get_value_from_db(
                MongoCollections.CONNECTIONS, service_id
            )
            if not connection:
                return

            current_status = connection.get("status")

            # If status is unchanged, do nothing
            if current_status == new_status:
                logger.debug(f"Status unchanged for {service_id}")
                return

            logger.info(
                f"Updating connection {service_id} status: "
                f"{current_status} -> {new_status}"
            )

            # Directly reflect LC/OXP status into controller DB
            connection["status"] = new_status

            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.CONNECTIONS,
                service_id,
                connection,
            )
            logger.info(f"Connection {service_id} status updated.")
            return
        elif msg_json.get("msg_type") and msg_json["msg_type"] == "oxp_conn_response":
            logger.info("Received OXP connection response.")
            service_id = msg_json.get("service_id")

            if not service_id:
                return

            connection = self.db_instance.get_value_from_db(
                MongoCollections.CONNECTIONS, service_id
            )

            if not connection:
                return

            breakdown = self.db_instance.get_value_from_db(
                MongoCollections.BREAKDOWNS, service_id
            )
            if not breakdown:
                logger.info(f"Could not find breakdown for {service_id}")
                return None

            conn_status = connection.get("status")
            oxp_number = len(breakdown)
            oxp_success_count = connection.get("oxp_success_count", 0)
            lc_domain = msg_json.get("lc_domain")
            response_domain = msg_json.get("breakdown_domain") or lc_domain
            oxp_response_code = msg_json.get("oxp_response_code")
            oxp_response_msg = msg_json.get("oxp_response")
            operation = msg_json.get("operation")
            oxp_response = connection.get("oxp_response")
            if not oxp_response:
                oxp_response = {}

            existing_domain_response = oxp_response.get(response_domain)
            if (
                operation == "delete"
                and isinstance(existing_domain_response, (list, tuple))
                and len(existing_domain_response) > 1
                and isinstance(existing_domain_response[1], dict)
                and existing_domain_response[1].get("service_id")
            ):
                preserved_payload = dict(existing_domain_response[1])
                if isinstance(oxp_response_msg, dict):
                    preserved_payload.update(oxp_response_msg)
                oxp_response[response_domain] = (oxp_response_code, preserved_payload)
            else:
                oxp_response[response_domain] = (oxp_response_code, oxp_response_msg)
            connection["oxp_response"] = oxp_response
            partial_cleanup_requested = connection.get(
                "partial_cleanup_requested", False
            )
            late_cleanup_domains = connection.get("late_cleanup_domains", [])

            if oxp_response_code // 100 == 2:
                if operation != "delete":
                    if partial_cleanup_requested:
                        if lc_domain not in late_cleanup_domains:
                            cleanup_status, cleanup_code = (
                                self.connection_handler.cleanup_partial_connection_domain(
                                    service_id, connection, lc_domain
                                )
                            )
                            logger.info(
                                f"Late partial cleanup result for {service_id} in {lc_domain}: {cleanup_status}, code={cleanup_code}"
                            )
                            late_cleanup_domains.append(lc_domain)
                            connection["late_cleanup_domains"] = late_cleanup_domains
                    else:
                        oxp_success_count += 1
                        connection["oxp_success_count"] = oxp_success_count
                        logger.info(
                            f"Update oxp_success_count: {oxp_success_count}; oxp_number: {oxp_number}"
                        )
                        if oxp_success_count == oxp_number:
                            if connection.get("status") and (
                                connection.get("status")
                                == str(ConnectionStateMachine.State.RECOVERING)
                            ):
                                connection, _ = connection_state_machine(
                                    connection,
                                    ConnectionStateMachine.State.UNDER_PROVISIONING,
                                )
                            connection, _ = connection_state_machine(
                                connection, ConnectionStateMachine.State.UP
                            )
            else:
                if connection.get("status") and (
                    connection.get("status")
                    == str(ConnectionStateMachine.State.MODIFYING)
                    or connection.get("status")
                    == str(ConnectionStateMachine.State.UNDER_PROVISIONING)
                ):
                    connection, _ = connection_state_machine(
                        connection, ConnectionStateMachine.State.DOWN
                    )
                if operation == "post" and not partial_cleanup_requested:
                    connection["partial_cleanup_requested"] = True
                    cleanup_status, cleanup_code = (
                        self.connection_handler.cleanup_partial_connection(
                            self.te_manager, service_id, connection
                        )
                    )
                    logger.info(
                        f"Partial cleanup result for {service_id}: {cleanup_status}, code={cleanup_code}"
                    )

            # ToDo: eg: if 3 oxps in the breakdowns: (1) all up: up (2) parital down: remove_connection()
            # release successful oxp circuits if some are down: remove_connection() (3) count the responses
            # to finalize the status of the connection.
            self.db_instance.update_field_in_json(
                MongoCollections.CONNECTIONS,
                service_id,
                "status",
                connection.get("status"),
            )
            self.db_instance.update_field_in_json(
                MongoCollections.CONNECTIONS,
                service_id,
                "oxp_response",
                oxp_response,
            )
            self.db_instance.update_field_in_json(
                MongoCollections.CONNECTIONS,
                service_id,
                "oxp_success_count",
                oxp_success_count,
            )
            logger.info("Connection updated: " + str(connection))
            return

        # topology message RPC from OXP: no exchange name is defined.
        msg_id = msg_json["id"]
        msg_version = msg_json["version"]

        domain_name = self.parse_helper.find_domain_name(msg_id, ":")
        msg_json["domain_name"] = domain_name
        self._sanitize_vlan_ranges(msg_json, latest_topo)

        db_msg_id = str(msg_id) + "-" + str(msg_version)
        # add message to db
        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, db_msg_id, msg_json
        )
        logger.info("Save to database complete.")
        logger.info("message ID:" + str(db_msg_id))

        # Update existing topology
        if domain_name in domain_dict:
            logger.info("Updating topo")
            logger.debug(msg_json)
            (
                removed_nodes,
                added_nodes,
                removed_links,
                added_links,
                uni_ports_up_to_down,
                uni_ports_down_to_up,
            ) = self.te_manager.update_topology(msg_json)
            logger.info("Updating topology in TE manager")
            if removed_links and len(removed_links) > 0:
                logger.info("Processing removed link.")
                self.connection_handler.handle_link_removal(
                    self.te_manager, removed_links
                )
            # failed_links = self.te_manager.get_failed_links()
            # if failed_links:
            #    logger.info("Processing link failure.")
            #    self.connection_handler.handle_link_failure(
            #        self.te_manager, failed_links
            #    )
            if uni_ports_up_to_down:
                logger.info(f"Processing uni ports up to down:{uni_ports_up_to_down}")
                self.connection_handler.handle_uni_ports_up_to_down(
                    uni_ports_up_to_down
                )
            if uni_ports_down_to_up:
                logger.info(f"Processing uni ports down to up:{uni_ports_down_to_up}")
                self.connection_handler.handle_uni_ports_down_to_up(
                    uni_ports_down_to_up
                )

        # Add new topology
        else:
            domain_dict[domain_name] = DomainStatus.UP
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.DOMAINS, Constants.DOMAIN_DICT, domain_dict
            )
            logger.info("Adding topology to TE manager")
            self.te_manager.add_topology(msg_json)

        # Save to database
        # ToDo: check if there is any change in topology update, if not, do not re-save to db.
        logger.info(f"Adding topology {domain_name} to db.")
        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, msg_id, msg_json
        )

        latest_topo = self.te_manager.topology_manager.get_topology().to_dict()
        # use 'latest_topo' as PK to save latest topo to db
        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY, latest_topo
        )
        logger.info("Save to database complete.")

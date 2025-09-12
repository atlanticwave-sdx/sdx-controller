import json
import logging

from sdx_datamodel.connection_sm import ConnectionStateMachine
from sdx_datamodel.constants import Constants, MongoCollections

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

    def process_lc_json_msg(
        self,
        msg,
        latest_topo,
        domain_list,
    ):
        logger.info("MQ received message:" + str(msg))
        msg_json = json.loads(msg)

        if msg_json.get("msg_type") and msg_json["msg_type"] == "oxp_conn_response":
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

            oxp_number = len(breakdown)
            oxp_success_count = connection.get("oxp_success_count", 0)
            lc_domain = msg_json.get("lc_domain")
            oxp_response_code = msg_json.get("oxp_response_code")
            oxp_response_msg = msg_json.get("oxp_response")
            oxp_response = connection.get("oxp_response")
            if not oxp_response:
                oxp_response = {}
            oxp_response[lc_domain] = (oxp_response_code, oxp_response_msg)
            connection["oxp_response"] = oxp_response

            if oxp_response_code // 100 == 2:
                if msg_json.get("operation") != "delete":
                    oxp_success_count += 1
                    connection["oxp_success_count"] = oxp_success_count
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
                    == str(ConnectionStateMachine.State.RECOVERING)
                ):
                    connection, _ = connection_state_machine(
                        connection, ConnectionStateMachine.State.ERROR
                    )
                elif (
                    connection.get("status")
                    and connection.get("status")
                    != str(ConnectionStateMachine.State.DOWN)
                    and connection.get("status")
                    != str(ConnectionStateMachine.State.ERROR)
                ):
                    connection, _ = connection_state_machine(
                        connection, ConnectionStateMachine.State.MODIFYING
                    )
                    connection, _ = connection_state_machine(
                        connection, ConnectionStateMachine.State.DOWN
                    )

            # ToDo: eg: if 3 oxps in the breakdowns: (1) all up: up (2) parital down: remove_connection()
            # release successful oxp circuits if some are down: remove_connection() (3) count the responses
            # to finalize the status of the connection.
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.CONNECTIONS,
                service_id,
                connection,
            )
            logger.info("Connection updated: " + service_id)
            return

        # topology message RPC from OXP: no exchange name is defined.
        msg_id = msg_json["id"]
        msg_version = msg_json["version"]

        domain_name = self.parse_helper.find_domain_name(msg_id, ":")
        msg_json["domain_name"] = domain_name

        db_msg_id = str(msg_id) + "-" + str(msg_version)
        # add message to db
        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, db_msg_id, msg_json
        )
        logger.info("Save to database complete.")
        logger.info("message ID:" + str(db_msg_id))

        # Update existing topology
        if domain_name in domain_list:
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
            domain_list.append(domain_name)
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.DOMAINS, Constants.DOMAIN_LIST, domain_list
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

import json
import logging

from sdx_datamodel.connection_sm import ConnectionStateMachine
from sdx_datamodel.constants import Constants, MongoCollections

from sdx_controller.handlers.connection_handler import (
    ConnectionHandler,
    connection_state_machine,
    get_connection_status,
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

            connection = self.db_instance.read_from_db(
                MongoCollections.CONNECTIONS, service_id
            )

            if not connection:
                return

            breakdown = self.db_instance.read_from_db(
                MongoCollections.BREAKDOWNS, service_id
            )
            if not breakdown:
                logger.info(f"Could not find breakdown for {service_id}")
                return None

            domains = breakdown.get(service_id)
            oxp_number = len(domains)

            connection_json = json.loads(connection[service_id])
            oxp_success_count = connection_json.get("oxp_success_count", 0)
            lc_domain = msg_json.get("lc_domain")
            oxp_response_code = msg_json.get("oxp_response_code")
            oxp_response_msg = msg_json.get("oxp_response")
            oxp_response = connection_json.get("oxp_response")
            if not oxp_response:
                oxp_response = {}
            oxp_response[lc_domain] = (oxp_response_code, oxp_response_msg)
            connection_json["oxp_response"] = oxp_response

            if oxp_response_code // 100 == 2:
                oxp_success_count += 1
                connection_json["oxp_success_count"] = oxp_success_count
                if oxp_success_count == oxp_number:
                    connection_json, _ = connection_state_machine(
                        connection_json, ConnectionStateMachine.State.UP
                    )
            else:
                connection_json, _ = connection_state_machine(
                    connection_json, ConnectionStateMachine.State.DOWN
                )

            # ToDo: eg: if 3 oxps in the breakdowns: (1) all up: up (2) parital down: remove_connection()
            # release successful oxp circuits if some are down: remove_connection() (3) count the responses
            # to finalize the status of the connection.
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.CONNECTIONS,
                service_id,
                json.dumps(connection_json),
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
            MongoCollections.TOPOLOGIES, db_msg_id, msg
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
            ) = self.te_manager.update_topology(msg_json)
            logger.info("Updating topology in TE manager")
            if removed_links and len(removed_links) > 0:
                logger.info("Processing removed link.")
                self.connection_handler.handle_link_failure(
                    self.te_manager, removed_links
                )
            failed_links = self.te_manager.get_failed_links()
            if failed_links:
                logger.info("Processing link failure.")
                self.connection_handler.handle_link_failure(
                    self.te_manager, failed_links
                )
            if (
                len(added_links) > 0
                or len(removed_links) > 0
                or len(added_nodes) > 0
                or len(removed_nodes) > 0
                or failed_links is not None
            ):
                logger.info("Update topology change in DB.")
                # update OXP topology in DB:
                self.db_instance.add_key_value_pair_to_db(
                    MongoCollections.TOPOLOGIES, domain_name, json.dumps(msg_json)
                )
                # use 'latest_topo' as PK to save latest full topo to db
                latest_topo = json.dumps(
                    self.te_manager.topology_manager.get_topology().to_dict()
                )
                self.db_instance.add_key_value_pair_to_db(
                    MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY, latest_topo
                )
                logger.info("Save to database complete.")
        # Add new topology
        else:
            domain_list.append(domain_name)
            self.db_instance.add_key_value_pair_to_db(
                MongoCollections.DOMAINS, Constants.DOMAIN_LIST, domain_list
            )
            logger.info("Adding topology to TE manager")
            self.te_manager.add_topology(msg_json)

        logger.info(f"Adding topology {domain_name} to db.")
        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, domain_name, json.dumps(msg_json)
        )

        # TODO: use TEManager API directly; but TEManager does not
        # expose a `get_topology()` method yet.
        latest_topo = json.dumps(
            self.te_manager.topology_manager.get_topology().to_dict()
        )
        # use 'latest_topo' as PK to save latest topo to db
        self.db_instance.add_key_value_pair_to_db(
            MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY, latest_topo
        )
        logger.info("Save to database complete.")

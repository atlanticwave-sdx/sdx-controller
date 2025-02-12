import json
import logging

from sdx_controller.handlers.connection_handler import ConnectionHandler
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

            connection = self.db_instance.read_from_db("connections", service_id)

            if not connection:
                return

            connection_json = json.loads(connection[service_id])
            oxp_response_code = msg_json.get("oxp_response_code")
            connection_json["oxp_response_code"] = oxp_response_code
            connection_json["oxp_response"] = msg_json.get("oxp_response")

            if oxp_response_code // 100 != 2:
                connection_json["status"] = "down"
            elif not connection_json.get("status"):
                connection_json["status"] = "up"

            self.db_instance.add_key_value_pair_to_db(
                "connections", service_id, json.dumps(connection_json)
            )
            logger.info("Connection updated: " + service_id)
            return

        msg_id = msg_json["id"]
        msg_version = msg_json["version"]

        domain_name = self.parse_helper.find_domain_name(msg_id, ":")
        msg_json["domain_name"] = domain_name

        db_msg_id = str(msg_id) + "-" + str(msg_version)
        # add message to db
        self.db_instance.add_key_value_pair_to_db("topologies", db_msg_id, msg)
        logger.info("Save to database complete.")
        logger.info("message ID:" + str(db_msg_id))

        # Update existing topology
        if domain_name in domain_list:
            logger.info("Updating topo")
            logger.debug(msg_json)
            self.te_manager.update_topology(msg_json)
            logger.info("Updating topology in TE manager")
            failed_links = self.te_manager.get_failed_links()
            if failed_links:
                logger.info("Processing link failure.")
                self.connection_handler.handle_link_failure(
                    self.te_manager, failed_links
                )
            #check topology modification:
            #node, port or link modification
            #new version of topology
            if latest_topo:
                self.db_instance.add_key_value_pair_to_db(
                    "topologies", "latest_topo", latest_topo
                )
        # Add new topology
        else:
            domain_list.append(domain_name)
            self.db_instance.add_key_value_pair_to_db(
                "domains", "domain_list", domain_list
            )
            logger.info("Adding topology to TE manager")
            self.te_manager.add_topology(msg_json)

        logger.info(f"Adding topology {domain_name} to db.")
        self.db_instance.add_key_value_pair_to_db(
            "topologies", domain_name, json.dumps(msg_json)
        )

        # TODO: use TEManager API directly; but TEManager does not
        # expose a `get_topology()` method yet.
        # Get latest topology and save to db
        # and individual OXP topology
        latest_topo = json.dumps(
            self.te_manager.topology_manager.get_topology().to_dict()
        )
        # use 'latest_topo' as PK to save latest topo to db
        self.db_instance.add_key_value_pair_to_db(
            "topologies", "latest_topo", latest_topo
        )
        logger.info("Save to database complete.")

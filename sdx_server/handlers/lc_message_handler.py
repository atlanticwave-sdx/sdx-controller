import json
import logging

from swagger_server.handlers.connection_handler import ConnectionHandler
from swagger_server.utils.parse_helper import ParseHelper

logger = logging.getLogger(__name__)


class LcMessageHandler:
    def __init__(self, db_instance, manager):
        self.db_instance = db_instance
        self.manager = manager
        self.parse_helper = ParseHelper()
        self.connection_handler = ConnectionHandler(db_instance)

    def process_lc_json_msg(
        self,
        msg,
        latest_topo,
        domain_list,
        num_domain_topos,
    ):
        logger.info("MQ received message:" + str(msg))
        msg_json = json.loads(msg)
        msg_id = msg_json["id"]
        msg_version = msg_json["version"]

        lc_queue_name = msg_json["lc_queue_name"]
        logger.debug("Processing LC message: lc_queue_name:")
        logger.debug(lc_queue_name)

        domain_name = self.parse_helper.find_between(msg_id, "topology:", ".net")
        msg_json["domain_name"] = domain_name

        db_msg_id = str(msg_id) + "-" + str(msg_version)
        # add message to db
        self.db_instance.add_key_value_pair_to_db(db_msg_id, msg)
        logger.info("Save to database complete.")
        logger.info("message ID:" + str(db_msg_id))

        # Update existing topology
        if domain_name in domain_list:
            logger.info("Updating topo")
            logger.debug(msg_json)
            self.manager.update_topology(msg_json)
            if "link_failure" in msg_json:
                logger.info("Processing link failure.")
                self.connection_handler.handle_link_failure(msg_json)
        # Add new topology
        else:
            domain_list.append(domain_name)
            self.db_instance.add_key_value_pair_to_db("domain_list", domain_list)

            logger.info("Adding topo")
            self.manager.add_topology(msg_json)

            if self.db_instance.read_from_db("num_domain_topos") is None:
                num_domain_topos = 1
                self.db_instance.add_key_value_pair_to_db(
                    "num_domain_topos", num_domain_topos
                )
            else:
                num_domain_topos = len(domain_list)
                num_domain_topos = int(num_domain_topos) + 1
                self.db_instance.add_key_value_pair_to_db(
                    "num_domain_topos", num_domain_topos
                )

        logger.info("Adding topo to db.")
        db_key = "LC-" + str(num_domain_topos)
        self.db_instance.add_key_value_pair_to_db(db_key, json.dumps(msg_json))

        latest_topo = json.dumps(self.manager.get_topology().to_dict())
        # use 'latest_topo' as PK to save latest topo to db
        self.db_instance.add_key_value_pair_to_db("latest_topo", latest_topo)
        logger.info("Save to database complete.")

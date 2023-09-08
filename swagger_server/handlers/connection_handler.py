import json
import logging

from swagger_server.models.simple_link import SimpleLink

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)


class ConnectionHandler:
    def __init__(self, db_instance):
        self.db_instance = db_instance
        pass

    def remove_connection(self, connection):
        # call pce to remove connection
        pass

    def place_connection(self, connection):
        # call pce to generate breakdown, and place connection
        pass

    def handle_link_failure(self, msg_json):
        logger.debug("Handling connections that contain failed link.")
        if self.db_instance.read_from_db("link_connections_dict") is None:
            logger.debug("No connection has been placed yet.")
            return
        link_connections_dict_str = self.db_instance.read_from_db(
            "link_connections_dict"
        )

        if link_connections_dict_str:
            link_connections_dict = json.loads(
                link_connections_dict_str["link_connections_dict"]
            )
        else:
            logger.debug("Failed to retrieve link_connections_dict from DB.")

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

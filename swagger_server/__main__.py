#!/usr/bin/env python3

import json
import logging
import os
import threading
from queue import Queue

import connexion
from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.topology.manager import TopologyManager
from sdx_pce.topology.temanager import TEManager

from swagger_server import encoder
from swagger_server.messaging.rpc_queue_consumer import RpcConsumer
from swagger_server.utils.db_utils import DbUtils
from swagger_server.models.simple_link import SimpleLink

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOG_FILE = os.environ.get("LOG_FILE")


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError as e:
        return False
    return True


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""

def _remove_connection(connection, db_instance):
    # call pce to remove connection
    pass

def _place_connection(connection, db_instance):
    # call pce to generate breakdown, and place connection
    pass

def _handle_link_failure(db_instance, msg_json):
    logger.debug("Handling connections that contain failed link.")
    if db_instance.read_from_db("link_connections_dict") is None:
        logger.debug("No connection has been placed yet.")
        return
    link_connections_dict_str = db_instance.read_from_db("link_connections_dict")

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
                _remove_connection(connection, db_instance)
                del link_connections_dict[simple_link][index]
                logger.debug("Removed connection:")
                logger.debug(connection)
                _place_connection(connection, db_instance)
                link_connections_dict[simple_link].append(connection)
                logger.debug("Placed connection:")
                logger.debug(connection)
    
    db_instance.add_key_value_pair_to_db(
                "link_connections_dict", json.dumps(link_connections_dict)
            )


def process_lc_json_msg(
    msg,
    db_instance,
    latest_topo,
    domain_list,
    manager,
    num_domain_topos,
):
    logger.info("MQ received message:" + str(msg))
    msg_json = json.loads(msg)
    msg_id = msg_json["id"]
    msg_version = msg_json["version"]

    lc_queue_name = msg_json["lc_queue_name"]
    logger.debug("---lc_queue_name:---")
    logger.debug(lc_queue_name)

    domain_name = find_between(msg_id, "topology:", ".net")
    msg_json["domain_name"] = domain_name

    db_msg_id = str(msg_id) + "-" + str(msg_version)
    # add message to db
    db_instance.add_key_value_pair_to_db(db_msg_id, msg)
    logger.info("Save to database complete.")
    logger.info("message ID:" + str(db_msg_id))

    # Update existing topology
    if domain_name in domain_list:
        logger.info("Updating topo")
        manager.update_topology(msg_json)
        if "link_failure" in msg_json:
            logger.info("Processing link failure.")
            _handle_link_failure(db_instance, msg_json)
    # Add new topology
    else:
        domain_list.append(domain_name)
        db_instance.add_key_value_pair_to_db("domain_list", domain_list)

        logger.info("adding topo")
        manager.add_topology(msg_json)

        if db_instance.read_from_db("num_domain_topos") is None:
            num_domain_topos = 1
            db_instance.add_key_value_pair_to_db("num_domain_topos", num_domain_topos)
        else:
            num_domain_topos = len(domain_list)
            num_domain_topos = int(num_domain_topos) + 1
            db_instance.add_key_value_pair_to_db("num_domain_topos", num_domain_topos)

    logger.info("adding topo to db:")
    db_key = "LC-" + str(num_domain_topos)
    db_instance.add_key_value_pair_to_db(db_key, json.dumps(msg_json))

    latest_topo = json.dumps(manager.get_topology().to_dict())
    # use 'latest_topo' as PK to save latest topo to db
    db_instance.add_key_value_pair_to_db("latest_topo", latest_topo)
    logger.info("Save to database complete.")


def start_consumer(thread_queue, db_instance):
    MESSAGE_ID = 0
    HEARTBEAT_ID = 0
    rpc = RpcConsumer(thread_queue, "")
    t1 = threading.Thread(target=rpc.start_consumer, args=())
    t1.start()

    manager = TopologyManager()

    latest_topo = {}
    domain_list = []


    if db_instance.read_from_db("domain_list") is not None:
        domain_list = db_instance.read_from_db("domain_list")["domain_list"]

    num_domain_topos = len(domain_list)

    if db_instance.read_from_db("num_domain_topos") is not None:
        db_instance.add_key_value_pair_to_db("num_domain_topos", num_domain_topos)
        for topo in range(1, num_domain_topos + 1):
            db_key = f"LC-{topo}"
            logger.debug(f"Reading {db_key} from DB")
            topology = db_instance.read_from_db(db_key)
            logger.debug(f"Read {db_key}: {topology}")
            if topology is None:
                continue
            else:
                # Get the actual thing minus the Mongo ObjectID.
                topology = topology[db_key]
            topo_json = json.loads(topology)
            manager.add_topology(topo_json)

    while True:
        # Queue.get() will block until there's an item in the queue.
        msg = thread_queue.get()
        logger.debug("MQ received message:" + str(msg))

        if "Heart Beat" in str(msg):
            HEARTBEAT_ID += 1
            logger.debug("Heart beat received. ID: " + str(HEARTBEAT_ID))
        else:
            logger.info("Saving to database.")
            if is_json(msg):
                if "version" in str(msg):
                    process_lc_json_msg(
                        msg,
                        db_instance,
                        latest_topo,
                        domain_list,
                        manager,
                        num_domain_topos,
                    )
                else:
                    logger.info("got message from MQ: " + str(msg))
            else:
                db_instance.add_key_value_pair_to_db(str(MESSAGE_ID), msg)
                logger.debug("Save to database complete.")
                logger.debug("message ID:" + str(MESSAGE_ID))
                value = db_instance.read_from_db(str(MESSAGE_ID))
                logger.debug("got value from DB:")
                logger.debug(value)
                MESSAGE_ID += 1


def main():
    if LOG_FILE:
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO)

    # Run swagger service
    app = connexion.App(__name__, specification_dir="./swagger/")
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(
        "swagger.yaml", arguments={"title": "SDX-Controller"}, pythonic_params=True
    )

    # Run swagger in a thread
    threading.Thread(target=lambda: app.run(port=8080)).start()

    # Get DB connection and tables set up.
    db_instance = DbUtils()
    db_instance.initialize_db()

    thread_queue = Queue()
    start_consumer(thread_queue, db_instance)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import argparse
import json
import logging
import threading
import time
from optparse import OptionParser

import connexion
from sdx.datamodel import parsing, topologymanager, validation
from sdx.datamodel.parsing.exceptions import DataModelException
from sdx.datamodel.parsing.topologyhandler import TopologyHandler
from sdx.datamodel.topologymanager.grenmlconverter import GrenmlConverter
from sdx.datamodel.topologymanager.manager import TopologyManager
from sdx.datamodel.validation.topologyvalidator import TopologyValidator

from swagger_server import encoder
from swagger_server.messaging.rpc_queue_consumer import *
from swagger_server.utils.db_utils import *

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)


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
        logger.info("updating topo")
        manager.update_topology(msg_json)
    # Add new topology
    else:
        domain_list.add(domain_name)
        logger.info("adding topo")
        manager.add_topology(msg_json)

        if db_instance.read_from_db("num_domain_topos") is None:
            num_domain_topos = 1
            db_instance.add_key_value_pair_to_db("num_domain_topos", num_domain_topos)
        else:
            num_domain_topos = db_instance.read_from_db("num_domain_topos")[
                "num_domain_topos"
            ]
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
    num_domain_topos = 0

    if db_instance.read_from_db("num_domain_topos") is not None:
        db_instance.add_key_value_pair_to_db("num_domain_topos", num_domain_topos)

    latest_topo = {}
    domain_list = set()

    while True:
        if thread_queue.empty():
            continue

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
    logging.basicConfig(level=logging.INFO)

    # Run swagger service
    app = connexion.App(__name__, specification_dir="./swagger/")
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(
        "swagger.yaml", arguments={"title": "SDX-Controller"}, pythonic_params=True
    )

    # Run swagger in a thread
    threading.Thread(target=lambda: app.run(port=8080)).start()

    DB_NAME = os.environ.get("DB_NAME") + ".sqlite3"
    MANIFEST = os.environ.get("MANIFEST")

    # Get DB connection and tables set up.
    db_instance = DbUtils()
    db_instance.initialize_db()

    thread_queue = Queue()
    start_consumer(thread_queue, db_instance)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import connexion

from swagger_server import encoder
from swagger_server.messaging.rpc_queue_consumer import *
from swagger_server.utils.db_utils import *

from optparse import OptionParser
import argparse
import time
import threading
import logging
import json
# make sure to install datamodel:
# https://github.com/atlanticwave-sdx/datamodel
from datamodel.sdxdatamodel import parsing
from datamodel.sdxdatamodel import topologymanager

from datamodel.sdxdatamodel import validation
from datamodel.sdxdatamodel.validation.topologyvalidator import TopologyValidator
from datamodel.sdxdatamodel.parsing.topologyhandler import TopologyHandler
from datamodel.sdxdatamodel.topologymanager.manager import TopologyManager
from datamodel.sdxdatamodel.topologymanager.grenmlconverter import GrenmlConverter
from datamodel.sdxdatamodel.parsing.exceptions import DataModelException

def is_json(myjson):
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

def start_consumer(thread_queue, db_instance):
    logger = logging.getLogger(__name__)
    logging.getLogger("pika").setLevel(logging.WARNING)

    MESSAGE_ID = 0
    HEARTBEAT_ID = 0
    
    rpc = RpcConsumer(thread_queue, '')
    t1 = threading.Thread(target=rpc.start_consumer, args=())
    t1.start()

    manager = TopologyManager()

    while True:
        if not thread_queue.empty():
            msg = thread_queue.get()
            logger.info("MQ received message:" + str(msg))
            
            if 'Heart Beat' in str(msg):
                HEARTBEAT_ID += 1
                logger.info('Heart beat received. ID: ' + str(HEARTBEAT_ID))
            else:
                logger.info('Saving to database.')
                if is_json(msg):
                    if 'version' in str(msg):
                        msg_json = json.loads(msg)
                        msg_id = msg_json["id"]
                        msg_version = msg_json["version"]
                        db_msg_id = str(msg_id) + "-" + str(msg_version)
                        # add message to db
                        db_instance.add_key_value_pair_to_db(db_msg_id, msg)
                        logger.info('Save to database complete.')
                        logger.info('message ID:' + str(db_msg_id))
                        print("adding topo")
                        manager.add_topology(msg_json)
                        latest_topo = manager.get_topology()
                        print(latest_topo)
                        # use 'latest_topo' as PK to save latest topo to db
                        db_instance.add_key_value_pair_to_db('latest_topo', str(latest_topo))
                        topo_val = db_instance.read_from_db('latest_topo')
                    else:
                        logger.info('got message from MQ: ' + str(msg))
                else:
                    db_instance.add_key_value_pair_to_db(MESSAGE_ID, msg) 

                    logger.info('Save to database complete.')
                    logger.info('message ID:' + str(MESSAGE_ID))
                    value = db_instance.read_from_db(MESSAGE_ID)
                    logger.info('got value from DB:')
                    logger.info(value)
                    MESSAGE_ID += 1
                

def main():

    # Sleep 7 seconds waiting for RabbitMQ to be ready
    # time.sleep(7)
    
    logging.basicConfig(level=logging.INFO)
    
    # Run swagger service
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'SDX-Controller'}, pythonic_params=True)
    
    # Run swagger in a thread
    threading.Thread(target=lambda: app.run(port=8080)).start()
    # app.run(port=8080)

    DB_NAME = os.environ.get('DB_NAME') + '.sqlite3'
    MANIFEST = os.environ.get('MANIFEST')

    # Get DB connection and tables set up.
    db_tuples = [('config_table', "test-config")]

    db_instance = DbUtils()
    db_instance._initialize_db(DB_NAME, db_tuples)
    # amqp_url = 'amqp://guest:guest@aw-sdx-monitor.renci.org:5672/%2F'
    thread_queue = Queue()
    start_consumer(thread_queue, db_instance)        

if __name__ == '__main__':
    main()

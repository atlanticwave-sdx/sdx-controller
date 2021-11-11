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

def start_consumer(thread_queue, db_instance):
    logger = logging.getLogger(__name__)
    logging.getLogger("pika").setLevel(logging.WARNING)

    MESSAGE_ID = 0
    
    rpc = RpcConsumer(thread_queue)
    t1 = threading.Thread(target=rpc.start_consumer, args=())
    t1.start()

    while True:
        if not thread_queue.empty():
            msg = thread_queue.get()
            logger.info("MQ received message:" + str(msg))

            logger.info('Saving to database.')
            db_instance.add_key_value_pair_to_db(MESSAGE_ID, msg)            
            logger.info('Save to database complete.')

            logger.info('message ID:' + str(MESSAGE_ID))
            value = db_instance.read_from_db(MESSAGE_ID)
            logger.info('got value back:')
            logger.info(value)
            MESSAGE_ID += 1

def main():

    # Sleep 7 seconds waiting for RabbitMQ to be ready
    time.sleep(7)
    
    logging.basicConfig(level=logging.INFO)
    
    # Run swagger service
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'SDX-Controller'}, pythonic_params=True)
    
    # Run swagger in a thread
    threading.Thread(target=lambda: app.run(port=8080)).start()
    # app.run(port=8080)

    DB_NAME = os.environ.get('DB_NAME')
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

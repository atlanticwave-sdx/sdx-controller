#!/usr/bin/env python3

import connexion

from swagger_server import encoder
from swagger_server.messaging.message_queue_consumer import *
from swagger_server.messaging.rpc_queue_consumer import *
from swagger_server.messaging.async_consumer import *
from swagger_server.utils.db_utils import *

from optparse import OptionParser
import argparse
import time
import threading


def main():

    # Sleep 10 seconds waiting for RabbitMQ to be ready
    time.sleep(7)
    
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    

    # Run swagger service
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.app.config['DB'] = 'db_instance'
    app.add_api('swagger.yaml', arguments={'title': 'SDX-Controller'}, pythonic_params=True)
    
    app.run(port=8080)

if __name__ == '__main__':
    main()

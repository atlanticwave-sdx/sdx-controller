#!/usr/bin/env python3

import connexion

from swagger_server import encoder
from swagger_server.messaging.message_queue_consumer import *
from swagger_server.messaging.rpc_queue_consumer import *
from swagger_server.utils.db_utils import *

from optparse import OptionParser
import argparse

def main():
    parser = OptionParser()

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-m", "--manifest", dest="manifest", type=str, 
                        action="store", help="specifies the manifest")
    
    parser.add_argument("-d", "--database", dest="database", type=str, 
                         action="store", help="Specifies the database ", 
                         default=":memory:")

    options = parser.parse_args()
    print(options.manifest)

    # testing db
    dbname = options.database
    # Get DB connection and tables set up.
    db_tuples = [('config_table', "test-config")]
    
    db_util = DbUtils()
    db_util._initialize_db(dbname, db_tuples)

    # Start listening RabbitMQ
    # serverconfigure = RabbitMqServerConfigure(host='localhost',
    #                                         queue='hello')

    # server = rabbitmqServer(server=serverconfigure)
    # server.startserver()

    # message queue rpc test
    rpc = RpcClient()
    body = "test body"
    print("Published Message: {}".format(body))
    response = rpc.call(body)
    print(" [.] Got response: " + str(response))

    db_util.add_key_value_pair_to_db('test', body)
    db_util.read_from_db('test')


    # Run swagger service
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'SDX-Controller'}, pythonic_params=True)
    app.run(port=8080)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import connexion

from swagger_server import encoder
from swagger_server.messaging.message_queue_consumer import *
from swagger_server.messaging.rpc_queue_consumer import *
from swagger_server.utils.db_utils import *

from optparse import OptionParser
import argparse
import _pickle as pickle
import dataset

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

    # Run swagger service
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'SDX-Controller'}, pythonic_params=True)
    app.run(port=8080)

def add_manifest_filename_to_db(dbname, manifest_filename):
    # Pushes LC network configuration info into the DB.
    # key: "manifest_filename"
    # value: manifest_filename
    key = 'manifest_filename'
    value = pickle.dumps(manifest_filename)
    db = dataset.connect('sqlite:///' + dbname, 
                                  engine_kwargs={'connect_args':
                                                {'check_same_thread':False}})
    config_table_name = "test-config"
    config_table = db.load_table(config_table_name)
    print("Adding new manifest filename %s" %
                        manifest_filename)
    config_table.insert({'key':key, 'value':value})


if __name__ == '__main__':
    main()

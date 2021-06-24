#!/usr/bin/env python3

import connexion

from swagger_server import encoder
from swagger_server.messaging.message_queue import *


def main():
    # Start listening RabbitMQ
    serverconfigure = RabbitMqServerConfigure(host='localhost',
                                            queue='hello')

    server = rabbitmqServer(server=serverconfigure)
    server.startserver()

    # Run swagger service
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'SDX-Controller'}, pythonic_params=True)
    app.run(port=8080)


if __name__ == '__main__':
    main()

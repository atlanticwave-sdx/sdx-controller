import ast
import os

import pika

MQ_HOST = os.environ.get("MQ_HOST")


class MessageQueue:
    def __init__(self):
        pass


class MetaClass(type):
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(MetaClass, cls).__call__(*args, **kwargs)
            return cls._instance[cls]


class RabbitMqServerConfigure(metaclass=MetaClass):
    def __init__(self, host=MQ_HOST, queue="hello"):
        self.host = host
        self.queue = queue


class rabbitmqServer:
    def __init__(self, server):
        self.server = server
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.server.host)
        )
        self._channel = self._connection.channel()
        self._tem = self._channel.queue_declare(queue=self.server.queue)
        print("Server started waiting for Messages ")

    @staticmethod
    def callback(ch, method, properties, body):
        payload = body.decode("utf-8")
        payload = ast.literal_eval(payload)
        print(type(payload))
        print("Data Received : {}".format(payload))
        return payload

    def startserver(self):
        self._channel.basic_consume(
            queue=self.server.queue,
            on_message_callback=rabbitmqServer.callback,
            auto_ack=True,
        )
        self._channel.start_consuming()


if __name__ == "__main__":
    serverconfigure = RabbitMqServerConfigure(host=MQ_HOST, queue="hello")

    server = rabbitmqServer(server=serverconfigure)
    server.startserver()

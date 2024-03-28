import ast
import os

import pika

MQ_HOST = os.getenv("MQ_HOST")
MQ_PORT = os.getenv("MQ_PORT") or 5672
MQ_USER = os.getenv("MQ_USER") or "guest"
MQ_PASS = os.getenv("MQ_PASS") or "guest"


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
    def __init__(
        self,
        host=MQ_HOST,
        port=MQ_PORT,
        username=MQ_USER,
        password=MQ_PASS,
        queue="hello",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.queue = queue


class rabbitmqServer:
    def __init__(self, server):
        self.server = server
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.server.host,
                port=self.server.port,
                credentials=pika.PlainCredentials(
                    username=self.server.username,
                    password=self.server.password,
                ),
            )
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
    serverconfigure = RabbitMqServerConfigure(
        host=MQ_HOST,
        port=MQ_PORT,
        username=MQ_USER,
        password=MQ_PASS,
        queue="hello",
    )

    server = rabbitmqServer(server=serverconfigure)
    server.startserver()

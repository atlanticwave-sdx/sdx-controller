#!/usr/bin/env python
import logging
import os
import threading
from queue import Queue

import pika

MQ_HOST = os.environ.get("MQ_HOST")
# subscribe to the corresponding queue
SUB_QUEUE = os.environ.get("SUB_QUEUE")


class RpcConsumer(object):
    def __init__(self, thread_queue, exchange_name):
        self.logger = logging.getLogger(__name__)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=MQ_HOST)
        )

        self.channel = self.connection.channel()
        self.exchange_name = exchange_name

        self.channel.queue_declare(queue=SUB_QUEUE)
        self._thread_queue = thread_queue

    def on_request(self, ch, method, props, message_body):
        response = message_body
        self._thread_queue.put(message_body)

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=MQ_HOST)
        )
        self.channel = self.connection.channel()

        ch.basic_publish(
            exchange=self.exchange_name,
            routing_key=props.reply_to,
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=str(response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_consumer(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=SUB_QUEUE, on_message_callback=self.on_request)

        self.logger.info(" [MQ] Awaiting requests from queue: " + SUB_QUEUE)
        self.channel.start_consuming()


if __name__ == "__main__":
    thread_queue = Queue()
    rpc = RpcConsumer(thread_queue)

    t1 = threading.Thread(target=rpc.start_consumer, args=())
    t1.start()

    while True:
        if not thread_queue.empty():
            print("-----thread-----got message: " + str(thread_queue.get()))
            print("----------")
    # rpc.start_consumer()

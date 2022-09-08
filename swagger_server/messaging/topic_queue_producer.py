#!/usr/bin/env python
import pika
import uuid
import os
import time
import threading
import logging

MQ_HOST = os.environ.get("MQ_HOST")


class TopicQueueProducer(object):
    def __init__(self, timeout, exchange_name, routing_key):
        self.logger = logging.getLogger(__name__)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=MQ_HOST)
        )

        self.channel = self.connection.channel()
        self.timeout = timeout

        self.exchange_name = exchange_name
        self.routing_key = routing_key

        # An event to stop the thread we start.
        self.exit_event = threading.Event()

        t1 = threading.Thread(target=self.keep_live, args=())
        t1.start()

        # set up callback queue
        result = self.channel.queue_declare(queue="", exclusive=True)

        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )

    def keep_live(self):
        """Publish heart beat messages periodically on the MQ."""
        while True:
            if self.exit_event.wait(30):
                break
            msg = "[MQ]: Heart Beat"
            self.logger.debug("Sending heart beat msg.")
            self.call(msg)

    def stop_keep_alive(self):
        """Ask the keep-alive thread to stop."""
        self.exit_event.set()

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, body):
        # if not self.connection or self.connection.is_closed:
        #     # print("Reopening connection...")
        #     self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_HOST))
        #     self.channel = self.connection.channel()
        #     # print("Connection reopened.")
        #     # channel.exchange_declare(exchange=self.exchange_name)

        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.exchange_declare(
            exchange=self.exchange_name, exchange_type="topic"
        )

        self.channel.basic_publish(
            exchange=self.exchange_name, routing_key=self.routing_key, body=str(body)
        )

        return "Success"


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    producer = TopicQueueProducer(5, "connection", "lc1_q1")
    body = "test body"
    print("Published Message: {}".format(body))
    response = producer.call(body)
    print(" [.] Got response: " + str(response))

    # To test that keep-alive thread indeed keeps things alive, use a
    # longer sleep here.
    time.sleep(30*5)

    print("Stoping producer's keep-alive thread")
    producer.stop_keep_alive()

#!/usr/bin/env python
import pika
import os
import threading
from queue import Queue

MQ_HOST = os.environ.get('MQ_HOST')

class RpcConsumer(object):
    def __init__(self, thread_queue):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=MQ_HOST))

        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='rpc_queue')
        self._thread_queue = thread_queue

    def on_request(self,ch, method, props, message_body):
        response = message_body
        self._thread_queue.put(message_body)

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_HOST))
        self.channel = self.connection.channel()
        
        ch.basic_publish(exchange='',
                        routing_key=props.reply_to,
                        properties=pika.BasicProperties(correlation_id = \
                                                            props.correlation_id),
                        body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_consumer(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='rpc_queue', 
                                   on_message_callback=self.on_request)

        print(" [x] Awaiting RPC requests")
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
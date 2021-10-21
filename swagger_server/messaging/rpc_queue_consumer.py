#!/usr/bin/env python
import pika
import os

SDX_MQ_IP = 'aw-sdx-monitor.renci.org'

class RpcConsumer(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=SDX_MQ_IP))

        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='rpc_queue')

    def on_request(self,ch, method, props, message_body):
        response = message_body

        ch.basic_publish(exchange='',
                        routing_key=props.reply_to,
                        properties=pika.BasicProperties(correlation_id = \
                                                            props.correlation_id),
                        body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_consumer(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='rpc_queue', on_message_callback=self.on_request)

        print(" [x] Awaiting RPC requests")
        self.channel.start_consuming() 

if __name__ == "__main__":
    rpc = RpcConsumer()
    rpc.start_consumer()
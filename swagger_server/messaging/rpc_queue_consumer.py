#!/usr/bin/env python
import json
import logging
import os
import threading
from queue import Queue

import pika
from sdx_pce.topology.manager import TopologyManager

from swagger_server.handlers.lc_message_handler import LcMessageHandler
from swagger_server.utils.parse_helper import ParseHelper

MQ_HOST = os.environ.get("MQ_HOST")
# subscribe to the corresponding queue
SUB_QUEUE = os.environ.get("SUB_QUEUE")

logger = logging.getLogger(__name__)


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

    def start_sdx_consumer(self, thread_queue, db_instance):
        MESSAGE_ID = 0
        HEARTBEAT_ID = 0
        rpc = RpcConsumer(thread_queue, "")
        t1 = threading.Thread(target=rpc.start_consumer, args=())
        t1.start()

        manager = TopologyManager()
        lc_message_handler = LcMessageHandler(db_instance, manager)
        parse_helper = ParseHelper()

        latest_topo = {}
        domain_list = []
        num_domain_topos = 0

        # This part reads from DB when SDX controller initially starts.
        # It looks for domain_list, and num_domain_topos, if they are already in DB,
        # Then use the existing ones from DB.
        if db_instance.read_from_db("domain_list"):
            domain_list = db_instance.read_from_db("domain_list")["domain_list"]
            num_domain_topos = len(domain_list)

        if db_instance.read_from_db("latest_topo"):
            latest_topo = db_instance.read_from_db("latest_topo")["latest_topo"]

        if db_instance.read_from_db("num_domain_topos"):
            db_instance.add_key_value_pair_to_db("num_domain_topos", num_domain_topos)
            for topo in range(1, num_domain_topos + 2):
                db_key = f"LC-{topo}"
                topology = db_instance.read_from_db(db_key)

                if topology:
                    # Get the actual thing minus the Mongo ObjectID.
                    topology = topology[db_key]
                    topo_json = json.loads(topology)
                    manager.add_topology(topo_json)
                    logger.debug(f"Read {db_key}: {topology}")

        while True:
            # Queue.get() will block until there's an item in the queue.
            msg = thread_queue.get()
            logger.debug("MQ received message:" + str(msg))

            if "Heart Beat" in str(msg):
                HEARTBEAT_ID += 1
                logger.debug("Heart beat received. ID: " + str(HEARTBEAT_ID))
            else:
                logger.info("Saving to database.")
                if parse_helper.is_json(msg):
                    if "version" in str(msg):
                        lc_message_handler.process_lc_json_msg(
                            msg,
                            latest_topo,
                            domain_list,
                            num_domain_topos,
                        )
                    else:
                        logger.info("got message from MQ: " + str(msg))
                else:
                    db_instance.add_key_value_pair_to_db(str(MESSAGE_ID), msg)
                    logger.debug("Save to database complete.")
                    logger.debug("message ID:" + str(MESSAGE_ID))
                    value = db_instance.read_from_db(str(MESSAGE_ID))
                    logger.debug("got value from DB:")
                    logger.debug(value)
                    MESSAGE_ID += 1


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

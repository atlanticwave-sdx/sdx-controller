#!/usr/bin/env python
import json
import logging
import os
import threading
import time
from queue import Queue

import pika

from swagger_server.handlers.lc_message_handler import LcMessageHandler
from swagger_server.utils.parse_helper import ParseHelper

MQ_HOST = os.environ.get("MQ_HOST")
MQ_PORT = int(os.environ.get("MQ_PORT"))
# subscribe to the corresponding queue
SUB_QUEUE = os.environ.get("SUB_QUEUE")
MQ_USER = os.environ.get("MQ_USER")
MQ_PASS = os.environ.get("MQ_PASS")
logger = logging.getLogger(__name__)


class RpcConsumer(object):
    def __init__(self, thread_queue, exchange_name, topology_manager):

        self.logger = logging.getLogger(__name__)
        self.logger.info(" [*] Connecting to server ...")

        credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(MQ_HOST, MQ_PORT, "/", credentials)
        )

        self.channel = self.connection.channel()
        self.exchange_name = exchange_name

        self.channel.queue_declare(queue=SUB_QUEUE)
        self._thread_queue = thread_queue

        self.manager = topology_manager

    def on_request(self, ch, method, props, message_body):
        response = message_body
        self._thread_queue.put(message_body)

        self.logger.info(" [*] Connecting to server ...")

        credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(MQ_HOST, MQ_PORT, "/", credentials)
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
        rpc = RpcConsumer(thread_queue, "", self.manager)
        t1 = threading.Thread(target=rpc.start_consumer, args=())
        t1.start()

        lc_message_handler = LcMessageHandler(db_instance, self.manager)
        parse_helper = ParseHelper()

        latest_topo = {}
        domain_list = []
        num_domain_topos = 0
        # For testing
        # db_instance.add_key_value_pair_to_db("link_connections_dict", {})

        # This part reads from DB when SDX controller initially starts.
        # It looks for domain_list, and num_domain_topos, if they are already in DB,
        # Then use the existing ones from DB.
        domain_list_from_db = db_instance.read_from_db("domain_list")
        latest_topo_from_db = db_instance.read_from_db("latest_topo")
        num_domain_topos_from_db = db_instance.read_from_db("num_domain_topos")

        if domain_list_from_db:
            domain_list = domain_list_from_db["domain_list"]
            logger.debug("Read domain_list from db: ")
            logger.debug(domain_list)

        if latest_topo_from_db:
            latest_topo = latest_topo_from_db["latest_topo"]
            logger.debug("Read latest_topo from db: ")
            logger.debug(latest_topo)

        if num_domain_topos_from_db:
            num_domain_topos = num_domain_topos_from_db["num_domain_topos"]
            logger.debug("Read num_domain_topos from db: ")
            logger.debug(num_domain_topos)
            for topo in range(1, num_domain_topos + 2):
                db_key = f"LC-{topo}"
                topology = db_instance.read_from_db(db_key)

                if topology:
                    # Get the actual thing minus the Mongo ObjectID.
                    topology = topology[db_key]
                    topo_json = json.loads(topology)
                    self.manager.add_topology(topo_json)
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
                    logger.debug(
                        "Save to database complete. message ID: " + str(MESSAGE_ID)
                    )
                    MESSAGE_ID += 1

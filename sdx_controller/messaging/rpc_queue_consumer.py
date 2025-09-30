#!/usr/bin/env python
import json
import logging
import os
import threading
from queue import Queue

import pika
from sdx_datamodel.constants import Constants, MessageQueueNames, MongoCollections
from sdx_datamodel.models.topology import SDX_TOPOLOGY_ID_prefix

from sdx_controller.handlers.lc_message_handler import LcMessageHandler
from sdx_controller.utils.parse_helper import ParseHelper

MQ_HOST = os.getenv("MQ_HOST")
MQ_PORT = os.getenv("MQ_PORT") or 5672
MQ_USER = os.getenv("MQ_USER") or "guest"
MQ_PASS = os.getenv("MQ_PASS") or "guest"

# subscribe to the corresponding queue
SUB_QUEUE = MessageQueueNames.OXP_UPDATE

logger = logging.getLogger(__name__)


class RpcConsumer(object):
    def __init__(self, thread_queue, exchange_name, te_manager):
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"[MQ] Using amqp://{MQ_USER}@{MQ_HOST}:{MQ_PORT}")

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=MQ_HOST,
                port=MQ_PORT,
                credentials=pika.PlainCredentials(username=MQ_USER, password=MQ_PASS),
            )
        )

        self.channel = self.connection.channel()
        self.exchange_name = exchange_name

        self.channel.queue_declare(queue=SUB_QUEUE)
        self._thread_queue = thread_queue

        self.te_manager = te_manager

        self._exit_event = threading.Event()

    def on_request(self, ch, method, props, message_body):
        response = message_body
        self._thread_queue.put(message_body)

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=MQ_HOST,
                port=MQ_PORT,
                credentials=pika.PlainCredentials(username=MQ_USER, password=MQ_PASS),
            )
        )
        self.channel = self.connection.channel()

        try:
            ch.basic_publish(
                exchange=self.exchange_name,
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=str(response),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as err:
            self.logger.info(f"[MQ] encountered error when publishing: {err}")

    def start_consumer(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=SUB_QUEUE, on_message_callback=self.on_request)

        self.logger.info(" [MQ] Awaiting requests from queue: " + SUB_QUEUE)
        self.channel.start_consuming()

    def start_sdx_consumer(self, thread_queue, db_instance):
        HEARTBEAT_ID = 0

        rpc = RpcConsumer(thread_queue, "", self.te_manager)
        t1 = threading.Thread(target=rpc.start_consumer, args=(), daemon=True)
        t1.start()

        lc_message_handler = LcMessageHandler(db_instance, self.te_manager)
        parse_helper = ParseHelper()

        latest_topo = {}
        domain_list = []

        # This part reads from DB when SDX controller initially starts.
        # It looks for domain_list, if already in DB,
        # Then use the existing ones from DB.
        domain_list_from_db = db_instance.get_value_from_db(
            MongoCollections.DOMAINS, Constants.DOMAIN_LIST
        )
        latest_topo_from_db = db_instance.get_value_from_db(
            MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY
        )

        if domain_list_from_db:
            domain_list = domain_list_from_db
            logger.debug("Domain list already exists in db: ")
            logger.debug(domain_list)

        if latest_topo_from_db:
            latest_topo = latest_topo_from_db
            logger.debug("Topology already exists in db: ")
            logger.debug(latest_topo)

        # If topologies already saved in db, use them to initialize te_manager
        if domain_list:
            for domain in domain_list:
                topology = db_instance.get_value_from_db(
                    MongoCollections.TOPOLOGIES, SDX_TOPOLOGY_ID_prefix + domain
                )

                if not topology:
                    continue

                # Get the actual thing minus the Mongo ObjectID.
                self.te_manager.add_topology(topology)
                logger.debug(f"Read {domain}: {topology}")
                # update topology state
                connections = db_instance.get_all_entries_in_collection(
                    MongoCollections.CONNECTIONS
                )
                if not connections:
                    logger.info("No connection was found")
                else:
                    for connection in connections:
                        service_id = next(iter(connection))
                        logger.info(f"service_id: {service_id}")
                        request_dict = connection.get(service_id)
                        status = request_dict.get("status")
                        breakdown = db_instance.read_from_db(
                            MongoCollections.BREAKDOWNS, service_id
                        )
                        if not breakdown:
                            logger.warning(f"Could not find breakdown for {service_id}")

        while not self._exit_event.is_set():
            # Queue.get() will block until there's an item in the queue.
            msg = thread_queue.get()
            logger.debug("MQ received message:" + str(msg))

            if "Heart Beat" in str(msg):
                HEARTBEAT_ID += 1
                logger.debug("Heart beat received. ID: " + str(HEARTBEAT_ID))
                continue

            if not parse_helper.is_json(msg):
                continue

            if "version" not in str(msg):
                logger.info("Got message (NO VERSION) from MQ: " + str(msg))

            lc_message_handler.process_lc_json_msg(
                msg,
                latest_topo,
                domain_list,
            )

    def stop_threads(self):
        """
        Signal threads that we're ready to stop.
        """
        logger.info("[MQ] Stopping threads.")
        self.channel.stop_consuming()
        self._exit_event.set()

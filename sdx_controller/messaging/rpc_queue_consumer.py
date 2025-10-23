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
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", 10))  # seconds
HEARTBEAT_TOLERANCE = int(
    os.getenv("HEARTBEAT_TOLERANCE", 10)
)  # consecutive missed heartbeats allowed


# subscribe to the corresponding queue
SUB_QUEUE = MessageQueueNames.OXP_UPDATE

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    def __init__(self):
        self.last_heartbeat = {}  # domain -> last heartbeat timestamp
        self.domain_status = {}  # domain -> "up" or "down"
        self.lock = threading.Lock()
        self.monitoring = False

    def record_heartbeat(self, domain):
        """Record heartbeat from a domain and mark it as up."""
        with self.lock:
            self.last_heartbeat[domain] = time.time()
            self.domain_status[domain] = "up"
            logger.debug(f"[HeartbeatMonitor] Heartbeat recorded for {domain}")

    def check_status(self):
        """Mark domains as down if heartbeats are missing."""
        now = time.time()
        with self.lock:
            for domain, last_time in self.last_heartbeat.items():
                if now - last_time > HEARTBEAT_TOLERANCE * HEARTBEAT_INTERVAL:
                    if self.domain_status.get(domain) != "down":
                        logger.warning(
                            f"[HeartbeatMonitor] Domain {domain} marked DOWN (missed {HEARTBEAT_TOLERANCE} heartbeats)"
                        )
                    self.domain_status[domain] = "down"

    def get_status(self, domain):
        """Return the current status of a domain."""
        with self.lock:
            return self.domain_status.get(domain, "unknown")

    def start_monitoring(self):
        """Start a background thread to monitor heartbeat status."""
        if self.monitoring:
            return
        self.monitoring = True
        logger.info("[HeartbeatMonitor] Started monitoring heartbeats.")

        def monitor_loop():
            while self.monitoring:
                self.check_status()
                time.sleep(HEARTBEAT_INTERVAL)

        t = threading.Thread(target=monitor_loop, daemon=True)
        t.start()


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
        rpc = RpcConsumer(thread_queue, "", self.te_manager)
        t1 = threading.Thread(target=rpc.start_consumer, args=(), daemon=True)
        t1.start()

        lc_message_handler = LcMessageHandler(db_instance, self.te_manager)
        parse_helper = ParseHelper()

        heartbeat_monitor = HeartbeatMonitor()
        heartbeat_monitor.start_monitoring()

        latest_topo = {}
        domain_dict = {}

        # This part reads from DB when SDX controller initially starts.
        # It looks for domain_dict, if already in DB,
        # Then use the existing ones from DB.
        domain_dict_from_db = db_instance.get_value_from_db(
            MongoCollections.DOMAINS, Constants.DOMAIN_DICT
        )
        latest_topo_from_db = db_instance.get_value_from_db(
            MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY
        )

        if domain_dict_from_db:
            domain_dict = domain_dict_from_db
            logger.debug("Domain list already exists in db: ")
            logger.debug(domain_dict)

        if latest_topo_from_db:
            latest_topo = latest_topo_from_db
            logger.debug("Topology already exists in db: ")
            logger.debug(latest_topo)

        # If topologies already saved in db, use them to initialize te_manager
        if domain_dict:
            for domain in domain_dict.keys():
                topology = db_instance.get_value_from_db(
                    MongoCollections.TOPOLOGIES, SDX_TOPOLOGY_ID_prefix + domain
                )

                if not topology:
                    continue

                # Get the actual thing minus the Mongo ObjectID.
                self.te_manager.add_topology(topology)
                logger.debug(f"Read {domain}: {topology}")

        while not self._exit_event.is_set():
            msg = thread_queue.get()
            logger.debug("MQ received message:" + str(msg))

            if "Heart Beat" in str(msg):
                domain = (
                    parse_helper.extract_domain_from_msg(msg)
                    if hasattr(parse_helper, "extract_domain_from_msg")
                    else "unknown"
                )
                heartbeat_monitor.record_heartbeat(domain)
                logger.debug(f"Heart beat received from {domain}")
                continue

            if not parse_helper.is_json(msg):
                continue

            lc_message_handler.process_lc_json_msg(
                msg,
                latest_topo,
                domain_dict,
            )

    def stop_threads(self):
        """
        Signal threads that we're ready to stop.
        """
        logger.info("[MQ] Stopping threads.")
        self.channel.stop_consuming()
        self._exit_event.set()

#!/usr/bin/env python
import json
import logging
import os
import threading
import time
import traceback
from queue import Queue

import pika
from sdx_datamodel.constants import (
    Constants,
    DomainStatus,
    MessageQueueNames,
    MongoCollections,
)
from sdx_datamodel.models.topology import SDX_TOPOLOGY_ID_prefix
from sdx_pce.models import ConnectionPath, ConnectionRequest, ConnectionSolution
from sdx_pce.topology.manager import TopologyManager

from sdx_controller.handlers.connection_handler import (
    ConnectionHandler,
    connection_state_machine,
    get_connection_status,
    parse_conn_status,
)
from sdx_controller.handlers.lc_message_handler import LcMessageHandler
from sdx_controller.models import connection
from sdx_controller.utils.parse_helper import ParseHelper

MQ_HOST = os.getenv("MQ_HOST")
MQ_PORT = os.getenv("MQ_PORT") or 5672
MQ_USER = os.getenv("MQ_USER") or "guest"
MQ_PASS = os.getenv("MQ_PASS") or "guest"
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", 10))  # seconds
HEARTBEAT_TOLERANCE = int(
    os.getenv("HEARTBEAT_TOLERANCE", 3)
)  # consecutive missed heartbeats allowed


# subscribe to the corresponding queue
SUB_QUEUE = MessageQueueNames.OXP_UPDATE

logger = logging.getLogger(__name__)

MongoCollections.SOLUTIONS = "solutions"


class HeartbeatMonitor:
    def __init__(self, db_instance):
        self.last_heartbeat = {}  # domain -> last heartbeat timestamp
        self.domain_status = {}  # domain -> current status (UP / UNKNOWN)
        self.lock = threading.Lock()
        self.monitoring = False
        self.db_instance = db_instance  # store DB instance

    def record_heartbeat(self, domain):
        """Record heartbeat from a domain and mark it as UP if previously UNKNOWN."""
        with self.lock:
            self.last_heartbeat[domain] = time.time()

            previous_status = self.domain_status.get(domain)
            self.domain_status[domain] = DomainStatus.UP

            # Update DB if status changed from UNKNOWN -> UP
            if previous_status == DomainStatus.UNKNOWN:
                logger.info(
                    f"[HeartbeatMonitor] Domain {domain} is BACK UP after missed heartbeats."
                )
                domain_dict_from_db = self.db_instance.get_value_from_db(
                    MongoCollections.DOMAINS, Constants.DOMAIN_DICT
                )
                if domain in domain_dict_from_db:
                    domain_dict_from_db[domain] = DomainStatus.UP
                    self.db_instance.add_key_value_pair_to_db(
                        MongoCollections.DOMAINS,
                        Constants.DOMAIN_DICT,
                        domain_dict_from_db,
                    )

            logger.debug(f"[HeartbeatMonitor] Heartbeat recorded for {domain}")

    def check_status(self):
        """Mark domains as UNKNOWN if heartbeats are missing."""
        now = time.time()
        with self.lock:
            for domain, last_time in self.last_heartbeat.items():
                if now - last_time > HEARTBEAT_TOLERANCE * HEARTBEAT_INTERVAL:
                    if self.domain_status.get(domain) != DomainStatus.UNKNOWN:
                        logger.warning(
                            f"[HeartbeatMonitor] Domain {domain} marked UNKNOWN (missed {HEARTBEAT_TOLERANCE} heartbeats)"
                        )
                        self.domain_status[domain] = DomainStatus.UNKNOWN

                        domain_dict_from_db = self.db_instance.get_value_from_db(
                            MongoCollections.DOMAINS, Constants.DOMAIN_DICT
                        )
                        if domain in domain_dict_from_db:
                            domain_dict_from_db[domain] = DomainStatus.UNKNOWN
                            self.db_instance.add_key_value_pair_to_db(
                                MongoCollections.DOMAINS,
                                Constants.DOMAIN_DICT,
                                domain_dict_from_db,
                            )

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

        heartbeat_monitor = HeartbeatMonitor(db_instance)
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

        residul_bw = {}
        if latest_topo_from_db:
            latest_topo = latest_topo_from_db
            logger.debug("Topology already exists in db: ")
            # logger.debug(latest_topo)
            update_topology_manager = TopologyManager()
            update_topology_manager.add_topology(latest_topo)
            residul_bw = update_topology_manager.get_residul_bandwidth()
            logger.debug(residul_bw)

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
            # update topology/pce state in TE Manager

            graph = self.te_manager.generate_graph_te()
            logger.debug(f"restart graph = {graph.nodes};{graph.edges}")
            connections = db_instance.get_all_entries_in_collection(
                MongoCollections.CONNECTIONS
            )
            if not connections:
                logger.info("No connection was found")
            else:
                for connection in connections:
                    service_id = next(iter(connection))
                    status = get_connection_status(db_instance, service_id)
                    logger.info(
                        f"Restart: service_id: {service_id}, status: {status.get(service_id)}"
                    )
                    # 1. update the vlan tables in pce
                    domain_breakdown = db_instance.get_value_from_db(
                        MongoCollections.BREAKDOWNS, service_id
                    )
                    if not domain_breakdown:
                        logger.warning(f"Could not find breakdown for {service_id}")
                        continue
                    try:
                        vlan_tags_table = self.te_manager.vlan_tags_table
                        for domain, segment in domain_breakdown.items():
                            logger.debug(f"domain:{domain};segment:{segment}")
                            domain_table = vlan_tags_table.get(domain)
                            uni_a = segment.get("uni_a")
                            vlan_table = domain_table.get(uni_a.get("port_id"))
                            vlan_table[uni_a.get("tag").get("value")] = service_id
                            uni_z = segment.get("uni_z")
                            vlan_table = domain_table.get(uni_z.get("port_id"))
                            vlan_table[uni_z.get("tag").get("value")] = service_id
                    except Exception as e:
                        err = traceback.format_exc().replace("\n", ", ")
                        logger.error(
                            f"Error when recovering breakdown vlan assignment: {e} - {err}"
                        )
                        return f"Error: {e}", 410
            logger.debug(f"Restart: solutions for {connections}")
            connectionSolution_list = self.te_manager.connectionSolution_list
            connections = db_instance.get_all_entries_in_collection(
                MongoCollections.CONNECTIONS
            )
            if not connections:
                logger.info("No connection was found")
            else:
                for connection in connections:
                    try:
                        service_id = next(iter(connection))
                        response = get_connection_status(db_instance, service_id)
                        if not response:
                            continue
                        qos_metrics = response[service_id].get("qos_metrics")
                        if not qos_metrics:
                            continue
                        min_bw = qos_metrics.get("min_bw", {"value": 0.0}).get(
                            "value", 0
                        )
                        logger.debug(f"service_id:{service_id}, {response}")
                        solution_links = db_instance.get_value_from_db(
                            MongoCollections.SOLUTIONS, service_id
                        )
                        logger.debug(
                            f"service_id:{service_id};solution:{solution_links}"
                        )
                        if not solution_links:
                            logger.warning(
                                f"Could not find solution in DB for {service_id}"
                            )
                            continue
                        links = []
                        for link in solution_links:
                            source_node = self.te_manager.topology_manager.get_topology().get_node_by_port(
                                link.get("source")
                            )
                            destination_node = self.te_manager.topology_manager.get_topology().get_node_by_port(
                                link.get("destination")
                            )
                            source = [
                                x
                                for x, y in graph.nodes(data=True)
                                if y["id"] == source_node.id
                            ]

                            destination = [
                                x
                                for x, y in graph.nodes(data=True)
                                if y["id"] == destination_node.id
                            ]
                            links.append(
                                {"source": source[0], "destination": destination[0]}
                            )
                        # rebuild solution object
                        request = ConnectionRequest(
                            source=0,
                            destination=0,
                            required_bandwidth=min_bw,
                            required_latency=float("inf"),
                        )
                        link_map = [
                            ConnectionPath(link.get("source"), link.get("destination"))
                            for link in links
                        ]
                        solution = ConnectionSolution(
                            connection_map={request: link_map},
                            cost=0,
                            request_id=service_id,
                        )
                        connectionSolution_list.append(solution)
                    except Exception as e:
                        err = traceback.format_exc().replace("\n", ", ")
                        logger.error(
                            f"Error when recovering solution list: {e} - {err}"
                        )
                        return f"Error: {e}", 410
            logger.debug(f"Restart: residul_bw")
            if residul_bw:
                self.te_manager.update_available_bw_in_topology(residul_bw)

        while not self._exit_event.is_set():
            msg = thread_queue.get()
            logger.debug("MQ received message:" + str(msg))

            if not parse_helper.is_json(msg):
                logger.debug("Non JSON message, ignored")
                continue

            msg_json = json.loads(msg)
            if "type" in msg_json and msg_json.get("type") == "Heart Beat":
                domain = msg_json.get("domain")
                heartbeat_monitor.record_heartbeat(domain)
                logger.debug(f"Heart beat received from {domain}")
                continue

            try:
                lc_message_handler.process_lc_json_msg(
                    msg,
                    latest_topo,
                    domain_dict,
                )
            except Exception as exc:
                err = traceback.format_exc().replace("\n", ", ")
                logger.error(f"Failed to process LC message: {exc} -- {err}")

    def stop_threads(self):
        """
        Signal threads that we're ready to stop.
        """
        logger.info("[MQ] Stopping threads.")
        self.channel.stop_consuming()
        self._exit_event.set()

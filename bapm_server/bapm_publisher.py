# Asynchronous MQ publisher, from pika, for testing purposes

import functools
import json
import logging

import pika
from pika.exchange_type import ExchangeType

LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
LOGGER = logging.getLogger(__name__)


class BAPMPublisher(object):
    """
    BAPM publisher.
    """

    EXCHANGE = "measurement"
    EXCHANGE_TYPE = ExchangeType.topic
    PUBLISH_INTERVAL = 1
    QUEUE = "sdx_q_measurement"
    ROUTING_KEY = "measurement.bapm"

    def __init__(self, amqp_url):
        self._connection = None
        self._channel = None

        self._deliveries = None
        self._acked = None
        self._nacked = None
        self._message_number = None

        self._stopping = False
        self._url = amqp_url

    def connect(self):
        LOGGER.info("Connecting to %s", self._url)
        return pika.SelectConnection(
            pika.URLParameters(self._url),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed,
        )

    def on_connection_open(self, _unused_connection):
        LOGGER.info("Connection opened")
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        LOGGER.error("Connection open failed, reopening in 5 seconds: %s", err)
        self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning("Connection closed, reopening in 5 seconds: %s", reason)
            self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def open_channel(self):
        LOGGER.info("Creating a new channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        LOGGER.info("Channel opened")
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        LOGGER.info("Adding channel close callback")
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        LOGGER.warning("Channel %i was closed: %s", channel, reason)
        self._channel = None
        if not self._stopping:
            self._connection.close()

    def setup_exchange(self, exchange_name):
        LOGGER.info("Declaring exchange %s", exchange_name)
        # Note: using functools.partial is not required, it is demonstrating
        # how arbitrary data can be passed to the callback when it is called
        cb = functools.partial(self.on_exchange_declareok, userdata=exchange_name)
        self._channel.exchange_declare(
            exchange=exchange_name, exchange_type=self.EXCHANGE_TYPE, callback=cb
        )

    def on_exchange_declareok(self, _unused_frame, userdata):
        LOGGER.info("Exchange declared: %s", userdata)
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        LOGGER.info("Declaring queue %s", queue_name)
        self._channel.queue_declare(queue=queue_name, callback=self.on_queue_declareok)

    def on_queue_declareok(self, _unused_frame):
        LOGGER.info(
            "Binding %s to %s with %s", self.EXCHANGE, self.QUEUE, self.ROUTING_KEY
        )
        self._channel.queue_bind(
            self.QUEUE,
            self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
            callback=self.on_bindok,
        )

    def on_bindok(self, _unused_frame):
        LOGGER.info("Queue bound")
        self.start_publishing()

    def start_publishing(self):
        LOGGER.info("Issuing consumer related RPC commands")
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        LOGGER.info("Issuing Confirm.Select RPC command")
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split(".")[1].lower()
        LOGGER.info(
            "Received %s for delivery tag: %i",
            confirmation_type,
            method_frame.method.delivery_tag,
        )
        if confirmation_type == "ack":
            self._acked += 1
        elif confirmation_type == "nack":
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        LOGGER.info(
            "Published %i messages, %i have yet to be confirmed, "
            "%i were acked and %i were nacked",
            self._message_number,
            len(self._deliveries),
            self._acked,
            self._nacked,
        )

    def schedule_next_message(self):
        LOGGER.info("Scheduling next message for %0.1f seconds", self.PUBLISH_INTERVAL)
        self._connection.ioloop.call_later(self.PUBLISH_INTERVAL, self.publish_message)

    def publish_message(self):
        if self._channel is None or not self._channel.is_open:
            return

        hdrs = {"test": "header"}
        properties = pika.BasicProperties(
            app_id="example-publisher", content_type="application/json", headers=hdrs
        )

        message = {"test msg": "test"}
        self._channel.basic_publish(
            self.EXCHANGE,
            self.ROUTING_KEY,
            json.dumps(message, ensure_ascii=False),
            properties,
        )
        self._message_number += 1
        self._deliveries.append(self._message_number)
        LOGGER.info("Published message # %i", self._message_number)
        self.schedule_next_message()

    def run(self):
        """Run the example code by connecting and then starting the IOLoop."""
        self._connection = None
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0

        try:
            self._connection = self.connect()
            self._connection.ioloop.start()
        except KeyboardInterrupt:
            self.stop()
            if self._connection is not None and not self._connection.is_closed:
                # Finish closing
                self._connection.ioloop.start()

        # while not self._stopping:
        #     self._connection = None
        #     self._deliveries = []
        #     self._acked = 0
        #     self._nacked = 0
        #     self._message_number = 0

        #     try:
        #         self._connection = self.connect()
        #         self._connection.ioloop.start()
        #     except KeyboardInterrupt:
        #         self.stop()
        #         if self._connection is not None and not self._connection.is_closed:
        #             # Finish closing
        #             self._connection.ioloop.start()

        LOGGER.info("Stopped")

    def stop(self):
        """Stop the example by closing the channel and connection. We
        set a flag here so that we stop scheduling new messages to be
        published. The IOLoop is started because this method is
        invoked by the Try/Catch below when KeyboardInterrupt is caught.
        Starting the IOLoop again will allow the publisher to cleanly
        disconnect from RabbitMQ.

        """
        LOGGER.info("Stopping")
        self._stopping = True
        self.close_channel()
        self.close_connection()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending
        the Channel.Close RPC command.

        """
        if self._channel is not None:
            LOGGER.info("Closing the channel")
            self._channel.close()

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        if self._connection is not None:
            LOGGER.info("Closing connection")
            self._connection.close()


def main():
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

    # Connect to localhost:5672 as guest with the password guest and virtual host "/" (%2F)
    publisher = BAPMPublisher("amqp://guest:guest@aw-sdx-monitor.renci.org:5672/%2F")
    publisher.run()


if __name__ == "__main__":
    main()

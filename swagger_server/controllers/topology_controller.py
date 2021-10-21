import connexion
import six
import os
from queue import Queue

from swagger_server.models.topology import Topology  # noqa: E501
from swagger_server import util
from swagger_server.utils.db_utils import *
from swagger_server.messaging.async_consumer import *
from swagger_server.messaging.rpc_queue_consumer import *

DB_NAME = os.environ.get('DB_NAME')
MANIFEST = os.environ.get('MANIFEST')
MESSAGE_ID = 0

# Get DB connection and tables set up.
db_tuples = [('config_table', "test-config")]

db_instance = DbUtils()
db_instance._initialize_db(DB_NAME, db_tuples)

amqp_url = 'amqp://guest:guest@aw-sdx-monitor.renci.org:5672/%2F'

thread_queue = Queue()

def start_consumer(amqp_url, thread_queue, db_instance):
    consumer = AsyncConsumer(amqp_url, thread_queue)
    t1 = threading.Thread(target=consumer.run, args=())
    t1.start()

    while True:
        if not thread_queue.empty():
            msg = thread_queue.get()
            print("MQ received message:" + str(msg))

            print('Saving to database.')
            db_instance.add_key_value_pair_to_db(MESSAGE_ID, msg)
            print('Saving to database complete.')

            print('message ID:' + str(MESSAGE_ID))
            value = db_instance.read_from_db(MESSAGE_ID)
            print('get value back:')
            print(value)


            

# logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

def get_topology():  # noqa: E501
    """get an existing topology

    ID of the topology # noqa: E501


    :rtype: str
    """
    return 'do some magic!'


def get_topologyby_version(topology_id, version):  # noqa: E501
    """Find topology by version

    Returns a single topology # noqa: E501

    :param topology_id: ID of topology to return
    :type topology_id: int
    :param version: version of topology to return
    :type version: int

    :rtype: Topology
    """
    return 'do some magic!'


def topology_version(topology_id):  # noqa: E501
    """Finds topology version

    Topology version # noqa: E501

    :param topology_id: topology id
    :type topology_id: str

    :rtype: Topology
    """
    return 'do some magic!'

start_consumer(amqp_url, thread_queue, db_instance)
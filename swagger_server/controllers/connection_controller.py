import connexion
import six
import os
import json

from swagger_server.models.connection import Connection  # noqa: E501
from swagger_server import util
from swagger_server.utils.db_utils import *
from swagger_server.messaging.topic_queue_producer import *

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)

DB_NAME = os.environ.get('DB_NAME')
MANIFEST = os.environ.get('MANIFEST')

# Get DB connection and tables set up.
db_tuples = [('config_table', "test-config")]

db_instance = DbUtils()
db_instance._initialize_db(DB_NAME, db_tuples)

producer = TopicQueueProducer(5, "connection", "lc1_q1")

class Payload(object):
    def __init__(self, j):
        self.__dict__ = json.loads(j)

def delete_connection(connection_id):  # noqa: E501
    """Delete connection order by ID

    delete a connection # noqa: E501

    :param connection_id: ID of the connection that needs to be deleted
    :type connection_id: int

    :rtype: None
    """
    return 'do some magic!'


def getconnection_by_id(connection_id):  # noqa: E501
    """Find connection by ID

    connection details # noqa: E501

    :param connection_id: ID of connection that needs to be fetched
    :type connection_id: int

    :rtype: Connection
    """
    value = db_instance.read_from_db('test')
    print('get value back:')
    print(value)
    return value


def place_connection(body):  # noqa: E501
    """Place an connection request from the SDX-Controller

     # noqa: E501

    :param body: order placed for creating a connection
    :type body: dict | bytes

    :rtype: Connection
    """
    print(body)
    if connexion.request.is_json:
        body = connexion.request.get_json()
        # body = Connection.from_dict(connexion.request.get_json())  # noqa: E501

    json_body = json.dumps(body)

    logger.debug('Placing connection. Saving to database.')
    db_instance.add_key_value_pair_to_db('test', json_body)
    logger.debug('Saving to database complete.')

    logger.debug("Publishing Message to MQ: {}".format(body))
    response = producer.call(json_body)
    logger.debug(" [.] Got response: " + str(response))

    return str(response)

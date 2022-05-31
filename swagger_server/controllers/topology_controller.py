import connexion
import six
import os
from queue import Queue

from swagger_server.utils.db_utils import *
from swagger_server.models.topology import Topology  # noqa: E501
from swagger_server import util

DB_NAME = os.environ.get('DB_NAME') + '.sqlite3'
# Get DB connection and tables set up.
db_tuples = [('config_table', "test-config")]
db_instance = DbUtils()
db_instance._initialize_db(DB_NAME, db_tuples)

def get_topology():  # noqa: E501
    """get an existing topology

    ID of the topology # noqa: E501


    :rtype: str
    """
    topo_val = db_instance.read_from_db('latest_topo')
    return topo_val


def get_topologyby_grenml():  # noqa: E501
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


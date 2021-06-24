import connexion
import six

from swagger_server.models.topology import Topology  # noqa: E501
from swagger_server import util

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

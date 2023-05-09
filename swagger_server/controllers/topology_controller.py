import json
import os
from queue import Queue

import connexion
import six
from sdx.datamodel.topologymanager.grenmlconverter import GrenmlConverter
from sdx.datamodel.topologymanager.manager import TopologyManager

from swagger_server import util
from swagger_server.models.topology import Topology  # noqa: E501
from swagger_server.utils.db_utils import *

# Get DB connection and tables set up.
db_instance = DbUtils()
db_instance.initialize_db()
manager = TopologyManager()


def get_topology():  # noqa: E501
    """get an existing topology

    ID of the topology # noqa: E501


    :rtype: str
    """
    topo_val = db_instance.read_from_db("latest_topo")["latest_topo"]
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

    num_domain_topos = 0

    if db_instance.read_from_db("num_domain_topos") is not None:
        num_domain_topos = db_instance.read_from_db("num_domain_topos")

    for i in range(1, int(num_domain_topos) + 1):
        curr_topo_str = db_instance.read_from_db("LC-" + str(i))
        curr_topo_json = json.loads(curr_topo_str)
        manager.add_topology(curr_topo_json)

    converter = GrenmlConverter(manager.get_topology())
    converter.read_topology()
    return converter.get_xml_str()


def topology_version(topology_id):  # noqa: E501
    """Finds topology version

    Topology version # noqa: E501

    :param topology_id: topology id
    :type topology_id: str

    :rtype: Topology
    """
    return "do some magic!"

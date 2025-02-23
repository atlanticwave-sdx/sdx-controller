from flask import current_app
from sdx_datamodel.constants import Constants, MongoCollections
from sdx_pce.topology.grenmlconverter import GrenmlConverter

from sdx_controller.utils.db_utils import DbUtils

# Get DB connection and tables set up.
db_instance = DbUtils()
db_instance.initialize_db()


def get_topology():  # noqa: E501
    """get an existing topology

    ID of the topology # noqa: E501


    :rtype: str
    """
    topo_val = db_instance.read_from_db(
        MongoCollections.TOPOLOGIES, Constants.LATEST_TOPOLOGY
    )

    # TODO: this is a workaround because of the way we read values
    # from MongoDB; refactor and test this more.
    if not topo_val:
        return None

    return topo_val[Constants.LATEST_TOPOLOGY]


def get_topologyby_grenml():  # noqa: E501
    """Find topology by version

    Returns a single topology # noqa: E501

    :param topology_id: ID of topology to return
    :type topology_id: int
    :param version: version of topology to return
    :type version: int

    :rtype: Topology
    """
    topology = current_app.te_manager.get_topology()
    converter = GrenmlConverter(topology)
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


def get_topology_domains():
    domain_list = db_instance.read_from_db(
        MongoCollections.DOMAINS, Constants.DOMAIN_LIST
    )
    if not domain_list:
        return []

    return domain_list[Constants.DOMAIN_LIST]

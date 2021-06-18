import connexion
import six

from swagger_server.models.connection import Connection  # noqa: E501
from swagger_server import util


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
    return 'do some magic!'


def place_connection(body):  # noqa: E501
    """Place an connection request from the SDX-Controller

     # noqa: E501

    :param body: order placed for creating a connection
    :type body: dict | bytes

    :rtype: Connection
    """
    if connexion.request.is_json:
        body = Connection.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'

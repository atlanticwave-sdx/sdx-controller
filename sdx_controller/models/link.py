# coding: utf-8

from __future__ import absolute_import

from datetime import date, datetime  # noqa: F401
from typing import Dict, List  # noqa: F401

from sdx_controller import util
from sdx_controller.models.base_model_ import Model
from sdx_controller.models.port import Port  # noqa: F401,E501


class Link(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(
        self,
        id: str = None,
        name: str = None,
        short_name: str = None,
        ports: List[Port] = None,
        bandwidth: float = None,
        residual_bandwidth: float = None,
        latency: float = None,
        packet_loss: float = None,
        availability: float = None,
        state: str = None,
        status: str = None,
    ):  # noqa: E501
        """Link - a model defined in Swagger

        :param id: The id of this Link.  # noqa: E501
        :type id: str
        :param name: The name of this Link.  # noqa: E501
        :type name: str
        :param short_name: The short_name of this Link.  # noqa: E501
        :type short_name: str
        :param ports: The ports of this Link.  # noqa: E501
        :type ports: List[Port]
        :param bandwidth: The bandwidth of this Link.  # noqa: E501
        :type bandwidth: float
        :param residual_bandwidth: The residual_bandwidth of this Link.  # noqa: E501
        :type residual_bandwidth: float
        :param latency: The latency of this Link.  # noqa: E501
        :type latency: float
        :param packet_loss: The packet_loss of this Link.  # noqa: E501
        :type packet_loss: float
        :param availability: The availability of this Link.  # noqa: E501
        :type availability: float
        :param state: The state of this Link.  # noqa: E501
        :type state: str
        :param status: The status of this Link.  # noqa: E501
        :type status: str
        """
        self.swagger_types = {
            "id": str,
            "name": str,
            "short_name": str,
            "ports": List[Port],
            "bandwidth": float,
            "residual_bandwidth": float,
            "latency": float,
            "packet_loss": float,
            "availability": float,
            "state": str,
            "status": str,
        }

        self.attribute_map = {
            "id": "id",
            "name": "name",
            "short_name": "short_name",
            "ports": "ports",
            "bandwidth": "bandwidth",
            "residual_bandwidth": "residual_bandwidth",
            "latency": "latency",
            "packet_loss": "packet_loss",
            "availability": "availability",
            "state": "state",
            "status": "status",
        }
        self._id = id
        self._name = name
        self._short_name = short_name
        self._ports = ports
        self._bandwidth = bandwidth
        self._residual_bandwidth = residual_bandwidth
        self._latency = latency
        self._packet_loss = packet_loss
        self._availability = availability
        self._state = state
        self._status = status

    @classmethod
    def from_dict(cls, dikt) -> "Link":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The link of this Link.  # noqa: E501
        :rtype: Link
        """
        return util.deserialize_model(dikt, cls)

    @property
    def id(self) -> str:
        """Gets the id of this Link.


        :return: The id of this Link.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id: str):
        """Sets the id of this Link.


        :param id: The id of this Link.
        :type id: str
        """
        if id is None:
            raise ValueError("Invalid value for `id`, must not be `None`")  # noqa: E501

        self._id = id

    @property
    def name(self) -> str:
        """Gets the name of this Link.


        :return: The name of this Link.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """Sets the name of this Link.


        :param name: The name of this Link.
        :type name: str
        """
        if name is None:
            raise ValueError(
                "Invalid value for `name`, must not be `None`"
            )  # noqa: E501

        self._name = name

    @property
    def short_name(self) -> str:
        """Gets the short_name of this Link.


        :return: The short_name of this Link.
        :rtype: str
        """
        return self._short_name

    @short_name.setter
    def short_name(self, short_name: str):
        """Sets the short_name of this Link.


        :param short_name: The short_name of this Link.
        :type short_name: str
        """

        self._short_name = short_name

    @property
    def ports(self) -> List[Port]:
        """Gets the ports of this Link.


        :return: The ports of this Link.
        :rtype: List[Port]
        """
        return self._ports

    @ports.setter
    def ports(self, ports: List[Port]):
        """Sets the ports of this Link.


        :param ports: The ports of this Link.
        :type ports: List[Port]
        """
        if ports is None:
            raise ValueError(
                "Invalid value for `ports`, must not be `None`"
            )  # noqa: E501

        self._ports = ports

    @property
    def bandwidth(self) -> float:
        """Gets the bandwidth of this Link.


        :return: The bandwidth of this Link.
        :rtype: float
        """
        return self._bandwidth

    @bandwidth.setter
    def bandwidth(self, bandwidth: float):
        """Sets the bandwidth of this Link.


        :param bandwidth: The bandwidth of this Link.
        :type bandwidth: float
        """

        self._bandwidth = bandwidth

    @property
    def residual_bandwidth(self) -> float:
        """Gets the residual_bandwidth of this Link.


        :return: The residual_bandwidth of this Link.
        :rtype: float
        """
        return self._residual_bandwidth

    @residual_bandwidth.setter
    def residual_bandwidth(self, residual_bandwidth: float):
        """Sets the residual_bandwidth of this Link.


        :param residual_bandwidth: The residual_bandwidth of this Link.
        :type residual_bandwidth: float
        """

        self._residual_bandwidth = residual_bandwidth

    @property
    def latency(self) -> float:
        """Gets the latency of this Link.


        :return: The latency of this Link.
        :rtype: float
        """
        return self._latency

    @latency.setter
    def latency(self, latency: float):
        """Sets the latency of this Link.


        :param latency: The latency of this Link.
        :type latency: float
        """

        self._latency = latency

    @property
    def packet_loss(self) -> float:
        """Gets the packet_loss of this Link.


        :return: The packet_loss of this Link.
        :rtype: float
        """
        return self._packet_loss

    @packet_loss.setter
    def packet_loss(self, packet_loss: float):
        """Sets the packet_loss of this Link.


        :param packet_loss: The packet_loss of this Link.
        :type packet_loss: float
        """

        self._packet_loss = packet_loss

    @property
    def availability(self) -> float:
        """Gets the availability of this Link.


        :return: The availability of this Link.
        :rtype: float
        """
        return self._availability

    @availability.setter
    def availability(self, availability: float):
        """Sets the availability of this Link.


        :param availability: The availability of this Link.
        :type availability: float
        """

        self._availability = availability

    @property
    def state(self) -> str:
        """Gets the state of this Link.


        :return: The state of this Link.
        :rtype: str
        """
        return self._state

    @state.setter
    def state(self, state: str):
        """Sets the state of this Link.


        :param state: The state of this Link.
        :type state: str
        """

        self._state = state

    @property
    def status(self) -> str:
        """Gets the status of this Link.


        :return: The status of this Link.
        :rtype: str
        """
        return self._status

    @status.setter
    def status(self, status: str):
        """Sets the status of this Link.


        :param status: The status of this Link.
        :type status: str
        """

        self._status = status

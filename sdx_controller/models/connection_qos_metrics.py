# coding: utf-8

from __future__ import absolute_import

from datetime import date, datetime  # noqa: F401
from typing import Dict, List  # noqa: F401

from sdx_controller import util
from sdx_controller.models.base_model_ import Model
from sdx_controller.models.connection_qos_unit import (  # noqa: F401,E501
    ConnectionQosUnit,
)


class ConnectionQosMetrics(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(
        self,
        min_bw: ConnectionQosUnit = None,
        max_delay: ConnectionQosUnit = None,
        max_number_oxps: ConnectionQosUnit = None,
        bandwidth_measured: float = None,
        latency_measured: float = None,
        packetloss_required: float = None,
        packetloss_measured: float = None,
        availability_required: float = None,
        availability_measured: float = None,
    ):  # noqa: E501
        """ConnectionQosMetrics - a model defined in Swagger

        :param min_bw: The min_bw of this ConnectionQosMetrics.  # noqa: E501
        :type min_bw: ConnectionQosUnit
        :param max_delay: The max_delay of this ConnectionQosMetrics.  # noqa: E501
        :type max_delay: ConnectionQosUnit
        :param max_number_oxps: The max_number_oxps of this ConnectionQosMetrics.  # noqa: E501
        :type max_number_oxps: ConnectionQosUnit
        :param bandwidth_measured: The bandwidth_measured of this ConnectionQosMetrics.  # noqa: E501
        :type bandwidth_measured: float
        :param latency_measured: The latency_measured of this ConnectionQosMetrics.  # noqa: E501
        :type latency_measured: float
        :param packetloss_required: The packetloss_required of this ConnectionQosMetrics.  # noqa: E501
        :type packetloss_required: float
        :param packetloss_measured: The packetloss_measured of this ConnectionQosMetrics.  # noqa: E501
        :type packetloss_measured: float
        :param availability_required: The availability_required of this ConnectionQosMetrics.  # noqa: E501
        :type availability_required: float
        :param availability_measured: The availability_measured of this ConnectionQosMetrics.  # noqa: E501
        :type availability_measured: float
        """
        self.swagger_types = {
            "min_bw": ConnectionQosUnit,
            "max_delay": ConnectionQosUnit,
            "max_number_oxps": ConnectionQosUnit,
            "bandwidth_measured": float,
            "latency_measured": float,
            "packetloss_required": float,
            "packetloss_measured": float,
            "availability_required": float,
            "availability_measured": float,
        }

        self.attribute_map = {
            "min_bw": "min_bw",
            "max_delay": "max_delay",
            "max_number_oxps": "max_number_oxps",
            "bandwidth_measured": "bandwidth_measured",
            "latency_measured": "latency_measured",
            "packetloss_required": "packetloss_required",
            "packetloss_measured": "packetloss_measured",
            "availability_required": "availability_required",
            "availability_measured": "availability_measured",
        }
        self._min_bw = min_bw
        self._max_delay = max_delay
        self._max_number_oxps = max_number_oxps
        self._bandwidth_measured = bandwidth_measured
        self._latency_measured = latency_measured
        self._packetloss_required = packetloss_required
        self._packetloss_measured = packetloss_measured
        self._availability_required = availability_required
        self._availability_measured = availability_measured

    @classmethod
    def from_dict(cls, dikt) -> "ConnectionQosMetrics":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The connection_qos_metrics of this ConnectionQosMetrics.  # noqa: E501
        :rtype: ConnectionQosMetrics
        """
        return util.deserialize_model(dikt, cls)

    @property
    def min_bw(self) -> ConnectionQosUnit:
        """Gets the min_bw of this ConnectionQosMetrics.


        :return: The min_bw of this ConnectionQosMetrics.
        :rtype: ConnectionQosUnit
        """
        return self._min_bw

    @min_bw.setter
    def min_bw(self, min_bw: ConnectionQosUnit):
        """Sets the min_bw of this ConnectionQosMetrics.


        :param min_bw: The min_bw of this ConnectionQosMetrics.
        :type min_bw: ConnectionQosUnit
        """

        self._min_bw = min_bw

    @property
    def max_delay(self) -> ConnectionQosUnit:
        """Gets the max_delay of this ConnectionQosMetrics.


        :return: The max_delay of this ConnectionQosMetrics.
        :rtype: ConnectionQosUnit
        """
        return self._max_delay

    @max_delay.setter
    def max_delay(self, max_delay: ConnectionQosUnit):
        """Sets the max_delay of this ConnectionQosMetrics.


        :param max_delay: The max_delay of this ConnectionQosMetrics.
        :type max_delay: ConnectionQosUnit
        """

        self._max_delay = max_delay

    @property
    def max_number_oxps(self) -> ConnectionQosUnit:
        """Gets the max_number_oxps of this ConnectionQosMetrics.


        :return: The max_number_oxps of this ConnectionQosMetrics.
        :rtype: ConnectionQosUnit
        """
        return self._max_number_oxps

    @max_number_oxps.setter
    def max_number_oxps(self, max_number_oxps: ConnectionQosUnit):
        """Sets the max_number_oxps of this ConnectionQosMetrics.


        :param max_number_oxps: The max_number_oxps of this ConnectionQosMetrics.
        :type max_number_oxps: ConnectionQosUnit
        """

        self._max_number_oxps = max_number_oxps

    @property
    def bandwidth_measured(self) -> float:
        """Gets the bandwidth_measured of this ConnectionQosMetrics.


        :return: The bandwidth_measured of this ConnectionQosMetrics.
        :rtype: float
        """
        return self._bandwidth_measured

    @bandwidth_measured.setter
    def bandwidth_measured(self, bandwidth_measured: float):
        """Sets the bandwidth_measured of this ConnectionQosMetrics.


        :param bandwidth_measured: The bandwidth_measured of this ConnectionQosMetrics.
        :type bandwidth_measured: float
        """

        self._bandwidth_measured = bandwidth_measured

    @property
    def latency_measured(self) -> float:
        """Gets the latency_measured of this ConnectionQosMetrics.


        :return: The latency_measured of this ConnectionQosMetrics.
        :rtype: float
        """
        return self._latency_measured

    @latency_measured.setter
    def latency_measured(self, latency_measured: float):
        """Sets the latency_measured of this ConnectionQosMetrics.


        :param latency_measured: The latency_measured of this ConnectionQosMetrics.
        :type latency_measured: float
        """

        self._latency_measured = latency_measured

    @property
    def packetloss_required(self) -> float:
        """Gets the packetloss_required of this ConnectionQosMetrics.


        :return: The packetloss_required of this ConnectionQosMetrics.
        :rtype: float
        """
        return self._packetloss_required

    @packetloss_required.setter
    def packetloss_required(self, packetloss_required: float):
        """Sets the packetloss_required of this ConnectionQosMetrics.


        :param packetloss_required: The packetloss_required of this ConnectionQosMetrics.
        :type packetloss_required: float
        """

        self._packetloss_required = packetloss_required

    @property
    def packetloss_measured(self) -> float:
        """Gets the packetloss_measured of this ConnectionQosMetrics.


        :return: The packetloss_measured of this ConnectionQosMetrics.
        :rtype: float
        """
        return self._packetloss_measured

    @packetloss_measured.setter
    def packetloss_measured(self, packetloss_measured: float):
        """Sets the packetloss_measured of this ConnectionQosMetrics.


        :param packetloss_measured: The packetloss_measured of this ConnectionQosMetrics.
        :type packetloss_measured: float
        """

        self._packetloss_measured = packetloss_measured

    @property
    def availability_required(self) -> float:
        """Gets the availability_required of this ConnectionQosMetrics.


        :return: The availability_required of this ConnectionQosMetrics.
        :rtype: float
        """
        return self._availability_required

    @availability_required.setter
    def availability_required(self, availability_required: float):
        """Sets the availability_required of this ConnectionQosMetrics.


        :param availability_required: The availability_required of this ConnectionQosMetrics.
        :type availability_required: float
        """

        self._availability_required = availability_required

    @property
    def availability_measured(self) -> float:
        """Gets the availability_measured of this ConnectionQosMetrics.


        :return: The availability_measured of this ConnectionQosMetrics.
        :rtype: float
        """
        return self._availability_measured

    @availability_measured.setter
    def availability_measured(self, availability_measured: float):
        """Sets the availability_measured of this ConnectionQosMetrics.


        :param availability_measured: The availability_measured of this ConnectionQosMetrics.
        :type availability_measured: float
        """

        self._availability_measured = availability_measured

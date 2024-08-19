# coding: utf-8

from __future__ import absolute_import

from datetime import date, datetime  # noqa: F401
from typing import Dict, List  # noqa: F401

from sdx_controller import util
from sdx_controller.models.base_model_ import Model


class ConnectionScheduling(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(
        self, start_time: datetime = None, end_time: datetime = None
    ):  # noqa: E501
        """ConnectionScheduling - a model defined in Swagger

        :param start_time: The start_time of this ConnectionScheduling.  # noqa: E501
        :type start_time: datetime
        :param end_time: The end_time of this ConnectionScheduling.  # noqa: E501
        :type end_time: datetime
        """
        self.swagger_types = {"start_time": datetime, "end_time": datetime}

        self.attribute_map = {"start_time": "start_time", "end_time": "end_time"}
        self._start_time = start_time
        self._end_time = end_time

    @classmethod
    def from_dict(cls, dikt) -> "ConnectionScheduling":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The connection_scheduling of this ConnectionScheduling.  # noqa: E501
        :rtype: ConnectionScheduling
        """
        return util.deserialize_model(dikt, cls)

    @property
    def start_time(self) -> datetime:
        """Gets the start_time of this ConnectionScheduling.


        :return: The start_time of this ConnectionScheduling.
        :rtype: datetime
        """
        return self._start_time

    @start_time.setter
    def start_time(self, start_time: datetime):
        """Sets the start_time of this ConnectionScheduling.


        :param start_time: The start_time of this ConnectionScheduling.
        :type start_time: datetime
        """

        self._start_time = start_time

    @property
    def end_time(self) -> datetime:
        """Gets the end_time of this ConnectionScheduling.


        :return: The end_time of this ConnectionScheduling.
        :rtype: datetime
        """
        return self._end_time

    @end_time.setter
    def end_time(self, end_time: datetime):
        """Sets the end_time of this ConnectionScheduling.


        :param end_time: The end_time of this ConnectionScheduling.
        :type end_time: datetime
        """

        self._end_time = end_time
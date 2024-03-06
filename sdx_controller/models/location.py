# coding: utf-8

from __future__ import absolute_import

from datetime import date, datetime  # noqa: F401
from typing import Dict, List  # noqa: F401

from sdx_controller import util
from sdx_controller.models.base_model_ import Model


class Location(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(
        self,
        address: str = None,
        latitude: float = None,
        longitude: float = None,
        iso3166_2_lvl4: str = None,
    ):  # noqa: E501
        """Location - a model defined in Swagger

        :param address: The address of this Location.  # noqa: E501
        :type address: str
        :param latitude: The latitude of this Location.  # noqa: E501
        :type latitude: float
        :param longitude: The longitude of this Location.  # noqa: E501
        :type longitude: float
        :param iso3166_2_lvl4: The iso3166_2_lvl4 code of this Location. # noqa: E501
        :type iso3166_2_lvl4: str
        """
        self.swagger_types = {
            "address": str,
            "latitude": float,
            "longitude": float,
            "iso3166_2_lvl4": str,
        }

        self.attribute_map = {
            "address": "address",
            "latitude": "latitude",
            "longitude": "longitude",
            "iso3166_2_lvl4": "iso3166_2_lvl4",
        }
        self._address = address
        self._latitude = latitude
        self._longitude = longitude
        self._iso3166_2_lvl4 = iso3166_2_lvl4

    @classmethod
    def from_dict(cls, dikt) -> "Location":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The location of this Location.  # noqa: E501
        :rtype: Location
        """
        return util.deserialize_model(dikt, cls)

    @property
    def address(self) -> str:
        """Gets the address of this Location.


        :return: The address of this Location.
        :rtype: str
        """
        return self._address

    @address.setter
    def address(self, address: str):
        """Sets the address of this Location.


        :param address: The address of this Location.
        :type address: str
        """

        self._address = address

    @property
    def latitude(self) -> float:
        """Gets the latitude of this Location.


        :return: The latitude of this Location.
        :rtype: float
        """
        return self._latitude

    @latitude.setter
    def latitude(self, latitude: float):
        """Sets the latitude of this Location.


        :param latitude: The latitude of this Location.
        :type latitude: float
        """

        self._latitude = latitude

    @property
    def longitude(self) -> float:
        """Gets the longitude of this Location.


        :return: The longitude of this Location.
        :rtype: float
        """
        return self._longitude

    @longitude.setter
    def longitude(self, longitude: float):
        """Sets the longitude of this Location.


        :param longitude: The longitude of this Location.
        :type longitude: float
        """

        self._longitude = longitude

    @property
    def iso3166_2_lvl4(self) -> str:
        """Gets the iso3166_2_lvl4 of this Location.


        :return: The iso3166_2_lvl4 of this Location.
        :rtype: str
        """
        return self._iso3166_2_lvl4

    @iso3166_2_lvl4.setter
    def iso3166_2_lvl4(self, iso3166_2_lvl4: str):
        """Sets the iso3166_2_lvl4 of this Location.


        :param iso3166_2_lvl4: The iso3166_2_lvl4 of this Location.
        :type iso3166_2_lvl4: str
        """

        self._iso3166_2_lvl4 = iso3166_2_lvl4

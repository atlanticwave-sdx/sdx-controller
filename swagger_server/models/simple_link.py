from typing import List


class SimpleLink:
    def __init__(self, ports: List[str]):
        self._ports = ports

    @property
    def ports(self) -> List[str]:
        """Gets the ports of this Link.


        :return: The ports of this Link.
        :rtype: List[Port]
        """
        return self._ports

    @ports.setter
    def ports(self, ports: List[str]):
        """Sets the ports of this Link.


        :param ports: The ports of this Link.
        :type ports: List[Port]
        """
        if ports is None:
            raise ValueError(
                "Invalid value for `ports`, must not be `None`"
            )  # noqa: E501

        self._ports = ports
        self._ports.sort()

    def to_string(self):
        return ",".join(self._ports)

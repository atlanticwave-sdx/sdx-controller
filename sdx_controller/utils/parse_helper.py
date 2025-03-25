import json


class ParseHelper:
    def __init__(self):
        pass

    def is_json(self, json_str):
        try:
            json.loads(json_str)
        except ValueError:
            return False
        return True

    def find_domain_name(self, topology_id, delimiter):
        """
        Find domain name from topology id.
        Topology IDs are expected to be of the format
        "urn:ogf:network:sdx:topology:zaoxi.net"
        """
        *_, domain_name = topology_id.split(delimiter)
        return domain_name

from enum import Enum


class MongoCollections(Enum):
    TOPOLOGIES = "topologies"
    CONNECTIONS = "connections"
    BREAKDOWNS = "breakdowns"
    DOMAINS = "domains"
    LINKS = "links"
    HISTORICAL_CONNECTIONS = "historical_connections"

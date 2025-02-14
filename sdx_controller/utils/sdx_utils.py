class QueueExchange(Enum):
    CONNECTION = auto()
    OXP_UPDATE = auto()

    def __str__(self):
        return self.name


class QueueTopic(Enum):
    CONNECTION = auto()
    TOPO = auto()

    def __str__(self):
        return self.name


class TopologyMessage(object):
    def __init__(self, message, domain_name):
        self.message = message
        self.domain_name = domain_name


class BreakdownMessage(object):
    def __init__(self, message, domain_name):
        self.message = message
        self.domain_name = domain_name

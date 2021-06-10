from MessageQueue import *
from optparse import OptionParser
import argparse

class SDXController():
    ''' This is the main coordinating module of the SDX controller. It mostly 
        provides startup and coordination, rather than performan many actions by
        itself.
        Singleton. ''' 

    def __init__(self, options=None):
        ''' The bulk of the work happens here. This initializes nearly 
            everything and starts up the main processing loop for the entire SDX
            Controller. '''
        self.loggerid = 'sdxcontroller'
        self.logfilename = 'sdxcontroller.log'
        self.debuglogfilename = None

        manifest = options.manifest
        #db = options.database
        #run_topo = options.topo

        serverconfigure = RabbitMqServerConfigure(host='localhost',
                                            queue='hello')

        server = rabbitmqServer(server=serverconfigure)
        server.startserver()
    
    
if __name__ == '__main__':
    parser = OptionParser()

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # parser.add_argument("-d", "--database", dest="database", type=str, 
    #                     action="store", help="Specifies the database ", 
    #                     default=":memory:")
    #
    parser.add_argument("-m", "--manifest", dest="manifest", type=str, 
                        action="store", help="specifies the manifest")
    #
    # parser.add_argument("-N", "--no_topo", dest="topo", default=True, 
    #                     action="store_false", help="Run without the topology")
    #
    # parser.add_argument("-H", "--host", dest="host", default='0.0.0.0', 
    #                     action="store", type=str, help="Choose a host address ")
    #
    # parser.add_argument("-p", "--port", dest="port", default=5000, 
    #                     action="store", type=int, 
    #                     help="Port number of web interface")
    #
    # parser.add_argument("-e", "--sense", dest="sport", default=5001, 
    #                     action="store", type=int, 
    #                     help="Port number of SENSE interface")

    #parser.add_argument("-l", "--lcport", dest="lcport", default=PORT,
    #                    action="store", type=int,
    #                    help="Port number for LCs to connect to")

    # Failure handling, enabled by default
    #parser.add_argument("-f", "--failrecover", dest="failrecover", default=True,
    #                    action="store_false", help="Run with failure recover")

    options = parser.parse_args()

    if not options.manifest:
        parser.print_help()
        exit()
        
    sdx = SDXController(options)
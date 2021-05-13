class SDXController(AtlanticWaveModule):
    ''' This is the main coordinating module of the SDX controller. It mostly 
        provides startup and coordination, rather than performan many actions by
        itself.
        Singleton. ''' 

    def __init__(self, runloop=True, options=None):
        ''' The bulk of the work happens here. This initializes nearly 
            everything and starts up the main processing loop for the entire SDX
            Controller. '''
        self.loggerid = 'sdxcontroller'
        self.logfilename = 'sdxcontroller.log'
        self.debuglogfilename = None
        super(SDXController, self).__init__(self.loggerid, self.logfilename,
                                            self.debuglogfilename)

        mani = options.manifest
        db = options.database
        run_topo = options.topo

        self.db_filename = db
        self.failrecover = options.failrecover

        # self.run_topo decides whether or not to send rules.
        self.run_topo = run_topo

        # Modules with configuration files
        self.tm = TopologyManager(self.loggerid, mani)

        # Initialize all the modules - Ordering is relatively important here
#        self.aci = AuthenticationInspector(self.loggerid)
#        self.azi = AuthorizationInspector(self.loggerid)
#        self.be = BreakdownEngine(self.loggerid)
#        self.rr = RuleRegistry(self.loggerid)
#        self.vi = ValidityInspector(self.loggerid)
#        self.um = UserManager(self.db_filename, mani, self.loggerid)

        if mani != None:
            self.lcm = LocalControllerManager(self.loggerid, mani)
        else: 
            self.lcm = LocalControllerManager(self.loggerid)

        topo = self.tm.get_topology()


        # Set up the connection-related nonsense - Have a connection event queue
#        self.ip = options.host
#        self.port = options.lcport
#        self.connections = {}
#        self.sdx_cm = SDXControllerConnectionManager(self.loggerid)
#        self.cm_thread = threading.Thread(target=self._cm_thread)
#        self.cm_thread.daemon = True
#        self.cm_thread.start()

        # Register known UserPolicies
#        self.rr.add_ruletype(L2TunnelPolicy)
#        self.rr.add_ruletype(L2MultipointPolicy)
#        self.rr.add_ruletype(EndpointConnectionPolicy)
#        self.rr.add_ruletype(EdgePortPolicy)
#        self.rr.add_ruletype(LearnedDestinationPolicy)
#        self.rr.add_ruletype(FloodTreePolicy)
#        self.rr.add_ruletype(SDXEgressPolicy)
#        self.rr.add_ruletype(SDXIngressPolicy)
#        self.rr.add_ruletype(ManagementSDXRecoverPolicy)

        # Start these modules last!
        if self.run_topo:
            self.rm = RuleManager(self.db_filename, self.loggerid,
                                  self.sdx_cm.send_breakdown_rule_add,
                                  self.sdx_cm.send_breakdown_rule_rm)
        else:
            self.rm = RuleManager(self.db_filename, self.loggerid,
                                  send_no_rules,
                                  send_no_rules)

        self.rapi = RestAPI(self.loggerid,
                            options.host, options.port, options.shib)
        self.sapi = SenseAPI(self.loggerid,
                             host=options.host, port=options.sport)


        # Install any rules switches will need. 
        self._prep_switches()

        self.logger.warning("%s initialized: %s" % (self.__class__.__name__,
                                                    hex(id(self))))

        # Go to main loop 
        if runloop:
            self._main_loop()
            
    def start_main_loop(self):
        self.main_loop_thread = threading.Thread(target=self._main_loop)
        self.main_loop_thread.daemon = True
        self.main_loop_thread.start()
        self.logger.debug("Main Loop - %s" % (self.main_loop_thread))

    def _main_loop(self):
        # Set up the select structures
        rlist = self.connections.values()
        wlist = []
        xlist = rlist
        timeout = 2.0

        # Main loop - Have a ~500ms timer on the select call to handle cxn 
        # events
        while True:
            # Handle event queue messages
            try:
                q_ele = self.sdx_cm.get_cxn_queue_element()
                while q_ele != None:
                    (action, cxn) = q_ele
                    if action == NEW_CXN:
                        self.logger.warning("Adding connection %s" % cxn)
                        if cxn in rlist:
                            # Already there. Weird, but OK
                            pass
                        rlist.append(cxn)
                        wlist = []
                        xlist = rlist
                        
                    elif action == DEL_CXN:
                        self.logger.warning("Removing connection %s" % cxn)
                        if cxn in rlist:
                            self._handle_connection_loss(cxn)
                            rlist.remove(cxn)
                            wlist = []
                            xlist = rlist
                    # Next queue element
                    q_ele = self.sdx_cm.get_cxn_queue_element()
            except:
                raise
                # This is raised if the cxn_q is empty of events.
                # Normal behaviour
                pass
                
            # Dispatch messages as appropriate
            try: 
                readable, writable, exceptional = cxnselect(rlist,
                                                            wlist,
                                                            xlist,
                                                            timeout)
            except Exception as e:
                self.logger.warning("select returned error: %s" % e)
                # This can happen if, say, there's a disconnection that hasn't
                # cleaned up or occured *during* the timeout period. This is due
                # to select failing.
                sleep(timeout/2)
                continue

            # Loop through readable
            for entry in readable:
                # Get Message
                try:
                    msg = entry.recv_protocol()
                except SDXMessageConnectionFailure as e:
                    # Connection needs to be disconnected.
                    entry.close()
                    continue
                except:
                    raise

                # Can return None if there was some internal message.
                if msg == None:
                    #self.logger.debug("Received internal message from recv_protocol %s" %
                    #                  hex(id(entry)))
                    continue
                self.logger.debug("Received a %s message from %s" %
                                  (type(msg), hex(id(entry))))

                # If message is UnknownSource or L2MultipointUnknownSource,
                # Send the appropriate handler.
                if isinstance(msg, SDXMessageUnknownSource):
                    self._switch_message_unknown_source(msg)
                elif isinstance(msg, SDXMessageL2MultipointUnknownSource):
                    self._switch_change_callback_handler(msg)

                # Else: Log an error
                else:
                    self.logger.error("Message %s is not valid" % msg)

            # Loop through writable
            for entry in writable:
                # Anything to do here?
                pass

            # Loop through exceptional
            for entry in exceptional:
                # FIXME: Handle connection failures
                pass
    

if __name__ == '__main__':
    #from optparse import OptionParser
    #parser = OptionParser()

    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-d", "--database", dest="database", type=str, 
                        action="store", help="Specifies the database ", 
                        default=":memory:")

    parser.add_argument("-m", "--manifest", dest="manifest", type=str, 
                        action="store", help="specifies the manifest")

    parser.add_argument("-s", "--shibboleth", dest="shib", default=False, 
                        action="store_true", help="Run with Shibboleth for authentication")

    parser.add_argument("-N", "--no_topo", dest="topo", default=True, 
                        action="store_false", help="Run without the topology")

    parser.add_argument("-H", "--host", dest="host", default='0.0.0.0', 
                        action="store", type=str, help="Choose a host address ")

    parser.add_argument("-p", "--port", dest="port", default=5000, 
                        action="store", type=int, 
                        help="Port number of web interface")

    parser.add_argument("-e", "--sense", dest="sport", default=5001, 
                        action="store", type=int, 
                        help="Port number of SENSE interface")

    parser.add_argument("-l", "--lcport", dest="lcport", default=PORT,
                        action="store", type=int,
                        help="Port number for LCs to connect to")

    # Failure handling, enabled by default
    parser.add_argument("-f", "--failrecover", dest="failrecover", default=True,
                        action="store_false", help="Run with failure recover")

    options = parser.parse_args()

    print("------------------OPTIONS-----------------------")
    print(options)

    if not options.manifest:
        parser.print_help()
        exit()
        
    sdx = SDXController(False, options)
    sdx._main_loop()
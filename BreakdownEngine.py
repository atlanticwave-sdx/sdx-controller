from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import hex
from builtins import str
from lib.AtlanticWaveModule import AtlanticWaveModule
from sdxctlr.AuthorizationInspector import AuthorizationInspector
from sdxctlr.TopologyManager import TopologyManager


class BreakdownEngine(AtlanticWaveModule):
    ''' The BreakdownEngine is one of the more complex pieces of the SDX 
        controller. It takes participant-level rules and breaks them down into 
        per-local controller rules. In the future, failover considerations will
        be added, in particular automatically creating backup paths will be 
        added as a standard feature.
        Singleton. '''
    
    def __init__(self, loggeridprefix='sdxcontroller', CATCH_ERRORS=True):
        loggerid = loggeridprefix + '.breakdownengine'
        super(BreakdownEngine, self).__init__(loggerid)
        self.CATCH_ERRORS = CATCH_ERRORS

        self.logger.warning("%s initialized: %s" % (self.__class__.__name__,
                                                    hex(id(self))))

    def get_breakdown(self, rule):
        ''' Breaks down the given rule to rules that each local controller can 
            handle. Requires a user to verify that the user had the correct 
            permissions determined by the AuthorizationInspector for proposed 
            rules (e.g., if a user cannot create paths through a particular LC, 
            reroute around that LC). '''
        if self.CATCH_ERRORS:
            try:
                tm = TopologyManager()
                ai = AuthorizationInspector()
                return rule.breakdown_rule(tm, ai)
            except Exception as e:
                self.dlogger.error("Caught Error \"%s\" for rule %s" %
                                   (str(e),rule))
                self.exception_tb(e)
        else:
            tm = TopologyManager()
            ai = AuthorizationInspector()
            return rule.breakdown_rule(tm, ai)

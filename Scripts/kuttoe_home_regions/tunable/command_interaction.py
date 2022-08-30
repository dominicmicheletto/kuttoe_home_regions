#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sim4 imports
from sims4.utils import constproperty

# event testing imports
from event_testing.tests import TestList

# local imports
from kuttoe_home_regions.interactions import CommandImmediateSuperInteraction
from kuttoe_home_regions.tunable.python_based_interaction_data import PythonBasedInteractionWithRegionData


#######################################################################################################################
#  Command Interaction                                                                                                #
#######################################################################################################################


class CommandInteractionTuningData(PythonBasedInteractionWithRegionData):
    @constproperty
    def class_base():
        return CommandImmediateSuperInteraction

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test())
        base_tests.append(self.get_identity_test())
        base_tests.append(self.get_trait_blacklist())
        base_tests.append(self.get_zone_test())
        base_tests.append(self.get_home_region_test())

        return TestList(base_tests)

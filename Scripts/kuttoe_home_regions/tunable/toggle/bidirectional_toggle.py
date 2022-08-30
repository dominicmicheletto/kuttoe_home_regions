#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# event testing imports
from event_testing.tests import TestList, CompoundTestList

# local imports
from kuttoe_home_regions.tunable.toggle import _BooleanToggleInteractionTuningDataBase


#######################################################################################################################
# Bidirectional Toggle                                                                                                #
#######################################################################################################################


class BidirectionalToggleTuningData(_BooleanToggleInteractionTuningDataBase):
    @property
    def global_tests(self):
        return TestList()

    def get_enabled_tests(self, toggle_value: bool):
        base_tests = list()
        base_tests.append(self.get_boolean_toggle_test('bidirectional_toggle', toggle_value))

        return CompoundTestList([TestList(base_tests)])

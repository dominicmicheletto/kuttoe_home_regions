#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sim4 imports
from sims4.common import Pack

# event testing imports
from event_testing.tests import TestList, CompoundTestList

# local imports
from kuttoe_home_regions.tunable.toggle import _BooleanToggleInteractionTuningDataBase


#######################################################################################################################
# Soft Filter Toggle                                                                                                  #
#######################################################################################################################


class HighSchoolToggleTuningData(_BooleanToggleInteractionTuningDataBase):
    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_pack_test({Pack.EP12}))

        return TestList(base_tests)

    def get_enabled_tests(self, toggle_value: bool):
        base_tests = list()
        base_tests.append(self.get_boolean_toggle_test('high_school_toggle', toggle_value))

        return CompoundTestList([TestList(base_tests)])

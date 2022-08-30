#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sim4 imports
from sims4.utils import constproperty
from sims4.tuning.tunable import OptionalTunable

# interaction imports
from interactions import ParticipantType
from interactions.utils.tunable_icon import TunableIconVariant

# event testing imports
from event_testing.tests import TestList, CompoundTestList

# ui imports
from ui.ui_dialog_picker import UiSimPicker

# local imports
from kuttoe_home_regions.interactions import HomeWorldPickerInteraction
from kuttoe_home_regions.tunable.python_based_interaction_data import PythonBasedInteractionWithRegionData


#######################################################################################################################
#  Picker Interaction                                                                                                 #
#######################################################################################################################


class PickerInteractionTuningData(PythonBasedInteractionWithRegionData):
    FACTORY_TUNABLES = {
        'sim_picker': UiSimPicker.TunableFactory(),
        'picker_icon': OptionalTunable(tunable=TunableIconVariant()),
    }

    @constproperty
    def class_base():
        return HomeWorldPickerInteraction

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.Actor, is_npc=False))

        return TestList(base_tests)

    @property
    def sim_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.PickedSim))
        base_tests.append(self.get_trait_blacklist(participant=ParticipantType.PickedSim))
        base_tests.append(self.get_zone_test(participant=ParticipantType.PickedSim))
        base_tests.append(self.get_home_region_test(participant=ParticipantType.PickedSim))

        return CompoundTestList([TestList(base_tests)])

    @constproperty
    def locked_args() -> dict:
        locked_args = dict()
        locked_args['include_actor_sim'] = False
        locked_args['include_uninstantiated_sims'] = True

        return locked_args

    @constproperty
    def properties_mapping() -> dict:
        properties_mapping = dict()
        properties_mapping['sim_tests'] = 'sim_tests'
        properties_mapping['_icon'] = 'picker_icon'
        properties_mapping['picker_dialog'] = 'sim_picker'

        return properties_mapping

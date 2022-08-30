#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Dict
from collections import defaultdict

# sim4 imports
from sims4.utils import classproperty, constproperty

# interaction imports
from interactions import ParticipantType
from interactions.base.immediate_interaction import ImmediateSuperInteraction

# event testing imports
from event_testing.tests import TestList, CompoundTestList

# local imports
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.interactions import SoftTogglePickerInteraction, ToggleSettingImmediateSuperInteraction
from kuttoe_home_regions.tunable import TunableInteractionName
from kuttoe_home_regions.tunable.toggle import _ToggleInteractionTuningDataBase
from kuttoe_home_regions.tunable.python_based_interaction_data import PythonBasedInteractionWithRegionData


#######################################################################################################################
# Soft Filter Toggle                                                                                                  #
#######################################################################################################################


class SoftFilterInteractionTuningData(_ToggleInteractionTuningDataBase, PythonBasedInteractionWithRegionData):
    _SUB_INTERACTION_CACHE = defaultdict(dict)

    @constproperty
    def class_base():
        return SoftTogglePickerInteraction

    @classproperty
    def sub_interaction_cache(cls) -> Dict[HomeWorldIds, Dict[bool, ImmediateSuperInteraction]]:
        return cls._SUB_INTERACTION_CACHE

    @constproperty
    def sub_interaction_base_class():
        return ToggleSettingImmediateSuperInteraction

    @property
    def sub_interaction_locked_args(self):
        locked_args = dict()

        locked_args['target_home_world'] = self.home_world
        return locked_args

    def _get_sub_interaction_name(self, toggle_value: bool):
        suffix = {True: 'On', False: 'Off'}[toggle_value]
        func = TunableInteractionName._Wrapper._get_hash_for_name

        return func(self.interaction_name_base(self.home_world)[0], suffix)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for home_world in HomeWorldIds:
            if home_world is HomeWorldIds.DEFAULT:
                continue

            for toggle_value in (True, False):
                self.sub_interaction_cache[self.home_world][toggle_value] = self._create_sub_interaction(toggle_value)

    @property
    def additional_picker_dialog_tokens(self):
        return (self.home_world.region_name(),)

    @property
    def additional_picker_item_args(self):
        return {'args': (self.home_world,), 'kwargs': {}}

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.Actor, is_npc=False))

        return TestList(base_tests)

    @classmethod
    def _get_continuation_affordance(cls, toggle_value: bool, source_world: HomeWorldIds):
        return cls.sub_interaction_cache[source_world][toggle_value]

    @property
    def additional_disable_token_reasons(self):
        return (self.home_world.region_name(),)

    def get_enabled_tests(self, toggle_value: bool):
        base_tests = list()
        base_tests.append(self.get_soft_filter_toggle_test(self.home_world, toggle_value))

        return CompoundTestList([TestList(base_tests)])

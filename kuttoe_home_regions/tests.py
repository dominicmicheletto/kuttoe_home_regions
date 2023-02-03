"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details custom tests that are used throughout the mod and functions used to create these tests in
Python instead of in tuning. It also details custom test set instances used by interactions in the mod.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from typing import List

# sim4 imports
from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableEnumEntry
from sims4.utils import constproperty

# event testing imports
from event_testing.test_base import BaseTest
from event_testing.results import TestResult
from event_testing.tests import _TunableTestSetBase, TunableTestVariant, TestSetInstance, TestList

# miscellaneous imports
from interactions import ParticipantTypeSingle, ParticipantTypeActorTargetSim
from caches import cached_test

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.commands import AlterType
from kuttoe_home_regions.utils import construct_auto_init_factory
from kuttoe_home_regions.interactions.mixins import HasHomeWorldMixin


#######################################################################################################################
# Factories                                                                                                           #
#######################################################################################################################

class _WorldsTestsBase(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {
        'target_home_world': HomeWorldIds.create_enum_entry(),
        'alter_type': AlterType.to_enum_entry(),
    }

    def get_expected_args(self):
        return {}

    @property
    def world_settings(self):
        from kuttoe_home_regions.settings import Settings

        return Settings.get_world_settings(self.world_value_source)

    @property
    def worlds_list(self) -> List[str]:
        from kuttoe_home_regions.settings import Settings

        return self.world_settings[Settings.WorldSettingNames.WORLDS]


class WorldsAvailableLeftTest(_WorldsTestsBase):
    @property
    def world_value_source(self):
        return self.target_home_world

    @constproperty
    def all_worlds():
        return {world.name for world in HomeWorldIds if world is not HomeWorldIds.DEFAULT}

    def get_available_worlds(self):
        return self.get_all_possible_worlds() - set(self.worlds_list)

    def get_all_possible_worlds(self):
        return self.all_worlds - {self.target_home_world.name}

    def __call__(self):
        if self.alter_type == AlterType.ALLOW_WORLD and self.get_available_worlds():
            return TestResult.TRUE
        elif self.alter_type == AlterType.DISALLOW_WORLD and self.worlds_list:
            return TestResult.TRUE
        else:
            return TestResult(False, 'World {} does not fit the required constraints', self.target_home_world.name,
                              tooltip=self.tooltip)


class IsWorldAvailableTest(_WorldsTestsBase):
    FACTORY_TUNABLES = {
        'source_world': HomeWorldIds.create_enum_entry(),
    }

    @property
    def world_value_source(self):
        return self.source_world

    def __call__(self):
        result = self.target_home_world.name in self.worlds_list

        if self.alter_type == AlterType.DISALLOW_WORLD and result:
            return TestResult.TRUE
        elif self.alter_type == AlterType.ALLOW_WORLD and not result:
            return TestResult.TRUE
        else:
            reason = 'already' if self.alter_type == AlterType.ALLOW_WORLD else 'not currently'

            return TestResult(False, 'World {} {} in {}\'s allow list',
                              self.source_world.name, reason, self.target_home_world.name)


class WorldHasSoftFilterEnabledTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {
        'source_world': HomeWorldIds.create_enum_entry(),
        'negate': Tunable(tunable_type=bool, default=False)
    }

    def get_expected_args(self):
        return {}

    @property
    def world_value_source(self):
        return self.source_world

    @property
    def world_settings(self):
        from kuttoe_home_regions.settings import Settings

        return Settings.get_world_settings(self.world_value_source)

    @property
    def soft_filter_value(self) -> bool:
        from kuttoe_home_regions.settings import Settings

        return self.world_settings[Settings.WorldSettingNames.SOFT]

    def __call__(self):
        result = self.soft_filter_value
        msg = f'World {self.world_value_source} does not have expected soft filter setting'

        return TestResult(not result if self.negate else result, msg, tooltip=self.tooltip)


class HasHomeRegionTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest, HasHomeWorldMixin):
    FACTORY_TUNABLES = {
        'participant': TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeActorTargetSim.Actor),
        'negate': Tunable(tunable_type=bool, default=False),
    }

    def get_expected_args(self):
        return {'test_targets': self.participant}

    def _get_test_result(self, test_targets, home_world: HomeWorldIds):
        test = self.get_home_region_test(home_world, participant=ParticipantTypeSingle.Actor, negate=False)
        test_list = TestList((test, ))

        result = False
        for participant in test_targets:
            result |= test_list.run_tests(participant.get_resolver()).result

        return result

    @cached_test
    def __call__(self, test_targets):
        found_home_region = False

        for world in HomeWorldIds.available_worlds:
            found_home_region |= self._get_test_result(test_targets, world)

            if found_home_region:
                if self.negate:
                    return TestResult(False, f'Sim has home region of {world}', tooltip=self.tooltip)
                return TestResult.TRUE

        if self.negate:
            return TestResult.TRUE
        return TestResult(False, f'Sim has no home region', tooltip=self.tooltip)


#######################################################################################################################
# Test Set Instances                                                                                                  #
#######################################################################################################################

class HomeRegionsTestSet(_TunableTestSetBase, is_fragment=True):
    MY_TEST_VARIANTS = {
        'has_home_region': HasHomeRegionTest,
    }

    def __init__(self, *args, **kwargs):
        for (test_name, test_factory) in self.MY_TEST_VARIANTS.items():
            TunableTestVariant.TEST_VARIANTS[test_name] = test_factory.TunableFactory

        super().__init__(*args, **kwargs)


class HomeRegionsTestSetInstance(TestSetInstance):
    INSTANCE_TUNABLES = {'test': HomeRegionsTestSet()}


#######################################################################################################################
# Functions                                                                                                           #
#######################################################################################################################

def get_is_world_available_test(
        source_world: HomeWorldIds,
        target_world: HomeWorldIds,
        alter_type: AlterType = AlterType.ALLOW_WORLD
):
    args = dict()
    args['source_world'] = source_world
    args['target_home_world'] = target_world
    args['alter_type'] = alter_type

    return construct_auto_init_factory(IsWorldAvailableTest, **args)


def get_worlds_available_left_test(
        target_world: HomeWorldIds,
        alter_type: AlterType,
        disabled_tooltip=None
):
    args = dict()
    args['target_home_world'] = target_world
    args['alter_type'] = alter_type
    if disabled_tooltip:
        args['tooltip'] = lambda *tokens: disabled_tooltip(target_world.region_name(), *tokens)

    return construct_auto_init_factory(WorldsAvailableLeftTest, **args)


def get_soft_filter_enabled_test(
        source_home_world: HomeWorldIds,
        disabled_tooltip=None,
        negate: bool = False,
):
    args = dict()
    args['source_world'] = source_home_world
    args['negate'] = negate
    if disabled_tooltip:
        args['tooltip'] = lambda *tokens: disabled_tooltip(source_home_world.region_name(), *tokens)

    return construct_auto_init_factory(WorldHasSoftFilterEnabledTest, **args)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = (
    'get_is_world_available_test', 'get_worlds_available_left_test', 'get_soft_filter_enabled_test',
    'WorldsAvailableLeftTest', 'IsWorldAvailableTest', 'WorldHasSoftFilterEnabledTest',
)

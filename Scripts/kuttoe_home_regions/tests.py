#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import List

# sim4 imports
from sims4.tuning.tunable import AutoFactoryInit, TunableEnumEntry, HasTunableSingletonFactory, TunableEnumSet
from sims4.tuning.tunable import TunableList, TunablePackSafeReference, Tunable
from sims4.localization import TunableLocalizedStringFactory
from sims4.utils import constproperty
from sims4.resources import Types

# event testing imports
from event_testing.test_base import BaseTest
from event_testing.results import TestResult

# interaction imports
from interactions import ParticipantTypeSingle, ParticipantTypeSingleSim, ParticipantType

# sim imports
from sims.sim_info_tests import TraitTest, SimInfoTest, MatchType, _SpeciesTestSpecies
from sims.sim_info_types import Age, Species

# misc test imports
from zone_tests import ZoneTest, ParticipantHomeZone
from traits.trait_type import TraitType
from world.world_tests import HomeRegionTest
from traits.traits import Trait
from services import get_instance_manager

# event testing imports
from event_testing.test_variants import TunableIdentityTest

# tunable utils imports
from tunable_utils.tunable_white_black_list import TunableWhiteBlackList

# local imports
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.commands import AlterType
from kuttoe_home_regions.utils import construct_auto_init_factory, make_immutable_slots_class


#######################################################################################################################
#  Tests                                                                                                              #
#######################################################################################################################


class _WorldsTestsBase(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {
        'target_home_world': TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT),
        'alter_type': TunableEnumEntry(tunable_type=AlterType, default=AlterType.ALLOW_WORLD),
    }

    def get_expected_args(self):
        return {}

    @property
    def world_settings(self):
        from kuttoe_home_regions.settings import Settings

        return Settings.get_world_settings(self.world_value_source)

    @property
    def worlds_list(self) -> List[str]:
        return self.world_settings['Worlds']


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
        'source_world': TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT),
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


class SoftFilterToggleValueTest(_WorldsTestsBase):
    FACTORY_TUNABLES = {
        'invert': Tunable(tunable_type=bool, default=False),
    }

    @property
    def world_value_source(self):
        return self.target_home_world

    @property
    def toggle_value(self) -> bool:
        return self.world_settings['Soft']

    def __call__(self):
        result = self.toggle_value != self.invert

        return TestResult(result, 'World {} does not have the required soft filter value of {}',
                          self.target_home_world.name, not self.invert, tooltip=self.tooltip)


#######################################################################################################################
#  Test Set Mixin                                                                                                     #
#######################################################################################################################


class _TestSetMixin:
    ALREADY_RESIDENT_TOOLTIP = TunableLocalizedStringFactory()
    SIM_HAS_HOUSE_TOOLTIP = TunableLocalizedStringFactory()
    BLACKLIST_TRAIT_TYPES = TunableEnumSet(enum_type=TraitType, allow_empty_set=True)
    TRAIT_BLACKLIST = TunableList(tunable=Trait.TunablePackSafeReference(), allow_none=False)
    VENUE_FILTER = TunableWhiteBlackList(tunable=TunablePackSafeReference(manager=get_instance_manager(Types.VENUE)))

    @staticmethod
    def get_soft_filter_toggle_test(source_world: HomeWorldIds, invert: bool = False, disabled_tooltip=None):
        args = dict()
        args['target_home_world'] = source_world
        args['invert'] = invert
        if disabled_tooltip:
            args['tooltip'] = lambda *tokens: disabled_tooltip(source_world.region_name(), *tokens)

        return construct_auto_init_factory(SoftFilterToggleValueTest, **args)

    @staticmethod
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

    @staticmethod
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

    def get_home_region_test(self, participant: ParticipantType = ParticipantType.TargetSim):
        args = dict()
        args['negate'] = True
        args['participant'] = participant
        args['region'] = self.region
        args['tooltip'] = self.ALREADY_RESIDENT_TOOLTIP

        return construct_auto_init_factory(HomeRegionTest, **args)

    def get_trait_blacklist(self, participant: ParticipantType = ParticipantType.TargetSim):
        args = dict()
        args['subject'] = participant
        args['whitelist_traits'] = tuple()
        args['blacklist_traits'] = self.TRAIT_BLACKLIST
        args['whitelist_trait_types'] = set()
        args['blacklist_trait_types'] = self.BLACKLIST_TRAIT_TYPES
        args['num_whitelist_required'] = 1
        args['num_blacklist_allowed'] = 0
        args['apply_thresholds_on_individual_basis'] = True

        return construct_auto_init_factory(TraitTest, **args)

    @staticmethod
    def get_identity_test(subjects_match=False):
        args = dict()
        args['subject_a'] = ParticipantTypeSingle.Actor
        args['subject_b'] = ParticipantTypeSingle.Object
        args['subjects_match'] = subjects_match
        args['use_definition'] = False
        args['use_part_owner'] = False

        return construct_auto_init_factory(TunableIdentityTest, has_factory=False, **args)

    @staticmethod
    def get_sim_info_test(participant: ParticipantType = ParticipantType.TargetSim, is_npc=True):
        args = dict()
        args['who'] = participant
        args['ages'] = {age for age in Age.values if age not in (Age.TODDLER, )}
        args['species'] = construct_auto_init_factory(_SpeciesTestSpecies, species={Species.HUMAN})
        args['npc'] = is_npc
        args['match_type'] = MatchType.MATCH_ALL

        return construct_auto_init_factory(SimInfoTest, **args)

    def get_zone_test(self, participant: ParticipantTypeSingleSim = ParticipantTypeSingleSim.TargetSim,
                      use_tooltip=True):
        args = dict()
        args['tooltip'] = self.SIM_HAS_HOUSE_TOOLTIP if use_tooltip else None
        args['zone_source_invalid_fallback'] = True
        args['zone_source'] = ParticipantHomeZone(participant=participant)

        zone_test_args = dict()
        zone_test_args['business_tests'] = None
        zone_test_args['is_apartment'] = None
        zone_test_args['is_penthouse'] = None
        zone_test_args['is_reserved'] = None
        zone_test_args['venue_tier'] = None
        zone_test_args['was_owner_household_changed'] = None
        zone_test_args['world_tests'] = None
        zone_test_args['zone_modifiers'] = None
        zone_test_args['use_source_venue'] = False
        zone_test_args['venue_type'] = self.VENUE_FILTER
        args['zone_tests'] = make_immutable_slots_class(**zone_test_args)

        return construct_auto_init_factory(ZoneTest, **args)


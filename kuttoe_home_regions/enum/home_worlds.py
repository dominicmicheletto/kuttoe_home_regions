"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the HomeWorldIds enumeration which contains a ton of information necessary for other aspects of the
mod to function.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from typing import Dict, Any

# misc imports
import enum
from services import get_instance_manager
from singletons import DEFAULT

# sims 4 imports
from sims4.resources import Types
from sims4.collections import frozendict
from sims4.tuning.tunable import Tunable, TunablePackSafeReference, OptionalTunable
from sims4.localization import TunableLocalizedStringFactory
from sims4.common import Pack, is_available_pack
from sims4.utils import classproperty

# world imports
from world.region import RegionType

# local imports
from kuttoe_home_regions.enum import DynamicFactoryEnumMetaclass, EnumItemFactory
from kuttoe_home_regions.utils import *
from kuttoe_home_regions.tunable.local_fixup import OptionalTunableLocalFixup, LocalFixup
from kuttoe_home_regions.tunable.world_icon_definition import TunableWorldIconMappingVariant, WorldIconSize
from kuttoe_home_regions.tunable.pack_resources import PackDefinition
from kuttoe_home_regions.tunable.bit_value import TunableBitValueVariant
from kuttoe_home_regions.tunable.street_selector import TunableStreetSelectorVariant


#######################################################################################################################
# Helper Enumeration  Declaration                                                                                     #
#######################################################################################################################

@enum_entry_factory(default='BASE_GAME', invalid=())
class WorldType(enum.Int):
    BASE_GAME = ...
    RESIDENTIAL = ...
    VACATION = ...
    HIDDEN = ...


#######################################################################################################################
# Factory Class Code                                                                                                  #
#######################################################################################################################

class RegionData:
    _LAST_BIT_VALUE = 0

    def __init__(
            self,
            region_id: int = 0,
            name=None,
            street_for_creation=None,
            pack: Pack = Pack.BASE_GAME,
            icon_mapping=frozendict(),
            local_fixup: LocalFixup = None,
            has_tourists: bool = False,
            bit_value: TunableBitValueVariant._Wrapper = TunableBitValueVariant.DEFAULT,
            world_type: WorldType = None,
    ):
        self._region_id = region_id
        self._name = name
        self._pack = pack
        self._icon_mapping = icon_mapping if type(icon_mapping) is frozendict else icon_mapping(self).get_icon_mapping()
        self._street_for_creation = street_for_creation
        self._local_fixup = local_fixup(self._region_id) if local_fixup else None
        self._has_tourists = has_tourists

        bit_value = TunableBitValueVariant.resolve_value(bit_value)
        if bit_value.value:
            self._LAST_BIT_VALUE = bit_value.value
        self._bit_value = bit_value.get_value(self._LAST_BIT_VALUE, self._pack)

        self._world_type = world_type

    @property
    def raw_bit_value(self): return self._bit_value

    @property
    def bit_value(self): return 1 << self._bit_value

    @property
    def street_for_creation(self): return self._street_for_creation

    @property
    def region_name(self) -> TunableLocalizedStringFactory._Wrapper: return self._name

    @property
    def pack(self): return self._pack

    @property
    def is_available(self) -> bool: return is_available_pack(self.pack)

    @property
    def icon_mapping(self) -> Dict[WorldIconSize, Any]: return self._icon_mapping

    @property
    def pie_menu_icon(self): return self.get_icon()

    def get_icon(self, icon_size=WorldIconSize.SMALL): return self.icon_mapping.get(icon_size, None)

    @property
    def has_tourists(self): return self._has_tourists

    @property
    def local_fixup(self): return self._local_fixup

    @property
    def has_local_fixup(self): return self._local_fixup is not None

    @property
    def default_local_fixup(self): return construct_auto_init_factory(LocalFixup, region_id=self._region_id)

    def apply_fixup_to_sim_info(self, sim_info, previous_region_id: int):
        if sim_info is None:
            return

        if self.has_local_fixup:
            self.local_fixup(sim_info, previous_region_id)
        else:
            return self.default_local_fixup.clear_all_data(sim_info)

    @property
    def world_type(self) -> WorldType:
        if self._world_type is not None:
            return self._world_type
        if self._pack is Pack.BASE_GAME:
            return WorldType.BASE_GAME
        if self.region.region_type is RegionType.REGIONTYPE_RESIDENTIAL:
            return WorldType.RESIDENTIAL
        elif self.region.region_type is RegionType.REGIONTYPE_DESTINATION:
            return WorldType.VACATION

    @property
    def supports_multiple_creation_streets(self):
        if self._street_for_creation is None:
            return False

        return self._street_for_creation.supports_multiple_streets

    @property
    def creation_streets(self):
        if self._street_for_creation is None:
            return frozenset()

        return self._street_for_creation.street_ids

    def has_street(self, street_id: int):
        return street_id in self._street_for_creation


@EnumItemFactory.ReprMixin(name='region_name', region_id=None, region=DEFAULT)
@EnumItemFactory.TunableReferenceMixin(region=('region_id', True))
class RegionDataFactory(EnumItemFactory):
    FACTORY_TUNABLES = {
        'region': TunablePackSafeReference(manager=get_instance_manager(Types.REGION)),
        'name': TunableLocalizedStringFactory(),
        'pack': PackDefinition(),
        'icon_mapping': TunableWorldIconMappingVariant(),
        'street_for_creation': TunableStreetSelectorVariant(),
        'local_fixup': OptionalTunableLocalFixup(),
        'has_tourists': Tunable(tunable_type=bool, default=False),
        'bit_value': TunableBitValueVariant(),
        'world_type': OptionalTunable(WorldType.to_enum_entry()),
    }
    FACTORY_TYPE = RegionData

    def __init__(self, *args, **kwargs):
        kwargs.update(self.FACTORY_TUNABLES)
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_default(value):
        return RegionData()


#######################################################################################################################
# Enumeration Code                                                                                                    #
#######################################################################################################################


@enum_entry_factory(default='DEFAULT', invalid=('DEFAULT', ), method_name='create_enum_entry')
@enum_set_factory(default='DEFAULT', invalid=('DEFAULT', ), method_name='create_enum_set')
class HomeWorldIds(enum.Int, metaclass=DynamicFactoryEnumMetaclass, factory_cls=RegionDataFactory,):
    COMMAND_NAME_BASE = Tunable(tunable_type=str, allow_empty=False, needs_tuning=True, default='')
    DEFAULT = 0

    @cached_classproperty
    def region_to_home_world_mapping(cls):
        return frozendict({home_world.region: home_world for home_world in cls})

    @classmethod
    def get_matching_home_world_from_value(cls, value):
        for world in cls:
            if world.value == value:
                return world

    @classproperty
    def tourist_worlds(cls):
        return frozenset(world for world in cls if world.has_tourists and world.is_available)

    @classproperty
    def worlds_that_support_multiple_streets(cls):
        return frozenset(world for world in cls if world.supports_multiple_creation_streets and world.is_available)

    @classproperty
    def available_worlds(cls):
        return frozenset(world for world in cls if world.is_available and world is not HomeWorldIds.DEFAULT)

    @classproperty
    def world_list(cls):
        return ', '.join(world.name for world in cls.available_worlds)

    @property
    def command_name_base(self):
        return self.COMMAND_NAME_BASE

    @property
    def desc(self):
        return self.name.replace('_', ' ').title()

    @property
    def pretty_name(self) -> str:
        return self.name.lower()

    @property
    def command_name(self):
        return '{}_{}'.format(self.command_name_base, self.pretty_name)

    @property
    def settings_name_base(self):
        return self.desc.replace(' ', '')

    @cached_classproperty
    def max_bit_value(self):
        bit_value = 0
        for world in self:
            bit_value |= world.bit_value

        return bit_value

    def create_lives_in_region_filter(self, minimum_filter_score: float = 0.0, *additional_regions, **overrides):
        from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

        args = dict()
        args['minimum_filter_score'] = minimum_filter_score
        args['region'] = tuple({self.region, *additional_regions})
        args['street_for_creation'] = self.street_for_creation
        args.update(overrides)

        return construct_auto_init_factory(LivesInRegionWithExceptions, **args)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('HomeWorldIds', 'WorldIconSize', 'WorldType', )

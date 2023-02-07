"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the NeighbourhoodStreets enum which maps provides a name to the available streets in the Sims 4
and provides important data, such as the name of the street and the ability to get the underlying Street tuning.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# misc imports
import enum
from interactions.utils.tunable_icon import TunableIconVariant

# sims 4 imports
from sims4.localization import TunableLocalizedStringFactory
from sims4.tuning.tunable import OptionalTunable
from sims4.utils import classproperty

# world imports
from world.street import Street

# local imports
from kuttoe_home_regions.enum import DynamicFactoryEnumMetaclass, EnumItemFactory
from kuttoe_home_regions.utils import *


#######################################################################################################################
# Factory Class Code                                                                                                  #
#######################################################################################################################

class NeighbourhoodStreetsData:
    def __init__(self, street_name=None, icon=None):
        self._street_name = street_name
        self._icon = icon

    @property
    def street_name(self) -> TunableLocalizedStringFactory._Wrapper: return self._street_name

    @property
    def icon(self): return self._icon


@EnumItemFactory.ReprMixin()
class NeighbourhoodStreetsDataFactory(EnumItemFactory):
    FACTORY_TUNABLES = {
        'street_name': TunableLocalizedStringFactory(),
        'icon': OptionalTunable(TunableIconVariant()),
    }
    FACTORY_TYPE = NeighbourhoodStreetsData

    def __init__(self, *args, **kwargs):
        kwargs.update(self.FACTORY_TUNABLES)
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_default(value):
        return NeighbourhoodStreetsData()


#######################################################################################################################
# Enumeration Code                                                                                                    #
#######################################################################################################################

@enum_entry_factory(default='DEFAULT', invalid=('DEFAULT', ), method_name='create_enum_entry')
@enum_set_factory(default='DEFAULT', invalid=('DEFAULT', ), method_name='create_enum_set')
class NeighbourhoodStreets(enum.Int, metaclass=DynamicFactoryEnumMetaclass, factory_cls=NeighbourhoodStreetsDataFactory):
    DEFAULT = 0

    @property
    def street_tuning(self) -> Street:
        return Street.WORLD_DESCRIPTION_TUNING_MAP.get(self.value, None)

    @property
    def street_guid64(self) -> int:
        return getattr(self.street_tuning, 'guid64', None)

    @filtered_cached_classproperty(filter_func=lambda value, **_: value.street_tuning is not None)
    def available_streets(cls): return frozenset(cls)

    @classproperty
    def streets_list(cls):
        return ', '.join(street.name for street in cls.available_streets)

    @property
    def desc(self):
        return self.name.replace('_', ' ').title()

    @property
    def dict_key(self) -> str: return str(self.value)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('NeighbourhoodStreets', )

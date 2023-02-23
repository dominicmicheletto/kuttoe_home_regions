"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details tuning used for icons specific to neighbourhood streets. Icons are inferred by the name of the street
by default, but can also be manually assigned, assigned a pre-made one (such as those used for parks), or assigned one
based off of a specific name over the name of the street's enum value -- in both the default and in this case, the name
is hashed and used to find the resource key of the icon.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# misc imports
import enum
from distributor.shared_messages import IconInfoData
from interactions.utils.tunable_icon import TunableIconVariant

# sims 4 imports
from sims4.resources import get_resource_key, Types
from sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableMapping
from sims4.tuning.tunable import TunableTuple

# local imports
from kuttoe_home_regions.utils import *


#######################################################################################################################
# Helper Enumerations                                                                                                 #
#######################################################################################################################

@enum_entry_factory(default='PARK', invalid=())
class PreMadeIconMapping(enum.Int):
    PARK = 0


#######################################################################################################################
# Factories                                                                                                           #
#######################################################################################################################

class HasherFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'use_high_bit': Tunable(tunable_type=bool, default=True)}

    @staticmethod
    def _from_hash(neighbourhood_street, use_high_bit: bool = True):
        _, key_id = neighbourhood_street.HASH_NAME_BASE(neighbourhood_street)
        if use_high_bit:
            key_id |= 0x8000000000000000  # need to flip the high bit
        resource_key = get_resource_key(key_id, Types.PNG)

        return lambda *_, **__: IconInfoData(icon_resource=resource_key)

    @property
    def is_from_hash(self): return True

    def hasher(self, neighbourhood_street):
        return self._from_hash(neighbourhood_street, use_high_bit=self.use_high_bit)


class SpecificNameHasherFactory(HasherFactory):
    FACTORY_TUNABLES = {'name': Tunable(tunable_type=str, default='')}
    ATTR = 'HASH_NAME_BASE'

    def hasher(self, neighbourhood_street):
        class NewStreetName(str):
            def __new__(cls, value: str, street):
                value = super(NewStreetName, cls).__new__(cls, value)
                value._street = street
                return value

            @property
            def HASH_NAME_BASE(self): return self._street.HASH_NAME_BASE

        return super().hasher(NewStreetName(self.name, neighbourhood_street))


#######################################################################################################################
# Tuning Definitions                                                                                                  #
#######################################################################################################################

class TunableNeighbourhoodIconVariant(TunableVariant):
    IS_FROM_HASH = 'is_from_hash'
    IS_PREMADE = 'is_premade'
    IS_SPECIFIC_NAME = 'is_specific_name'

    @classmethod
    def _make_tunable_tuple(cls, locked_arg: str, **args):
        return TunableTuple(**args, locked_args={locked_arg: True})

    def __init__(self, *args, **kwargs):
        kwargs['locked_args'] = dict(disabled=None)
        kwargs['enabled'] = TunableIconVariant(icon_pack_safe=True)
        kwargs['from_name'] = HasherFactory.TunableFactory()
        kwargs['premade'] = self._make_tunable_tuple(self.IS_PREMADE, icon=PreMadeIconMapping.to_enum_entry())
        kwargs['specific_name'] = SpecificNameHasherFactory.TunableFactory()
        kwargs['default'] = 'from_name'

        super().__init__(*args, **kwargs)

    @classmethod
    def get_icon(cls, neighbourhood_street):
        icon = neighbourhood_street._icon

        if icon is None:
            return None
        elif hasattr(icon, cls.IS_FROM_HASH):
            return icon.hasher(neighbourhood_street)
        elif hasattr(icon, cls.IS_PREMADE):
            return neighbourhood_street.OTHER_ICONS_MAPPING.get(icon.icon, None)
        return icon


class TunablePreMadeIconMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'icon_name'
        kwargs['key_type'] = PreMadeIconMapping.to_enum_entry()
        kwargs['value_name'] = 'icon'
        kwargs['value_type'] = TunableIconVariant()

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('TunablePreMadeIconMapping', 'PreMadeIconMapping', 'TunableNeighbourhoodIconVariant', )

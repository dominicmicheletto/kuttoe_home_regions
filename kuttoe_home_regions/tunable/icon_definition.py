"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details tuning used for icons.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# misc imports
import enum

# sims 4 imports
from sims4.resources import Types, get_resource_key
from sims4.collections import frozendict
from sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunable, OptionalTunable, HasTunableFactory
from sims4.tuning.tunable import AutoFactoryInit, TunableVariant
from sims4.common import Pack
from sims4.hash_util import hash64

# interaction imports
from interactions.utils.tunable_icon import TunableIconVariant, IconInfoData


#######################################################################################################################
# Helper Enumerations                                                                                                 #
#######################################################################################################################

class IconSize(enum.Int):
    SMALL = 32
    MEDIUM = 64
    LARGE = 128


#######################################################################################################################
# Factories                                                                                                           #
#######################################################################################################################

class IconDefinition(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = dict(icon_size=TunableEnumEntry(tunable_type=IconSize, default=IconSize.SMALL))

    def __init__(self, home_world, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._home_world = home_world

    @property
    def home_world(self):
        return self._home_world

    @property
    def resource(self):
        return self.home_world.get_icon(self.icon_size)


#######################################################################################################################
# Tuning Definitions                                                                                                  #
#######################################################################################################################

class IconMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'icon_size'
        kwargs['key_type'] = TunableEnumEntry(tunable_type=IconSize, default=IconSize.SMALL)
        kwargs['value_name'] = 'resource'
        kwargs['value_type'] = TunableIconVariant()

        super().__init__(*args, **kwargs)


class DefaultIconMapping(Tunable):
    class _Wrapper:
        def __init__(self, home_world):
            self._home_world = home_world

        @property
        def pack(self):
            return self._home_world.pack

        @property
        def pack_name(self):
            if self.pack == Pack.BASE_GAME:
                return 'base'
            return self.pack.name

        @property
        def resource_name(self):
            return f'icon_pack_{self.pack_name}'

        def get_resource_for_size(self, size: IconSize):
            key_id = hash64(f'{self.resource_name}_{size.value}')
            resource_key = get_resource_key(key_id, Types.PNG)

            return lambda *_, **__: IconInfoData(icon_resource=resource_key)

        def get_icon_mapping(self):
            return self()

        def __call__(self):
            return frozendict({size: self.get_resource_for_size(size) for size in IconSize})

    def __init__(self, *args, **kwargs):
        kwargs['needs_tuning'] = False
        kwargs['default'] = None

        super().__init__(tunable_type=str, *args, **kwargs)
        self.cache_key = 'TunableDefaultIconMapping'

    def _convert_to_value(self, *_, **__):
        return self._Wrapper


class TunableIconDefinition(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['tunable'] = IconDefinition.TunableFactory()
        kwargs['enabled_name'] = 'use_specific'
        kwargs['disabled_name'] = 'use_default'

        super().__init__(*args, **kwargs)


class TunableIconMappingVariant(TunableVariant):
    def __init__(self, *args, **kwargs):
        kwargs['use_default'] = DefaultIconMapping()
        kwargs['specify'] = IconMapping()
        kwargs['default'] = 'use_default'

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('IconSize', 'IconDefinition', 'TunableIconMappingVariant', 'TunableIconDefinition', )

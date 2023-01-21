"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details helpful resources for packs, such as defining which ones are required and determining what "type"
of pack a specific Pack is.
"""


#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

import enum
from sims4.common import Pack
from sims4.tuning.tunable import OptionalTunable, TunableEnumEntry
from kuttoe_home_regions.utils import cached_classproperty


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


class PackType(enum.Int):
    BASE = ...
    FREE = ...
    STUFF = ...
    GAME = ...
    EXPANSION = ...

    @cached_classproperty
    def _pack_type_mapping(cls):
        return {name[0]: value for (name, value) in cls.items()}

    @classmethod
    def get_pack_type(cls, pack: Pack):
        return cls._pack_type_mapping[pack.name[0]]

    @classmethod
    def get_pack_of_types(cls, *pack_types, invert: bool = False):
        pack_types = set(pack_types)

        def filter_func(pack):
            raw_value = cls.get_pack_type(pack) in pack_types

            return not raw_value if invert else raw_value

        return tuple(pack for pack in Pack.values if filter_func(pack))


#######################################################################################################################
#  Tuning Definitions                                                                                                 #
#######################################################################################################################

class PackDefinition(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['tunable'] = TunableEnumEntry(tunable_type=Pack, default=Pack.BASE_GAME)
        kwargs['disabled_name'] = 'requires_none'
        kwargs['disabled_value'] = Pack.BASE_GAME
        kwargs['enabled_name'] = 'requires_pack'

        super().__init__(*args, **kwargs)


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = ('PackType', 'PackDefinition', )

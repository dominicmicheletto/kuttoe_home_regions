"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details a special variant used for determining the bit value assigned to each region in the HomeWorldIds
enumeration. This is important for the bitset that allows for special Sim exemptions.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims 4 imports
from sims4.tuning.tunable import Tunable, TunableVariant, TunableTuple
from sims4.common import Pack

# local imports
from kuttoe_home_regions.utils import *
from kuttoe_home_regions.tunable.pack_resources import PackType


#######################################################################################################################
# Tuning Declarations                                                                                                 #
#######################################################################################################################

class TunableBitValueVariant(TunableVariant):
    def __init__(self, *args, **kwargs):
        kwargs['specify'] = Tunable(tunable_type=int, default=0)
        kwargs['use_pack_value'] = TunableTuple(locked_args=dict(is_offset=False, value=None))
        kwargs['offset_from_pack_value'] = TunableTuple(locked_args=dict(is_offset=True, value=None))

        super().__init__(*args, **kwargs, default='use_pack_value')

    class _Wrapper:
        __slots__ = ('_value', '_is_offset',)

        @cached_classproperty
        def pack_values(cls): return PackType.get_pack_of_types(PackType.STUFF, invert=True)

        def __init__(self, value: int = 0, is_offset=False):
            self._value = value
            self._is_offset = is_offset

        @classmethod
        def get_pack_value(cls, pack: Pack = Pack.BASE_GAME):
            return cls.pack_values.index(pack)

        def get_value(self, last_value: int = 0, pack: Pack = Pack.BASE_GAME):
            if self.is_manual_value:
                return self._value

            pack_value = self.get_pack_value(pack) * (2 if self._is_offset else 1)
            return last_value + pack_value

        @property
        def value(self): return self._value

        @property
        def is_offset(self): return self._is_offset

        @property
        def is_manual_value(self): return self and not self.is_offset

        def __bool__(self): return self._value is not None

    DEFAULT = _Wrapper(0, False)

    @classmethod
    def resolve_value(cls, value):
        if value is None:
            return cls.DEFAULT
        elif type(value) is int:
            return cls._Wrapper(value, False)
        else:
            return cls._Wrapper(value.value, value.is_offset)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('TunableBitValueVariant', )

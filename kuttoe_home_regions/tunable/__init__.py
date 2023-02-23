"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details tuning elements defined in script.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from collections import namedtuple
from typing import Tuple

# sim4 imports
from sims4 import hash_util
from sims4.tuning.tunable import Tunable


#######################################################################################################################
# Named Tuples                                                                                                        #
#######################################################################################################################

InteractionRegistryData = namedtuple('InteractionRegistryData', [
    'interaction', 'resource_key',
])


#######################################################################################################################
# Interaction Name Tuning                                                                                             #
#######################################################################################################################

class TunableInteractionName(Tunable):
    class _Wrapper:
        @staticmethod
        def _get_hash_for_name(interaction_name_base: str, suffix: str) -> Tuple[str, int]:
            hash_name_template = '{}_{}'.format(interaction_name_base, suffix)

            return hash_name_template, hash_util.hash64(hash_name_template)

        @classmethod
        def _get_hash_for_home_world(cls, interaction_name_base: str, home_world):
            return cls._get_hash_for_name(interaction_name_base, home_world.pretty_name)

        @classmethod
        def _get_hash_for_neighbourhood_street(cls, interaction_name_base: str, neighbourhood_street):
            return cls._get_hash_for_name(interaction_name_base, neighbourhood_street.hash_name)

        __slots__ = ('_interaction_name_base',)

        def __init__(self, interaction_name_base: str) -> None:
            self._interaction_name_base = interaction_name_base

        def __bool__(self) -> bool:
            return self._interaction_name_base is not None

        def __call__(self, value):
            from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
            from kuttoe_home_regions.enum.neighbourhood_streets import NeighbourhoodStreets

            if type(value) is HomeWorldIds:
                func = self._get_hash_for_home_world
            elif type(value) is NeighbourhoodStreets:
                func = self._get_hash_for_neighbourhood_street
            else:
                func = self._get_hash_for_name

            return func(self.interaction_name_base, value)

        def _get_hash_for_suffix(self, suffix: str):
            return self._get_hash_for_name(self.interaction_name_base, suffix)

        @property
        def interaction_name_base(self):
            return self._interaction_name_base

    def __init__(self, *args, **kwargs):
        kwargs['needs_tuning'] = True
        kwargs['default'] = None

        super().__init__(tunable_type=str, *args, **kwargs)
        self.cache_key = 'TunableInteractionName'

    def _convert_to_value(self, interaction_name_base: str):
        if interaction_name_base is None:
            return
        return self._Wrapper(interaction_name_base)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('TunableInteractionName', 'InteractionRegistryData', )

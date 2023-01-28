"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details special filter tuning. This allows for the filters to be generated dynamically so that new worlds
are automatically plugged-in as soon as the HomeWorldIds enum is updated.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# typing imports
from typing import Set

# sims 4 imports
from sims4.tuning.tunable import Tunable, TunableSet
from sims4.collections import frozendict
from sims4.utils import classproperty

# filter imports
from filters.location_based_filter_terms import LocationBasedFilterTerms

# zone modifier imports
from zone_modifier.zone_modifier import ZoneModifier

# misc imports
import snippets

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.utils import does_zone_have_modifiers


#######################################################################################################################
# Filter Tuning                                                                                                       #
#######################################################################################################################

class LocationBasedFilterTermsWithLotTraitExceptions(LocationBasedFilterTerms):
    """
    This is a special tunable filter which allows for lots with specific lot traits being exempt from filter-based
    location filters.
    """

    __slots__ = ('_lot_trait_exceptions', '_num_required', )

    FACTORY_TUNABLES = {
        'lot_trait_exceptions': TunableSet(ZoneModifier.TunablePackSafeReference()),
        'num_required': Tunable(tunable_type=int, default=1)
    }

    def __init__(self, lot_trait_exceptions: Set[ZoneModifier] = frozenset(), num_required: int = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._lot_trait_exceptions = lot_trait_exceptions
        self._num_required = num_required

    @property
    def lot_trait_exceptions(self):
        return self._lot_trait_exceptions

    @property
    def num_required(self):
        return self._num_required

    def is_lot_exempt(self):
        return does_zone_have_modifiers(*self.lot_trait_exceptions, num_required=self.num_required)

    def get_filter_terms(self):
        if self.is_lot_exempt():
            return self.default_filter_terms
        return super().get_filter_terms()


#######################################################################################################################
# Snippet Class Information                                                                                           #
#######################################################################################################################

snippet_name = snippets.SNIPPET_CLASS_NAMES['location_based_filter_terms']
SnippetBase = vars(snippets)[snippet_name]


#######################################################################################################################
# Base Tuning Class                                                                                                   #
#######################################################################################################################

class _DynamicFilterBase(SnippetBase):
    LOT_TRAIT_INSTANCE = ZoneModifier.TunablePackSafeReference()
    INSTANCE_TUNABLES = {
        '_skipped_regions': HomeWorldIds.create_enum_set(optional=True),
    }

    @classmethod
    def soft_filter_value(cls, home_world: HomeWorldIds) -> float:
        from kuttoe_home_regions.settings import Settings

        return Settings.get_world_settings(home_world)[Settings.WorldSettingNames.SOFT_FILTER_VALUE]

    @classmethod
    def _get_region_list(cls, home_world: HomeWorldIds):
        return {home_world.region}

    @classmethod
    def _create_filter_term(cls, home_world: HomeWorldIds, minimum_filter_score: float = 0.0):
        return home_world.create_lives_in_region_filter(minimum_filter_score, *cls._get_region_list(home_world))

    @classmethod
    def _generate_value(cls):
        return dict()

    @classproperty
    def skipped_regions(cls):
        if not cls._skipped_regions:
            return frozenset()
        else:
            return frozenset(world.region for world in cls._skipped_regions)

    @classmethod
    def is_region_skipped(cls, region):
        return region in cls.skipped_regions

    @classmethod
    def get_filtered_value(cls):
        return {key: value for (key, value) in cls._generate_value().items() if not cls.is_region_skipped(key)}

    @staticmethod
    def _merge_filter_lists(old_list: LocationBasedFilterTermsWithLotTraitExceptions, new_list: dict):
        terms = dict(old_list.region_to_filter_terms)

        for (region, filter_term) in new_list.items():
            new_terms = {filter_term}
            new_terms.update(terms.get(region, tuple()))
            terms[region] = tuple(new_terms)

        args = dict()
        args['default_filter_terms'] = old_list.default_filter_terms
        args['region_to_filter_terms'] = frozendict(terms)
        args['lot_trait_exceptions'] = frozenset({old_list.LOT_TRAIT_INSTANCE})
        args['num_required'] = 1

        return LocationBasedFilterTermsWithLotTraitExceptions(**args)

    @classmethod
    def _tuning_loaded_callback(cls):
        cls.value = cls._merge_filter_lists(cls, cls.get_filtered_value())


#######################################################################################################################
# Tuning Classes                                                                                                      #
#######################################################################################################################

class SoftTunableLocationBasedFilterTermsSnippet(_DynamicFilterBase):
    @classmethod
    def _generate_value(cls):
        return {
            world.region: cls._create_filter_term(world, cls.soft_filter_value(world))
            for world
            in HomeWorldIds.available_worlds
        }


class DynamicTunableLocationBasedFilterTermsSnippet(_DynamicFilterBase):
    @classmethod
    def _get_settings_data(cls, home_world: HomeWorldIds):
        from kuttoe_home_regions.settings import Settings

        return Settings.get_world_settings(home_world)

    @classmethod
    def has_soft_filter(cls, home_world: HomeWorldIds) -> bool:
        return cls._get_settings_data(home_world)['Soft']

    @classmethod
    def get_worlds_list(cls, home_world: HomeWorldIds) -> set:
        return {HomeWorldIds[region].region for region in cls._get_settings_data(home_world)['Worlds']}

    @classmethod
    def _get_region_list(cls, home_world: HomeWorldIds):
        return super()._get_region_list(home_world).union(cls.get_worlds_list(home_world))

    @classmethod
    def _get_soft_filter_value(cls, home_world: HomeWorldIds):
        return cls.soft_filter_value(home_world) if cls.has_soft_filter(home_world) else 0.0

    @classmethod
    def _generate_value(cls):
        return {
            world.region: cls._create_filter_term(world, cls._get_soft_filter_value(world))
            for world
            in HomeWorldIds.available_worlds
        }


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = (
    'SoftTunableLocationBasedFilterTermsSnippet', 'DynamicTunableLocationBasedFilterTermsSnippet',
    'LocationBasedFilterTermsWithLotTraitExceptions'
)

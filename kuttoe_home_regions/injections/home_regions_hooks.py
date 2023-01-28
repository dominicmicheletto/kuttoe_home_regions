"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file allows for snippets that can be used to "hook into" the Home Regions filters. This both allows for mods to
add support for themselves, and for parts of the long lists of SituationJobs and Filters to be splintered off into
smaller bites.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableSet, TunableMapping
from sims4.repr_utils import standard_repr

# situations imports
from situations.situation_job import SituationJob

# filter imports
from filters.tunable import TunableSimFilter

# miscellaneous imports
import enum

# local imports
from kuttoe_home_regions.injections.situation_job_filters import BypassListType
from kuttoe_home_regions.tunable.searchable_whitelist_blacklist import TunableSearchableWhiteBlackList
from kuttoe_home_regions.utils import SnippetMixin, filtered_cached_property, cached_property


#######################################################################################################################
# Enumerations                                                                                                        #
#######################################################################################################################

class ListType(enum.Int):
    SOFT_LIST = ...
    BYPASS_LIST = ...
    SECOND_CHANCE_LIST = ...
    FILTERS_TO_BYPASS = ...

    @property
    def prop_name(self): return self.name.lower()

    def get_list(self, tunable): return getattr(tunable, self.prop_name, frozenset())


#######################################################################################################################
# Tuning                                                                                                              #
#######################################################################################################################

class JobsSearchListMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'list_type'
        kwargs['key_type'] = BypassListType.to_enum_entry(invalid=())
        kwargs['value_name'] = 'search_list'
        kwargs['value_type'] = TunableSearchableWhiteBlackList()

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Factories                                                                                                           #
#######################################################################################################################

class TunableHomeRegionInjectionHook(
    HasTunableSingletonFactory, AutoFactoryInit,
    SnippetMixin, snippet_name='home_region_injection_hook'
):
    __slots__ = ('_soft_list', '_bypass_list', '_second_chance_list', '_filters_to_bypass', 'jobs_search')

    FACTORY_TUNABLES = {
        'soft_list': TunableSet(tunable=SituationJob.TunablePackSafeReference()),
        'bypass_list': TunableSet(tunable=SituationJob.TunablePackSafeReference()),
        'second_chance_list': TunableSet(tunable=SituationJob.TunablePackSafeReference()),
        'filters_to_bypass': TunableSet(tunable=TunableSimFilter.TunablePackSafeReference()),
        'jobs_search': JobsSearchListMapping(),
    }

    def __init__(self, soft_list, bypass_list, second_chance_list, filters_to_bypass, jobs_search, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._soft_list: frozenset = soft_list
        self._bypass_list: frozenset = bypass_list
        self._second_chance_list: frozenset = second_chance_list
        self._filters_to_bypass: frozenset = filters_to_bypass
        self.jobs_search = jobs_search

    def _get_matched_situations(self, list_type: BypassListType):
        if list_type in self.jobs_search:
            return self.jobs_search.get(list_type).matched_situation_jobs
        return set()

    @filtered_cached_property(filter_func=lambda value, **_: value is not None)
    def soft_list(self): return self._soft_list | self._get_matched_situations(BypassListType.SOFT)

    @filtered_cached_property(filter_func=lambda value, **_: value is not None)
    def bypass_list(self): return self._bypass_list | self._get_matched_situations(BypassListType.GLOBAL)

    @filtered_cached_property(filter_func=lambda value, **_: value is not None)
    def second_chance_list(self): return self._second_chance_list | self._get_matched_situations(BypassListType.NONE)

    @filtered_cached_property(filter_func=lambda value, **_: value is not None)
    def filters_to_bypass(self): return self._filters_to_bypass

    @cached_property
    def has_values(self):
        return any((self.soft_list, self.bypass_list, self.second_chance_list, self.filters_to_bypass, ))

    def __bool__(self): return self.has_values

    def __repr__(self):
        args = {list_value.prop_name: list_value.get_list(self) for list_value in ListType}
        return standard_repr(self, **args)

    def __len__(self): return sum(len(list_value.get_list(self)) for list_value in ListType)

    @staticmethod
    def update_from_list(list_type: ListType, *values):
        aggregated_values = set()

        for value in values:
            if not value.has_values:
                continue
            aggregated_values.update(list_type.get_list(value))

        return aggregated_values


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

(
    TunableHomeRegionInjectionHookSnippetReference, TunableHomeRegionInjectionHookSnippet
) = TunableHomeRegionInjectionHook._snippet

__all__ = (
   'TunableHomeRegionInjectionHook',
   'TunableHomeRegionInjectionHookSnippetReference', 'TunableHomeRegionInjectionHookSnippet',
   'ListType',
)

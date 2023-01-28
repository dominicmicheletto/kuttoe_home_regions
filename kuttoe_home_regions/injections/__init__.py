"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details and performs the primary injections that are responsible for the mod to function. This does NOT
include the code that creates the UI.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from collections import defaultdict

# sims4 imports
from sims4.utils import classproperty
from sims4.resources import Types
from sims4.tuning.instance_manager import InstanceManager
from sims4.collections import frozendict
from sims4.tuning.tunable import TunableSet, TunableMapping, TunablePackSafeReference, TunableEnumEntry, Tunable
from sims4.tuning.tunable import TunableVariant, HasTunableFactory, AutoFactoryInit, TunableList, OptionalTunable
from sims4.tuning.tunable import TunableTuple

# venue imports
from venues.npc_summoning import ResidentialLotArrivalBehavior, CreateAndAddToSituation, AddToBackgroundSituation
from venues.npc_summoning import NotfifyZoneDirector
from venues.venue_constants import NPCSummoningPurpose

# situations imports
from situations.situation_job import SituationJob

# filter imports
from filters.tunable import LivesInRegion, TunableSimFilter, FilterTermTag, TunableAggregateFilter
from filters.location_based_filter_terms import TunableLocationBasedFilterTermsSnippet

# miscellaneous
from tag import TunableTags
import enum
from sims.sim_info_types import Species
from services import get_instance_manager

# local imports
from kuttoe_home_regions.utils import *
from kuttoe_home_regions.injections.situation_job_filters import *
from kuttoe_home_regions.injections.situation_filter_replacement import *
from kuttoe_home_regions.injections.home_regions_hooks import TunableHomeRegionInjectionHook, ListType


#######################################################################################################################
# Venue Modifications                                                                                                 #
#######################################################################################################################

class InviteOverVariant(TunableVariant):
    def __init__(self, *args, **kwargs):
        kwargs['residential'] = ResidentialLotArrivalBehavior.TunableFactory()
        kwargs['create_situation'] = CreateAndAddToSituation.TunableFactory()
        kwargs['add_to_background_situation'] = AddToBackgroundSituation.TunableFactory()
        kwargs['notify_zone_director'] = NotfifyZoneDirector.TunableFactory()
        kwargs['locked_args'] = dict(disabled=None)
        kwargs['default'] = 'disabled'

        super().__init__(*args, **kwargs)


class TunableInviteOverOverridesMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_type'] = TunableEnumEntry(tunable_type=Species, default=Species.HUMAN,
                                              invalid_enums=(Species.INVALID,))
        kwargs['value_type'] = InviteOverVariant()

        super().__init__(*args, **kwargs)


class VenueModifications:
    VENUES_LIST = TunableSet(tunable=TunablePackSafeReference(manager=get_instance_manager(Types.VENUE)))
    INVITE_OVER_OVERRIDES = TunableInviteOverOverridesMapping()

    @cached_classproperty
    def venues(cls):
        return {venue for venue in cls.VENUES_LIST if venue is not None}

    @classmethod
    def _modify_venues(cls, _manager):
        for venue in cls.venues:
            npc_summoning_behaviour = dict(venue.npc_summoning_behavior)
            npc_summoning_behaviour[NPCSummoningPurpose.Invite_Over] = cls.INVITE_OVER_OVERRIDES
            venue.npc_summoning_behavior = frozendict(npc_summoning_behaviour)


#######################################################################################################################
# Situation Job Modifications                                                                                         #
#######################################################################################################################

class SituationJobModifications:
    TEMPLATE = TunableSituationJobsTemplateSnippet()
    SOFT_FILTER = TunableLocationBasedFilterTermsSnippet(pack_safe=True)
    MAIN_FILTER = TunableLocationBasedFilterTermsSnippet(pack_safe=True)
    SOFT_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    BYPASS_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    SECOND_CHANCE_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    FORCED_REPLACEMENT_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    SITUATION_FILTER_FIXUP = TunableSituationFilterReplacementSnippet()
    FILTER_REPLACEMENT_LIST = TunableSituationFilterReplacementSnippet()
    FILTERS_TO_BYPASS = TunableSet(tunable=TunableSimFilter.TunablePackSafeReference())
    BYPASS_TAGS = TunableTags(filter_prefixes=['situation'], pack_safe=True)
    HIGH_SCHOOL_SITUATION_JOBS_INFO = TunableSituationJobsFilterSnippet()
    TOURISTS_SITUATION_JOBS_INFO = TunableTouristsJobsFilterSnippet()

    _BYPASSED_JOBS = set()
    _HOOKS = tuple()

    @classmethod
    def _load_all_hooks(cls):
        cls._HOOKS = TunableHomeRegionInjectionHook.get_registered_snippets()

    @classproperty
    def _has_tourists_info(cls): return cls.TOURISTS_SITUATION_JOBS_INFO is not None

    @conditional_cached_classproperty(condition=lambda cls: cls._has_tourists_info, fallback=frozendict())
    def tourists_situations(cls):
        situations = defaultdict(list)

        for situation_jobs_info in cls.TOURISTS_SITUATION_JOBS_INFO:
            if situation_jobs_info.is_world_based:
                situations[situation_jobs_info.setting_value.world].append(situation_jobs_info())

        return frozendict({key: tuple(value) for (key, value) in situations.items()})

    @classproperty
    def _has_high_school_info(cls): return cls.HIGH_SCHOOL_SITUATION_JOBS_INFO is not None

    @conditional_cached_classproperty(condition=lambda cls: cls._has_high_school_info, fallback=SituationFilterResult())
    def high_school_situations(cls):
        return cls.HIGH_SCHOOL_SITUATION_JOBS_INFO.value()

    @cached_classproperty
    def filters_to_bypass(cls):
        primary_list = {tunable_filter for tunable_filter in cls.FILTERS_TO_BYPASS}
        primary_list.update(TunableHomeRegionInjectionHook.update_from_list(ListType.FILTERS_TO_BYPASS, *cls._HOOKS))

        return primary_list

    @cached_classproperty
    def soft_list(cls):
        primary_list = {situation_job for situation_job in cls.SOFT_LIST if situation_job is not None}
        primary_list.update(cls.high_school_situations.soft_)
        primary_list.update(TunableHomeRegionInjectionHook.update_from_list(ListType.SOFT_LIST, *cls._HOOKS))

        for (world, values) in cls.tourists_situations.items():
            if not world.has_tourists:
                continue

            for value in values:
                primary_list.update(value.soft_)

        return primary_list

    @cached_classproperty
    def bypass_list(cls):
        primary_list = {situation_job for situation_job in cls.BYPASS_LIST if situation_job is not None}
        primary_list.update(cls.high_school_situations.global_)
        primary_list.update(TunableHomeRegionInjectionHook.update_from_list(ListType.BYPASS_LIST, *cls._HOOKS))

        for (world, values) in cls.tourists_situations.items():
            if not world.has_tourists:
                continue

            for value in values:
                primary_list.update(value.global_)

        return primary_list

    @cached_classproperty
    def second_chance_list(cls):
        primary_list = {situation_job for situation_job in cls.SECOND_CHANCE_LIST if situation_job is not None}
        primary_list.update(TunableHomeRegionInjectionHook.update_from_list(ListType.SECOND_CHANCE_LIST, *cls._HOOKS))

        return primary_list

    @filtered_cached_classproperty(filter_func=lambda value, **_: value is not None)
    def forced_replacement_list(cls): return cls.FORCED_REPLACEMENT_LIST

    @classmethod
    def _verify_filter_existence(cls):
        if not all([cls.MAIN_FILTER, cls.SOFT_FILTER]):
            sim_filter = cls.MAIN_FILTER if cls.MAIN_FILTER is None else cls.SOFT_FILTER

            raise AttributeError('Dependent SimFilter tuning unexpectedly None: {}'.format(sim_filter))

    @classmethod
    def _inject_soft_filter(cls):
        for situation in cls.soft_list:
            situation.location_based_filter_terms += (cls.SOFT_FILTER,)

    @classmethod
    def _inject_force_replacement(cls):
        factory = getattr(cls.TEMPLATE, 'value', None)
        if not factory:
            return

        for situation in cls.forced_replacement_list:
            factory(situation).replace_tunables('no_show_action')

    @classmethod
    def _replace_filters(cls): getattr(cls.FILTER_REPLACEMENT_LIST, 'value', lambda: None)()

    @classmethod
    def _fixup_filters_for_situation_jobs(cls): getattr(cls.SITUATION_FILTER_FIXUP, 'value', lambda: None)()

    @classmethod
    def _add_jobs_to_bypass_list(cls, situation):
        phases = getattr(situation, '_phases', tuple())

        for phase in phases:
            jobs = phase._job_list.keys()
            cls._BYPASSED_JOBS.update(job for job in jobs if job is not None and job not in cls.second_chance_list)

    @classmethod
    def check_situation(cls, situation):
        tags = getattr(situation, 'tags', set())
        should_bypass = list()

        should_bypass.append(situation.force_invite_only or situation._implies_greeted_status)
        should_bypass.append(tags & cls.BYPASS_TAGS)

        if any(should_bypass):
            cls._add_jobs_to_bypass_list(situation)

    @classmethod
    def _inject_into_situation_jobs(cls):
        cls._BYPASSED_JOBS.update(cls.bypass_list, cls.soft_list)

        situation_manager: InstanceManager = get_instance_manager(Types.SITUATION)
        for situation in situation_manager.get_ordered_types():
            cls.check_situation(situation)

        situation_jobs_manager: InstanceManager = get_instance_manager(Types.SITUATION_JOB)
        for situation_job in situation_jobs_manager.get_ordered_types():
            if not hasattr(situation_job, 'location_based_filter_terms'):
                continue

            if situation_job not in cls._BYPASSED_JOBS and situation_job.filter not in cls.filters_to_bypass:
                situation_job.location_based_filter_terms += (cls.MAIN_FILTER,)

    @classmethod
    def _do_injections(cls, _manager):
        cls._verify_filter_existence()
        cls._load_all_hooks()
        cls._inject_soft_filter()
        cls._inject_force_replacement()
        cls._replace_filters()
        cls._fixup_filters_for_situation_jobs()
        cls._inject_into_situation_jobs()


#######################################################################################################################
# Filter Modifications                                                                                                #
#######################################################################################################################

class ReplacementPolicy(enum.Int):
    COMBINE = 0
    REPLACE = 1


class TunableReplacementPolicy(TunableEnumEntry):
    def __init__(self, invalid_enums=tuple(), default=ReplacementPolicy.COMBINE, *args, **kwargs):
        super().__init__(tunable_type=ReplacementPolicy, invalid_enums=invalid_enums, default=default, *args, **kwargs)


class TunableFilterList(TunableList):
    @classmethod
    def make_tunable(cls, optional=True):
        kwargs = dict()

        kwargs['filter'] = TunableSimFilter.TunablePackSafeReference(allow_none=False)
        kwargs['tag'] = TunableEnumEntry(tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG)

        if optional:
            kwargs['optional'] = Tunable(tunable_type=bool, default=True)

        return TunableTuple(**kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(tunable=self.make_tunable(optional=True), *args, **kwargs)


class AggregateFilterOverrides(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'filters': TunableTuple(replacement_policy=TunableReplacementPolicy(), filters_list=TunableFilterList()),
        'leader_filter': OptionalTunable(enabled_name='override', disabled_name='do_not_override',
                                         tunable=TunableFilterList.make_tunable(optional=False))
    }

    __slots__ = ('_sim_filter', )

    def __init__(self, sim_filter, *args, **kwargs):
        self._sim_filter = sim_filter

        super().__init__(*args, **kwargs)

    @property
    def sim_filter(self): return self._sim_filter

    @property
    def replacement_policy(self) -> ReplacementPolicy: return self.filters.replacement_policy

    def __bool__(self): return self._sim_filter is not None

    def __call__(self):
        if not self:
            return False

        filters = list()
        if self.replacement_policy == ReplacementPolicy.COMBINE:
            filters.extend(self.sim_filter.filters)
        filters.extend(self.filters.filters_list)
        self.sim_filter.filters = tuple(filters)

        if self.leader_filter:
            self.sim_filter.leader_filter = self.leader_filter

        return True


class TunableAggregateFilterOverrides(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'filter'
        kwargs['key_type'] = TunableAggregateFilter.TunablePackSafeReference()
        kwargs['value_name'] = 'overrides'
        kwargs['value_type'] = AggregateFilterOverrides.TunableFactory()

        super().__init__(*args, **kwargs)


class FilterModifications:
    ADD_REGION_TEST_LIST = TunableSet(tunable=TunableSimFilter.TunablePackSafeReference())
    AGGREGATE_FILTER_OVERRIDES = TunableAggregateFilterOverrides()

    @classproperty
    def lives_in_region_test(cls):
        return LivesInRegion(force_filter_term=True, invert_score=False, minimum_filter_score=0.0, region=None,
                             street_for_creation=None)

    @filtered_cached_classproperty(filter_func=lambda value, **_: value is not None)
    def add_region_filters_list(cls): return cls.ADD_REGION_TEST_LIST

    @classmethod
    def _inject_into_filters(cls, _manager):
        for (sim_filter, overrides) in cls.AGGREGATE_FILTER_OVERRIDES.items():
            overrides(sim_filter)()
        for sim_filter in cls.add_region_filters_list:
            sim_filter._filter_terms += (cls.lives_in_region_test, )


#######################################################################################################################
# Injection Registration                                                                                              #
#######################################################################################################################

@on_load_complete(Types.SNIPPET, safe=False)
def _register_all_injections(snippet_manager):
    VenueModifications._modify_venues(snippet_manager)
    SituationJobModifications._do_injections(snippet_manager)
    FilterModifications._inject_into_filters(snippet_manager)


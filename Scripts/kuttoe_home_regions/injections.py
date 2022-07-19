#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.utils import classproperty
from sims4.resources import Types
from sims4.tuning.instance_manager import InstanceManager
from sims4.collections import frozendict
from sims4.tuning.tunable import TunableSet, TunableMapping, TunablePackSafeReference, TunableEnumEntry
from sims4.tuning.tunable import TunableVariant, HasTunableFactory, AutoFactoryInit, TunableInterval, TunableList
from sims4.tuning.tunable import TunableEnumWithFilter, TunableTuple, Tunable, OptionalTunable

# venue imports
from venues.npc_summoning import ResidentialLotArrivalBehavior, CreateAndAddToSituation, AddToBackgroundSituation,\
    NotfifyZoneDirector
from venues.venue_constants import NPCSummoningPurpose

# situations imports
from situations.situation_types import JobHolderNoShowAction
from situations.situation_job import SituationJob

# filter imports
from filters.tunable import LivesInRegion, TunableSimFilter, FilterTermTag, TunableAggregateFilter
from filters.location_based_filter_terms import TunableLocationBasedFilterTermsSnippet

# miscellaneous
from tag import Tag
import enum
from sims.sim_info_types import Species
from services import get_instance_manager
from singletons import DEFAULT

# local imports
from kuttoe_home_regions.utils import on_load_complete


#######################################################################################################################
#  Venue Modifications                                                                                                #
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

    @classproperty
    def venues(cls):
        return {venue for venue in cls.VENUES_LIST if venue is not None}

    @staticmethod
    @on_load_complete(Types.TUNING, safe=False)
    def _modify_venues(tuning_manager):
        cls = VenueModifications

        for venue in cls.venues:
            npc_summoning_behaviour = dict(venue.npc_summoning_behavior)
            npc_summoning_behaviour[NPCSummoningPurpose.Invite_Over] = cls.INVITE_OVER_OVERRIDES
            venue.npc_summoning_behavior = frozendict(npc_summoning_behaviour)


#######################################################################################################################
#  Situation Job Modifications                                                                                        #
#######################################################################################################################


class SituationJobTemplate(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'no_show_action': TunableEnumEntry(tunable_type=JobHolderNoShowAction,
                                           default=JobHolderNoShowAction.DO_NOTHING),
        'sim_auto_invite': TunableInterval(tunable_type=int, default_lower=0, minimum=0, default_upper=0),
        'location_based_filter_terms': TunableList(tunable=TunableLocationBasedFilterTermsSnippet(pack_safe=True))
    }

    def __init__(self, _situation_job: SituationJob, *args, **kwargs):
        self._situation_job = _situation_job
        super().__init__(*args, **kwargs)

    @property
    def situation_job(self):
        return self._situation_job

    def __bool__(self):
        return self._situation_job is not None

    def replace_tunables(self, tunables=DEFAULT):
        if not self:
            return

        tunables = (tunables, ) if isinstance(tunables, str) else tunables
        props_list = list(self.FACTORY_TUNABLES.keys()) if tunables is DEFAULT else tunables
        for prop in props_list:
            setattr(self._situation_job, prop, getattr(self, prop))


class FilterToSituationJobMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'new_filter'
        kwargs['key_type'] = TunablePackSafeReference(manager=get_instance_manager(Types.SIM_FILTER), deferred=True)
        kwargs['value_name'] = 'situation_jobs'
        kwargs['value_type'] = TunableList(tunable=SituationJob.TunablePackSafeReference(deferred=True))

        super().__init__(*args, **kwargs)


class SituationJobModifications:
    TEMPLATE = SituationJobTemplate.TunableFactory()
    SOFT_FILTER = TunableLocationBasedFilterTermsSnippet(pack_safe=True)
    MAIN_FILTER = TunableLocationBasedFilterTermsSnippet(pack_safe=True)
    SOFT_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    BYPASS_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    SECOND_CHANCE_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    FORCED_REPLACEMENT_LIST = TunableSet(tunable=SituationJob.TunablePackSafeReference())
    SITUATION_FILTER_FIXUP = FilterToSituationJobMapping()
    FILTER_REPLACEMENT_LIST = FilterToSituationJobMapping()
    FILTERS_TO_BYPASS = TunableList(tunable=TunableSimFilter.TunablePackSafeReference())
    BYPASS_TAGS = TunableSet(tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['situation'],
                                                           default=Tag.INVALID, pack_safe=True))
    _BYPASSED_JOBS = set()

    @classproperty
    def soft_list(cls):
        return {situation_job for situation_job in cls.SOFT_LIST if situation_job is not None}

    @classproperty
    def bypass_list(cls):
        return {situation_job for situation_job in cls.BYPASS_LIST if situation_job is not None}

    @classproperty
    def second_chance_list(cls):
        return {situation_job for situation_job in cls.SECOND_CHANCE_LIST if situation_job is not None}

    @classproperty
    def forced_replacement_list(cls):
        return {situation_job for situation_job in cls.FORCED_REPLACEMENT_LIST if situation_job is not None}

    @classproperty
    def bypassed_situations(cls):
        return cls.soft_list | cls.bypass_list

    @classmethod
    def _inject_soft_filter(cls):
        for situation in cls.soft_list:
            situation.location_based_filter_terms += (cls.SOFT_FILTER, )

    @classmethod
    def _inject_force_replacement(cls):
        for situation in cls.forced_replacement_list:
            cls.TEMPLATE(situation).replace_tunables('no_show_action')

    @classmethod
    def _replace_filters(cls):
        for (new_filter, situation_jobs) in cls.FILTER_REPLACEMENT_LIST.items():
            if not new_filter:
                continue

            for situation in situation_jobs:
                if situation:
                    situation.filter = new_filter

    @classmethod
    def _fixup_filters_for_situation_jobs(cls):
        for (new_filter, situation_jobs) in cls.SITUATION_FILTER_FIXUP.items():
            if not new_filter:
                continue

            for situation_job in situation_jobs:
                if not situation_job:
                    continue

                cls.TEMPLATE(situation_job).replace_tunables()
                situation_job.filter = new_filter

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
        cls._BYPASSED_JOBS.update(cls.bypass_list)

        situation_manager: InstanceManager = get_instance_manager(Types.SITUATION)
        for situation in situation_manager.get_ordered_types():
            cls.check_situation(situation)

        situation_jobs_manager: InstanceManager = get_instance_manager(Types.SITUATION_JOB)
        for situation_job in situation_jobs_manager.get_ordered_types():
            if not hasattr(situation_job, 'location_based_filter_terms'):
                continue

            if situation_job not in cls._BYPASSED_JOBS and situation_job.filter not in cls.FILTERS_TO_BYPASS:
                situation_job.location_based_filter_terms += (cls.MAIN_FILTER, )

    @staticmethod
    @on_load_complete(Types.TUNING, safe=False)
    def _do_injections(tuning_manager):
        cls = SituationJobModifications

        if not all([cls.MAIN_FILTER, cls.SOFT_FILTER]):
            sim_filter = cls.MAIN_FILTER if cls.MAIN_FILTER is None else cls.SOFT_FILTER
            raise AttributeError('Dependent SimFilter tuning unexpectedly None: {}'.format(sim_filter))

        cls._inject_soft_filter()
        cls._inject_force_replacement()
        cls._replace_filters()
        cls._fixup_filters_for_situation_jobs()
        cls._inject_into_situation_jobs()


#######################################################################################################################
#  Filter Modifications                                                                                               #
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

    def __init__(self, sim_filter, *args, **kwargs):
        self._sim_filter = sim_filter

        super().__init__(*args, **kwargs)

    @property
    def sim_filter(self):
        return self._sim_filter

    @property
    def replacement_policy(self) -> ReplacementPolicy:
        return self.filters.replacement_policy

    def __bool__(self):
        return self._sim_filter is not None

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

    @classproperty
    def add_region_filters_list(cls):
        return {sim_filter for sim_filter in cls.ADD_REGION_TEST_LIST if sim_filter is not None}

    @staticmethod
    @on_load_complete(Types.TUNING, safe=False)
    def _inject_into_filters(tuning_manager):
        cls = FilterModifications

        for (sim_filter, overrides) in cls.AGGREGATE_FILTER_OVERRIDES.items():
            overrides(sim_filter)()
        for sim_filter in cls.add_region_filters_list:
            sim_filter._filter_terms += (cls.lives_in_region_test, )

"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details tuning used to create a template situation job and tuning used for selectively replacing the
filters that appear in a situation job. Both are exported as snippets for convenience.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims 4 imports
from sims4.resources import Types
from sims4.tuning.tunable import HasTunableFactory, HasTunableSingletonFactory, AutoFactoryInit
from sims4.tuning.tunable import TunableEnumEntry, TunableList, TunableInterval
from sims4.tuning.tunable import TunableMapping, TunablePackSafeReference, OptionalTunable

# filter imports
from filters.location_based_filter_terms import TunableLocationBasedFilterTermsSnippet


# situations imports
from situations.situation_types import JobHolderNoShowAction
from situations.situation_job import SituationJob

# miscellaneous
from singletons import DEFAULT
from services import get_instance_manager


# local imports
from kuttoe_home_regions.utils import filtered_cached_property, SnippetMixin


#######################################################################################################################
# Situation Job Template Factory                                                                                      #
#######################################################################################################################

class SituationJobTemplate(
    HasTunableFactory, AutoFactoryInit, SnippetMixin,
    snippet_name='situation_job_template',
):
    FACTORY_TUNABLES = {
        'no_show_action': TunableEnumEntry(tunable_type=JobHolderNoShowAction,
                                           default=JobHolderNoShowAction.DO_NOTHING),
        'sim_auto_invite': TunableInterval(tunable_type=int, default_lower=0, minimum=0, default_upper=0),
        'location_based_filter_terms': TunableList(tunable=TunableLocationBasedFilterTermsSnippet(pack_safe=True))
    }

    __slots__ = ('_situation_job', )

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


#######################################################################################################################
# Situation Filter Replacement Factory                                                                                #
#######################################################################################################################

class FilterToSituationJobMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'new_filter'
        kwargs['key_type'] = TunablePackSafeReference(manager=get_instance_manager(Types.SIM_FILTER), deferred=True)
        kwargs['value_name'] = 'situation_jobs'
        kwargs['value_type'] = TunableList(tunable=SituationJob.TunablePackSafeReference(deferred=True))

        super().__init__(*args, **kwargs)


class TunableSituationTemplateVariant(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['enabled_name'] = 'use_template'
        kwargs['disabled_name'] = 'no_template'

        super().__init__(tunable=SituationJobTemplate.SnippetVariant(), *args, **kwargs)


class SituationFilterReplacement(
    HasTunableSingletonFactory, AutoFactoryInit, SnippetMixin,
    snippet_name='situation_filter_replacement',
):
    FACTORY_TUNABLES = {
        'filter_replacements': FilterToSituationJobMapping(),
        'template': TunableSituationTemplateVariant(),
    }

    @filtered_cached_property(filter_func=lambda value, **_: value is not None, iterable_type=frozenset)
    def filters(self): return self.filter_replacements.keys()

    @property
    def has_template(self): return self.template is not None

    def get_situations_jobs_for_filter(self, tunable_filter):
        unfiltered_situation_jobs = self.filter_replacements.get(tunable_filter, frozenset())

        return frozenset(situation_job for situation_job in unfiltered_situation_jobs if situation_job is not None)

    def __call__(self):
        for tunable_filter in self.filters:
            for situation_job in self.get_situations_jobs_for_filter(tunable_filter):
                if self.has_template:
                    self.template(situation_job).replace_tunables()

                situation_job.filter = tunable_filter


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

(TunableSituationJobsTemplateSnippetReference, TunableSituationJobsTemplateSnippet) = SituationJobTemplate._snippet
(
    TunableSituationFilterReplacementSnippetReference, TunableSituationFilterReplacementSnippet
) = SituationFilterReplacement._snippet

__all__ = (
    'TunableSituationJobsTemplateSnippetReference', 'TunableSituationJobsTemplateSnippet',
    'TunableSituationFilterReplacementSnippetReference', 'TunableSituationFilterReplacementSnippet',
)

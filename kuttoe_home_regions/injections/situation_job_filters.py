"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details a special tunable snippet that is used for filtering out situation jobs based on "prefixes"
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from typing import NamedTuple, Dict
from collections import defaultdict

# sims 4 imports
from sims4.utils import classproperty, staticproperty
from sims4.resources import Types
from sims4.tuning.tunable import Tunable, TunableSet, TunableVariant, TunableMapping
from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit

# situation imports
from situations.situation_job import SituationJob

# miscellaneous
import enum
from tag import TunableTags

# local imports
from kuttoe_home_regions.utils import *
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.tunable.searchable_whitelist_blacklist import TunableSearchableWhiteBlackList


#######################################################################################################################
# Enumerations                                                                                                        #
#######################################################################################################################

@enum_entry_factory(default='GLOBAL', invalid=('NONE', ))
class BypassListType(enum.Int):
    NONE = 0
    GLOBAL = 1
    SOFT = 2


#######################################################################################################################
# Situation Filter Result class                                                                                       #
#######################################################################################################################

class SituationFilterResult(NamedTuple):
    soft_: set = set()
    global_: set = set()

    def difference(self, situations: set):
        return type(self)(soft_=self.soft_.difference(situations), global_=self.global_.difference(situations))

    def __iadd__(self, other):
        return type(self)(soft_=self.soft_ | other.soft_, global_=self.global_ | other.global_)

    def update(self, situations: set, list_type: BypassListType = BypassListType.GLOBAL):
        def make_set(base_type: BypassListType):
            base_set = self.soft_ if base_type is BypassListType.SOFT else self.global_

            return base_set | situations if list_type in (base_type, BypassListType.NONE) else base_set

        soft_ = make_set(BypassListType.SOFT)
        global_ = make_set(BypassListType.GLOBAL)
        return type(self)(soft_=soft_, global_=global_)

    def soft_bypass(self, situations: set):
        return self.soft_ | situations

    def global_bypass(self, situations: set):
        return self.global_ | situations


#######################################################################################################################
# Tuning                                                                                                              #
#######################################################################################################################

class SituationBypassMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'job'
        kwargs['key_type'] = SituationJob.TunablePackSafeReference()
        kwargs['value_name'] = 'bypass_list'
        kwargs['value_type'] = BypassListType.to_enum_entry(invalid=())

        super().__init__(*args, **kwargs)


class TunableSettingValueVariant(TunableVariant):
    class _SettingValueFactoryBase(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = dict(key=Tunable(tunable_type=str, default=None, allow_empty=False))

        @staticproperty
        def is_world_based(): return False

        @classproperty
        def settings(cls):
            from kuttoe_home_regions.settings import Settings

            return Settings

        def get_setting_value(self) -> bool:
            return self.settings.settings.get(self.key)

        def __call__(self):
            return self.get_setting_value()

        def __repr__(self):
            return f'{super().__repr__()}[{self()}]'

    class _WorldBasedSetting(_SettingValueFactoryBase):
        FACTORY_TUNABLES = dict(world=HomeWorldIds.create_enum_entry())

        @staticproperty
        def is_world_based(): return True

        def get_setting_value(self):
            return self.settings.get_world_settings(self.world).get(self.key)

    def __init__(self, *args, **kwargs):
        kwargs['world_based'] = self._WorldBasedSetting.TunableFactory()
        kwargs['not_world_based'] = self._SettingValueFactoryBase.TunableFactory()
        kwargs['default'] = 'not_world_based'

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Factory Declaration                                                                                                 #
#######################################################################################################################

class SituationJobsFilter(
    HasTunableSingletonFactory, AutoFactoryInit, SnippetMixin,
    snippet_name='situation_jobs_filter',
):
    """
    **prefix_list**: These are the list of "prefixes" that will be used to search for all SITUATION_JOBS tuning whose name
    begins with any of the following prefixes. Whitelisted and blacklisted (if any) entries will be collected, and then
    the overall result will be the difference between the two. These will be added to the global bypass list IF this
    filter is turned "on" and ignored otherwise.

    **setting_value**: This is a tuple used to get the setting which will be used to turn this tuning filter "on" or "off"

    **whitelist**: These are a specific list of situation jobs which were not found by the prefix_list but which should
    be collected for bypass.

    **whitelist_tags**: These are tags which are used to look up SITUATION_JOBS added to the collective bypass list.

    **blacklist_tags**: These are tags which are used against any SITUATION_JOBS collected in the whitelist_tags. Anything
    collected from the whitelist_tags with any of these tags will be uncollected.

    **blacklist**: This is a mapping of SITUATION_JOBS against the bypass list that they will go towards.
    By default, they go to the GLOBAL bypass list. They can also go to the SOFT bypass list, or simply be excluded from
    being collected in general and don't go to any list. Anything collected here which goes towards a list will be
    bypassed regardless whether this tuning filter is "on"
    """

    @classmethod
    def tuned_values(cls):
        from services import get_instance_manager

        return get_instance_manager(Types.SITUATION_JOB).types.values()

    FACTORY_TUNABLES = {
        'setting_value': TunableSettingValueVariant(),
        'target_list': BypassListType.to_enum_entry(),
        'search_list': TunableSearchableWhiteBlackList(),
        'whitelist': TunableSet(tunable=SituationJob.TunablePackSafeReference()),
        'whitelist_tags': TunableTags(filter_prefixes=['role'], pack_safe=True),
        'blacklist_tags': TunableTags(pack_safe=True),
        'blacklist': SituationBypassMapping(),
    }

    @property
    def is_world_based(self): return self.setting_value.is_world_based

    @filtered_cached_property(filter_func=lambda value, **_: value is not None)
    def whitelisted_situation_jobs(cls): return cls.whitelist

    @property
    def toggle_value(self) -> bool: return self.setting_value()

    def __bool__(self): return self.toggle_value

    @property
    def has_whitelist_tags(self): return bool(self.whitelist_tags)

    def _test_situation(self, situation_job):
        whitelist_test = situation_job.tags & self.whitelist_tags
        blacklist_test = situation_job.tags & self.blacklist_tags

        return whitelist_test and not blacklist_test

    @conditional_cached_property(condition=lambda self: self.has_whitelist_tags, fallback=frozenset())
    def tagged_situation_jobs(self): return frozenset(job for job in self.tuned_values() if self._test_situation(job))

    @property
    def matched_situation_jobs(self) -> set: return self.search_list.matched_situation_jobs

    @cached_property
    def blacklisted_situation_jobs(self):
        situations_lists: Dict[BypassListType, set] = defaultdict(set)

        for (job, bypass_list_type) in self.blacklist.items():
            if job is None:
                continue
            situations_lists[bypass_list_type].add(job)

        return situations_lists

    def __call__(self):
        situations = {*self.matched_situation_jobs, *self.tagged_situation_jobs, *self.whitelisted_situation_jobs}
        soft_list = self.blacklisted_situation_jobs.get(BypassListType.SOFT, set())
        global_list = self.blacklisted_situation_jobs.get(BypassListType.GLOBAL, set())
        blacklist = self.blacklisted_situation_jobs.get(BypassListType.NONE, set())

        if self.target_list is BypassListType.GLOBAL:
            # if High School is opened to everyone (we are disabled) then the whitelisted situations should be
            # added to the global bypass list and anything blacklisted should be added to the appropriate list further
            # if High School is restricted (we are enabled) then the whitelisted situations are ignored and only
            # blacklisted situations should be returned

            result = SituationFilterResult(soft_=soft_list, global_=global_list)
            return (result.update(situations) if self else result).difference(blacklist)

        elif self.target_list is BypassListType.SOFT:
            # if we are in this case, we are targeting things like the Tourist toggle
            # in such a case, situation jobs that get collected either end up in the soft filter list or in the
            # global bypass list, depending on if the filter is turned on or off.
            # This contrasts with the above in that things get collected to go to the global bypass list ONLY
            # in the event the filter is enabled, in addition to blacklists against THOSE situations which will end up
            # in the designated list, or simply not be collected at all

            results = SituationFilterResult(soft_=situations, global_=global_list)
            return (results.update(soft_list, list_type=BypassListType.SOFT) if self else results).difference(blacklist)

        else:
            return SituationFilterResult()


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

(TunableSituationJobsFilterSnippetReference, TunableSituationJobsFilterSnippet) = SituationJobsFilter._snippet
(
    TunableTouristsJobsFilterSnippetReference, TunableTouristsJobsFilterSnippet
) = SituationJobsFilter.define_snippet('tourists_jobs_filter', use_list_reference=True)

__all__ = (
    'SituationFilterResult',
    'TunableSituationJobsFilterSnippet', 'TunableSituationJobsFilterSnippetReference',
    'TunableTouristsJobsFilterSnippetReference', 'TunableTouristsJobsFilterSnippet',
)

"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details a special tunable used for searching through large swathes of situation jobs by name.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from typing import Callable
from functools import partial
import re

# sims 4 imports
from sims4.utils import classproperty
from sims4.repr_utils import standard_repr
from sims4.resources import Types
from sims4.tuning.tunable import Tunable, OptionalTunable, TunableSingletonFactory, TunableSet

# miscellaneous
import enum

# local imports
from kuttoe_home_regions.utils import *


#######################################################################################################################
# Prefix White/BlackList Tuning                                                                                       #
#######################################################################################################################

@enum_entry_factory(default='PREFIX', invalid=())
class SearchType(enum.Int):
    PREFIX = ...
    SUFFIX = ...
    CONTAINS = ...
    REGEX = ...

    @classproperty
    def search_func(cls) -> Callable[[str, str], bool]:
        def _search_func(job_name: str, search_term: str) -> bool:
            if cls is cls.SUFFIX:
                func = str.endswith
            elif cls is cls.CONTAINS:
                func = str.__contains__
            elif cls is cls.REGEX:
                func = lambda job_name, search_term: bool(re.match(search_term, job_name, flags=0))
            else:
                func = str.startswith

            return func(job_name, search_term)

        return _search_func


class SearchableWhiteBlackList(ManagedTuningMixin, tuning_type=Types.SITUATION_JOB):
    __slots__ = ('_whitelist', '_blacklist', '_search_type',)
    REPLACEMENT_STRING = re.compile(r"<class 'sims4\.tuning\.instances\.|'>")

    @classmethod
    def _get_job_name(cls, situation_job):
        return re.sub(cls.REPLACEMENT_STRING, '', str(situation_job))

    def __init__(self, whitelist=frozenset(), blacklist=frozenset(), search_type=SearchType.PREFIX):
        self._whitelist = whitelist
        self._blacklist = blacklist
        self._search_type: SearchType = search_type

    @property
    def search_func(self) -> Callable[[str, str], bool]: return self._search_type.search_func

    def _does_situation_job_match(self, situation_job):
        situation_job_name = self._get_job_name(situation_job)

        def _match(from_whitelist=True):
            source_name = 'white' if from_whitelist else 'black'
            source = getattr(self, f'_{source_name}list', set())

            return any(self.search_func(situation_job_name, search_term) for search_term in source)

        return False if _match(False) else _match(True)

    @cached_property
    def matched_situation_jobs(self) -> set:
        return set(job for job in self.tuned_values() if self._does_situation_job_match(job))

    def __iter__(self):
        yield from self.matched_situation_jobs

    def __repr__(self):
        return standard_repr(self, whitelist=self._whitelist, blacklist=self._blacklist, search_type=self._search_type)

    def __str__(self):
        return f'{repr(self)}[{self.matched_situation_jobs}]'


class TunableSearchableWhiteBlackList(TunableSingletonFactory):
    __slots__ = ()

    @staticmethod
    def _factory(whitelist, blacklist, search_type):
        return SearchableWhiteBlackList(whitelist, blacklist, search_type)

    FACTORY_TYPE = _factory

    @classproperty
    def tunable(cls):
        return Tunable(tunable_type=str, default=None, allow_empty=False)

    @classproperty
    def base_tunable(cls):
        return TunableSet(cls.tunable)

    @classproperty
    def optional_tunable(cls):
        t = cls.base_tunable
        return OptionalTunable(disabled_value=frozenset(), disabled_name='nothing', enabled_name='specify', tunable=t)

    def load_etree_node(self, node, source, expect_error):
        value = super().load_etree_node(node, source, expect_error)
        whitelist = value._whitelist
        blacklist = value._blacklist

        error_msg, base_msg = None, '\nInstance: {}, Prefix List: {}'.format(source, value)
        if blacklist and not whitelist:
            error_msg = 'Prefix list must contain a whitelisted item if there is a blacklisted item.'
        elif any(prefix in whitelist for prefix in blacklist):
            error_msg = 'Item cannot appear both in whitelist and blacklist at the same time.'

        if error_msg:
            raise ValueError(f'{error_msg}{base_msg}')
        return value

    def __init__(self):
        super().__init__(
            whitelist=self.base_tunable,
            blacklist=self.optional_tunable,
            search_type=SearchType.to_enum_entry()
        )


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('TunableSearchableWhiteBlackList', )

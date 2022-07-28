#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims 4 imports
from sims4.tuning.tunable import Tunable
from sims4.collections import frozendict

# filter imports
from filters.location_based_filter_terms import LocationBasedFilterTerms

# misc imports
import snippets

# local imports
from kuttoe_home_regions.home_worlds import HomeWorldIds


#######################################################################################################################
#  Snippet Class Information                                                                                          #
#######################################################################################################################


snippet_name = snippets.SNIPPET_CLASS_NAMES['location_based_filter_terms']
SnippetBase = vars(snippets)[snippet_name]


#######################################################################################################################
#  Base Tuning Class                                                                                                  #
#######################################################################################################################


class _DynamicFilterBase(SnippetBase):
    SOFT_FILTER_VALUE = Tunable(tunable_type=float, default=0.1)

    @classmethod
    def _get_region_list(cls, home_world: HomeWorldIds):
        return {home_world.region}

    @classmethod
    def _create_filter_term(cls, home_world: HomeWorldIds, minimum_filter_score: float = 0.0):
        return home_world.create_lives_in_region_filter(minimum_filter_score, *cls._get_region_list(home_world))

    @classmethod
    def _generate_value(cls):
        return dict()

    @staticmethod
    def _merge_filter_lists(old_list, new_list):
        value = old_list.value
        terms = dict(value.region_to_filter_terms)

        for (region, filter_term) in new_list.items():
            new_terms = {filter_term}
            new_terms.update(terms.get(region, tuple()))
            terms[region] = tuple(new_terms)

        args = dict()
        args['default_filter_terms'] = value.default_filter_terms
        args['region_to_filter_terms'] = frozendict(terms)
        return LocationBasedFilterTerms(**args)

    @classmethod
    def _tuning_loaded_callback(cls):
        cls.value = cls._merge_filter_lists(cls, cls._generate_value())


#######################################################################################################################
#  Tuning Classes                                                                                                     #
#######################################################################################################################


class SoftTunableLocationBasedFilterTermsSnippet(_DynamicFilterBase):
    @classmethod
    def _generate_value(cls):
        return {
            world.region: cls._create_filter_term(world, cls.SOFT_FILTER_VALUE)
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
        return cls.SOFT_FILTER_VALUE if cls.has_soft_filter(home_world) else 0.0

    @classmethod
    def _generate_value(cls):
        return {
            world.region: cls._create_filter_term(world, cls._get_soft_filter_value(world))
            for world
            in HomeWorldIds.available_worlds
        }

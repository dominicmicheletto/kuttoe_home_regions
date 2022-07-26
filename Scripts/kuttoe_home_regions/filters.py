#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims 4 imports
from sims4.tuning.tunable import Tunable
from sims4.collections import frozendict

# filter imports
from filters.tunable import LivesInRegion

# misc imports
import snippets

# local imports
from kuttoe_home_regions.home_worlds import HomeWorldIds


#######################################################################################################################
#  Tuning Classes                                                                                                     #
#######################################################################################################################

snippet_name = snippets.SNIPPET_CLASS_NAMES['location_based_filter_terms']
SnippetBase = vars(snippets)[snippet_name]


class _DynamicFilterBase(SnippetBase):
    SOFT_FILTER_VALUE = Tunable(tunable_type=float, default=0.1)

    @classmethod
    def _get_region_list(cls, home_world: HomeWorldIds):
        return {home_world}

    @classmethod
    def _create_filter_term(cls, home_world: HomeWorldIds, minimum_filter_score: float = 0):
        args = dict()
        args['region'] = tuple(cls._get_region_list(home_world))
        args['street_for_creation'] = home_world.value
        args['minimum_filter_score'] = minimum_filter_score

        return LivesInRegion(**args)

    @classmethod
    def _generate_value(cls):
        return dict()

    @classmethod
    def _tuning_loaded_callback(cls):
        terms = dict(cls.value.region_to_filter_terms)
        terms.update(cls._generate_value())

        cls.value.region_to_filter_terms = frozendict(terms)


class SoftTunableLocationBasedFilterTermsSnippet(_DynamicFilterBase):
    @classmethod
    def _generate_value(cls):
        return {
            world: cls._create_filter_term(world, cls.SOFT_FILTER_VALUE)
            for world
            in HomeWorldIds.available_worlds
        }


class DynamicTunableLocationBasedFilterTermsSnippet(_DynamicFilterBase):
    @classmethod
    def _get_settings_data(cls, home_world: HomeWorldIds):
        from kuttoe_home_regions.settings import Settings

        return Settings.get_world_settings(home_world)

    @classmethod
    def _get_region_list(cls, home_world: HomeWorldIds):
        settings_data = cls._get_settings_data(home_world)

        additional_regions = {HomeWorldIds[region].region for region in settings_data['Worlds']}
        return super()._get_region_list(home_world).union(additional_regions)

    @classmethod
    def _get_soft_filter_value(cls, home_world: HomeWorldIds):
        settings_data = cls._get_settings_data(home_world)

        return cls.SOFT_FILTER_VALUE if settings_data['Soft'] else 0

    @classmethod
    def _generate_value(cls):
        return {
            world: cls._create_filter_term(world, cls._get_soft_filter_value(world))
            for world
            in HomeWorldIds.available_worlds
        }


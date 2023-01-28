"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details a special tunable variant of factories which determines how pickers that rely on world lists how
the list of worlds is to be generated.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

from sims4.tuning.tunable import TunableVariant, Tunable, HasTunableSingletonFactory, AutoFactoryInit
from interactions import ParticipantType
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.filters.statistics import UsesAllowedRegionsBitsetMixin


#######################################################################################################################
# Tunable Definitions                                                                                                 #
#######################################################################################################################

class TunableAllowedWorldsList(TunableVariant):
    class _AllowedWorldsListBase(HasTunableSingletonFactory, AutoFactoryInit):
        def get_worlds(self, _resolver):
            return tuple()

    class _ExemptWorlds(_AllowedWorldsListBase, UsesAllowedRegionsBitsetMixin):
        FACTORY_TUNABLES = {'restrict_to_exempt_worlds': Tunable(tunable_type=bool, default=False)}

        @staticmethod
        def _get_sim_info(resolver):
            return resolver.get_participant(ParticipantType.TargetSim) or resolver.get_participant(ParticipantType.Actor)

        def _should_include_world(self, world, sim_info):
            if self.restrict_to_exempt_worlds:
                return self._is_world_allowed(sim_info, world)
            else:
                return not self._is_world_allowed(sim_info, world)

        def get_worlds(self, resolver):
            sim_info = self._get_sim_info(resolver)

            return (world for world in HomeWorldIds.available_worlds if self._should_include_world(world, sim_info))

    class _AllAllowedWorlds(_AllowedWorldsListBase):
        def get_worlds(self, _resolver):
            return HomeWorldIds.available_worlds

    class _TouristWorlds(_AllowedWorldsListBase):
        def get_worlds(self, _resolver):
            return HomeWorldIds.tourist_worlds

    class _SpecifyWorlds(_TouristWorlds):
        FACTORY_TUNABLES = {'world_list': HomeWorldIds.create_enum_set()}

        def get_worlds(self, _resolver):
            return self.world_list

    def __init__(self, *args, **kwargs):
        factories = dict()
        factories['all_worlds'] = self._AllAllowedWorlds, True
        factories['exempt_worlds'] = self._ExemptWorlds, False
        factories['tourist_worlds'] = self._TouristWorlds, False
        factories['specify_worlds'] = self._SpecifyWorlds, False

        for (key, [factory, is_default]) in factories.items():
            kwargs[key] = factory.TunableFactory()

            if is_default:
                kwargs['default'] = key

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('TunableAllowedWorldsList', )

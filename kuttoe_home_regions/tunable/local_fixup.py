"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the LocalFixup tuning that is used in conjunction with the HomeRegions data to define "fixup"
information that needs to occur to make a Sim a "proper" resident of a given World.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# misc imports
import services
from sims.sim_info import SimInfo

# sims 4 imports
from sims4.resources import Types
from sims4.tuning.tunable import Tunable, OptionalTunable, TunableSet, AutoFactoryInit, HasTunableFactory

# local imports
from kuttoe_home_regions.utils import cached_property


#######################################################################################################################
# Factory Declaration                                                                                                 #
#######################################################################################################################

class LocalFixup(AutoFactoryInit, HasTunableFactory):
    __getitem__ = services.get_instance_manager

    @staticmethod
    def _get_region_info(world_id: int):
        from kuttoe_home_regions.enum.home_worlds import HomeWorldIds

        home_world = HomeWorldIds.get_matching_home_world_from_value(world_id)
        if home_world.has_local_fixup:
            return home_world.local_fixup
        return home_world.default_local_fixup

    @staticmethod
    def clear_all_data(sim_info: SimInfo):
        from traits.trait_tracker import TraitTracker
        from kuttoe_home_regions.enum.home_worlds import HomeWorldIds

        if sim_info is None: return
        tracker: TraitTracker = sim_info.trait_tracker

        for home_world in HomeWorldIds.available_worlds:
            local_fixup = home_world.local_fixup
            if local_fixup is None:
                continue

            for trait in local_fixup.traits:
                tracker._remove_trait(trait)

    FACTORY_TUNABLES = {
        '_traits': TunableSet(Tunable(tunable_type=int, default=0, allow_empty=False)),
    }

    def __init__(self, region_id: int, *args, **kwargs):
        self._region_id = region_id

        super().__init__(*args, **kwargs)

    @cached_property
    def traits(self): return self._collect_tuning(Types.TRAIT, self._traits)

    def _collect_tuning(self, tuning_type: Types, tuning_ids):
        manager = self[tuning_type]
        collected_tuning = set()

        for tuning_id in tuning_ids:
            tuning = manager.get(tuning_id)

            if tuning is not None:
                collected_tuning.add(tuning)

        return frozenset(collected_tuning)

    def apply_traits(self, sim_info: SimInfo, previous_region_info):
        from traits.trait_tracker import TraitTracker
        tracker: TraitTracker = sim_info.trait_tracker

        if previous_region_info is not None:
            for trait in previous_region_info.traits:
                tracker._remove_trait(trait)

        for trait in self.traits:
            tracker._add_trait(trait)

    def __call__(self, sim_info: SimInfo, previous_region_id: int):
        if sim_info is None: return

        region_info = self._get_region_info(previous_region_id)
        self.apply_traits(sim_info, region_info)

    def __bool__(self):
        return bool(self.traits)


#######################################################################################################################
# Other Tunables                                                                                                      #
#######################################################################################################################

class OptionalTunableLocalFixup(OptionalTunable):
    def __init__(self, *args, **kwargs):
        super().__init__(tunable=LocalFixup.TunableFactory(), *args, **kwargs)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('OptionalTunableLocalFixup', 'LocalFixup', )

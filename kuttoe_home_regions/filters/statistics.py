"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the bitset that is used for Sim-specific region exemptions. The bitset takes the form of a
statistic and offers several convenience methods used for determining which regions are and are not allowed
(set in the bitset) and for toggling region exemptions by setting and unsetting specific bits.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims 4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.utils import flexmethod, classproperty
from sims4.tuning.tunable import Tunable, TunableMapping, TunableEnumEntry

# statistics imports
from statistics.statistic import Statistic
from statistics.statistic_tracker import StatisticTracker
from statistics.base_statistic import GalleryLoadBehavior

# miscellaneous imports
from sims.sim_info import SimInfo

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds


#######################################################################################################################
# Tuning Definitions                                                                                                  #
#######################################################################################################################

class TunableGalleryLoadBehaviourMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_type'] = Tunable(tunable_type=bool, default=False, allow_empty=False, needs_tuning=True)
        kwargs['value_type'] = TunableEnumEntry(tunable_type=GalleryLoadBehavior, default=GalleryLoadBehavior.DONT_LOAD)

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Instance Tuning Definitions                                                                                         #
#######################################################################################################################

class AllowedRegionsBitset(Statistic):
    REMOVE_INSTANCE_TUNABLES = ('gallery_load_behavior', )
    GALLERY_LOAD_BEHAVIOUR_MAPPING = TunableGalleryLoadBehaviourMapping()

    @classproperty
    def gallery_load_behavior(cls):
        from kuttoe_home_regions.settings import Settings

        default = GalleryLoadBehavior.LOAD_ONLY_FOR_SIM
        return cls.GALLERY_LOAD_BEHAVIOUR_MAPPING.get(Settings.save_across_gallery_toggle, default)

    @flexmethod
    def get_value(cls, inst):
        return int(super(__class__, inst if inst is not None else cls).get_value())

    def is_region_allowed(self, region: HomeWorldIds):
        return bool(self.get_value() & region.bit_value)

    def is_region_disallowed(self, region: HomeWorldIds):
        return not self.is_region_allowed(region)

    def get_allowed_regions(self):
        return {region for region in HomeWorldIds.available_worlds if self.is_region_allowed(region)}

    def get_disallowed_regions(self):
        return HomeWorldIds.available_worlds - self.get_allowed_regions()

    def allow_region(self, region: HomeWorldIds):
        self.set_value(self.get_value() | region.bit_value)

    def disallow_region(self, region: HomeWorldIds):
        self.set_value(self.get_value() & ~region.bit_value)

    def allow_all_regions(self):
        self.set_value(self.max_value)

    def disallow_all_regions(self):
        self.set_value(self.min_value)


class UsesAllowedRegionsBitsetMixin:
    ALLOWED_REGIONS_BITSET = Statistic.TunablePackSafeReference(class_restrictions=('AllowedRegionsBitset',))

    @classproperty
    def stat_type(cls): return cls.ALLOWED_REGIONS_BITSET

    @classmethod
    def get_stat_from_sim_info(cls, sim_info: SimInfo) -> AllowedRegionsBitset:
        return sim_info.get_statistic(cls.stat_type, True)

    @classmethod
    def _is_region_allowed(cls, sim_info: SimInfo, region):
        home_world: HomeWorldIds = HomeWorldIds.region_to_home_world_mapping[region]
        stat: AllowedRegionsBitset = sim_info.get_statistic(cls.stat_type, True)

        return stat.is_region_allowed(home_world)

    @classmethod
    def _is_world_allowed(cls, sim_info: SimInfo, home_world: HomeWorldIds):
        stat: AllowedRegionsBitset = sim_info.get_statistic(cls.stat_type, True)

        return stat.is_region_allowed(home_world)

    @classmethod
    def _does_sim_have_filter_exemptions(cls, sim_info: SimInfo):
        stat_tracker: StatisticTracker = sim_info.statistic_tracker
        stat = stat_tracker.get_statistic(stat_type=cls.stat_type, add=False)

        if stat is not None:
            return stat.get_value() != 0

        return False


#######################################################################################################################
# Instance Tunable Locking                                                                                            #
#######################################################################################################################

lock_instance_tunables(AllowedRegionsBitset, max_value_tuning=HomeWorldIds.max_bit_value)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('AllowedRegionsBitset', 'UsesAllowedRegionsBitsetMixin', )

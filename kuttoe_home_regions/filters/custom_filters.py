"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the special filter used to allow for specific Sim exceptions to region filters.

Region filter exceptions are only applicable to LivesInRegion filters created by the Home Regions mod itself. All other
existing LivesInRegion filters are beholden to the filters defined in the core game.

Exemptions are determined by checking the value if their "allowed regions" bitset and seeing if any of the regions
in the filter are defined as exemptions. If the Sim has no special exemptions, then the original score is given.
Otherwise, the score given is 1 if either the original filter is true or the Sim is specially allowed in any of the
given regions, and 0 if neither of the two apply.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# Python imports
from typing import NamedTuple, Optional

# sims 4 imports
from sims4.reload import protected

# miscellaneous imports
import services
from sims4.tuning.tunable import OptionalTunable
from world.region import get_region_instance_from_zone_id
from filters.tunable import LivesInRegion, FilterResult
from sims.sim_info import SimInfo

# local imports
from kuttoe_home_regions.filters.statistics import UsesAllowedRegionsBitsetMixin
from kuttoe_home_regions.tunable.street_selector import TunableStreetSelectorVariant


#######################################################################################################################
# Global Variable Declaration                                                                                         #
#######################################################################################################################

with protected(globals()):
    _TRACK_FILTER_PROGRESS = False


#######################################################################################################################
# Named Tuple Declarations                                                                                           #
#######################################################################################################################

class FilterProgress(NamedTuple):
    first_name: str
    last_name: str
    score: FilterResult
    region: Optional[tuple]
    was_exempt: bool


#######################################################################################################################
# Factory Declaration                                                                                                 #
#######################################################################################################################

class LivesInRegionWithExceptions(LivesInRegion, UsesAllowedRegionsBitsetMixin):
    _FILTER_PROGRESS = list()
    FACTORY_TUNABLES = {
        'street_for_creation': OptionalTunable(TunableStreetSelectorVariant()),
    }

    def get_valid_world_ids(self):
        if self.street_for_creation is None:
            return None, None

        street = self.street_for_creation()
        if street is None:
            return None, None

        world_id = services.get_world_id(street.value)
        value = [(world_id, ), None]

        if self.invert_score:
            value.reverse()

        return tuple(value)

    def _track_progress(self, sim_info: SimInfo, score: FilterResult, has_exemptions: bool):
        global _TRACK_FILTER_PROGRESS

        if not _TRACK_FILTER_PROGRESS:
            return

        row = FilterProgress(sim_info.first_name, sim_info.last_name, score, self.region, has_exemptions)
        self._FILTER_PROGRESS.append(row)

    def calculate_score(self, sim_info: SimInfo, **kwargs):
        original_score = super().calculate_score(sim_info, **kwargs)
        has_exemptions = self._does_sim_have_filter_exemptions(sim_info)

        self._track_progress(sim_info, original_score, has_exemptions)
        if not has_exemptions:
            return original_score

        current_region = get_region_instance_from_zone_id(services.current_zone_id())
        regions = self.region if self.region is not None else (current_region, )
        score = 1 if any(self._is_region_allowed(sim_info, region) for region in regions) else 0
        score = max(score, original_score.score)

        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('LivesInRegionWithExceptions', )

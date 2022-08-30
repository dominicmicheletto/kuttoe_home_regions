#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Dict, List
from collections import defaultdict

# sim4 imports
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory

# local imports
from kuttoe_home_regions.utils import InteractionTargetType
from kuttoe_home_regions.tunable import InteractionRegistryData
from kuttoe_home_regions.tunable.world_list_interaction import AllowWorldInteractionTuningData
from kuttoe_home_regions.tunable.world_list_interaction import DisallowWorldInteractionTuningData
from kuttoe_home_regions.tunable.command_interaction import CommandInteractionTuningData
from kuttoe_home_regions.tunable.picker_interaction import PickerInteractionTuningData
from kuttoe_home_regions.tunable.toggle.soft_filter_toggle import SoftFilterInteractionTuningData
from kuttoe_home_regions.tunable.toggle.bidirectional_toggle import BidirectionalToggleTuningData
from kuttoe_home_regions.tunable.toggle.high_school_toggle import HighSchoolToggleTuningData


#######################################################################################################################
#  Tunable Data                                                                                                       #
#######################################################################################################################


class _InteractionDataBase(HasTunableFactory, AutoFactoryInit):
    @classmethod
    def _init_property(cls, inst, property_cls):
        return property_cls()

    @classmethod
    def _create_properties(cls, inst, key: str):
        tuning_cls = getattr(inst, key, None)
        if not tuning_cls:
            return

        tuning = cls._init_property(inst, tuning_cls)
        setattr(inst, f'{key}_data', tuning)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in self.forwarded_properties:
            self._create_properties(self, key)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        tunables = getattr(cls, 'FACTORY_TUNABLES', dict())
        setattr(cls, 'forwarded_properties', tuple(tunables.keys()))

    def __iter__(self):
        for prop in self.forwarded_properties:
            yield getattr(self, f'{prop}_data', None)

    @property
    def interaction_target_mapping(self) -> Dict[InteractionTargetType, List[InteractionRegistryData]]:
        mapping = defaultdict(set)

        for interaction_data in self:
            if not interaction_data:
                continue

            mapping[interaction_data.injection_target].add(interaction_data.interaction_data)

        return {**mapping}

    def inject(self) -> Dict[InteractionTargetType, int]:
        mapping = defaultdict(int)

        for (target, affordance_infos) in self.interaction_target_mapping.items():
            mapping[target] += target.update_and_register_affordances(*affordance_infos)

        return {**mapping}


class InteractionData(_InteractionDataBase):
    FACTORY_TUNABLES = {
        'command': CommandInteractionTuningData.TunableFactory(),
        'picker': PickerInteractionTuningData.TunableFactory(),
        'allow_world': AllowWorldInteractionTuningData.TunableFactory(),
        'disallow_world': DisallowWorldInteractionTuningData.TunableFactory(),
        'soft_filter': SoftFilterInteractionTuningData.TunableFactory(),
    }

    @classmethod
    def _init_property(cls, inst, property_cls):
        return property_cls(inst.world_data)

    def __init__(self, world_data, *args, **kwargs):
        self._world_data = world_data
        super().__init__(*args, **kwargs)

    @property
    def world_data(self):
        return self._world_data


class InteractionWithoutRegionData(_InteractionDataBase):
    FACTORY_TUNABLES = {
        'high_school_toggle': HighSchoolToggleTuningData.TunableFactory(),
        'bidirectional_toggle': BidirectionalToggleTuningData.TunableFactory(),
    }

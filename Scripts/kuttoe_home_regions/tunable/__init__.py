#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from collections import namedtuple
from typing import Tuple

# sim4 imports
from sims4 import hash_util
from sims4.resources import Types, get_resource_key
from sims4.utils import constproperty
from sims4.tuning.tunable import TunableEnumEntry, Tunable

# local imports
from kuttoe_home_regions.utils import InteractionTargetType
from kuttoe_home_regions.ui import InteractionType
from kuttoe_home_regions.home_worlds import HomeWorldIds


#######################################################################################################################
#  Named Tuples                                                                                                       #
#######################################################################################################################


InteractionRegistryData = namedtuple('InteractionRegistryData', [
    'interaction', 'resource_key',
])


#######################################################################################################################
#  Interaction Name Tuning                                                                                            #
#######################################################################################################################


class TunableInteractionName(Tunable):
    class _Wrapper:
        @staticmethod
        def _get_hash_for_name(interaction_name_base: str, suffix: str) -> Tuple[str, int]:
            hash_name_template = '{}_{}'.format(interaction_name_base, suffix)

            return hash_name_template, hash_util.hash64(hash_name_template)

        @classmethod
        def _get_hash_for_home_world(cls, interaction_name_base: str, home_world: HomeWorldIds):
            return cls._get_hash_for_name(interaction_name_base, home_world.pretty_name)

        __slots__ = ('_interaction_name_base',)

        def __init__(self, interaction_name_base: str) -> None:
            self._interaction_name_base = interaction_name_base

        def __bool__(self) -> bool:
            return self._interaction_name_base is not None

        def __call__(self, home_world: HomeWorldIds):
            return self._get_hash_for_home_world(self.interaction_name_base, home_world)

        def _get_hash_for_suffix(self, suffix: str):
            return self._get_hash_for_name(self.interaction_name_base, suffix)

        @property
        def interaction_name_base(self):
            return self._interaction_name_base

    def __init__(self, *args, **kwargs):
        kwargs['needs_tuning'] = True
        kwargs['default'] = None

        super().__init__(tunable_type=str, *args, **kwargs)
        self.cache_key = 'TunableInteractionName'

    def _convert_to_value(self, interaction_name_base: str):
        if interaction_name_base is None:
            return
        return self._Wrapper(interaction_name_base)


#######################################################################################################################
# Mixins                                                                                                              #
#######################################################################################################################


class _InteractionTypeMixin:
    __CACHE = dict()
    FACTORY_TUNABLES = {
        'injection_target': TunableEnumEntry(tunable_type=InteractionTargetType,
                                             default=InteractionTargetType.INVALID,
                                             invalid_enums=(InteractionTargetType.INVALID,)),
        'interaction_name_base': TunableInteractionName(),
    }
    INSTANCE_TUNABLES = FACTORY_TUNABLES

    @constproperty
    def locked_args() -> dict:
        return dict()

    @constproperty
    def properties_mapping() -> dict:
        return dict()

    @property
    def interaction_type(self) -> InteractionType:
        return self.class_base.interaction_type

    @property
    def command_interaction(self):
        if self in self.__CACHE:
            return self.__CACHE[self]

        cls = self.create_tuning_class(self.class_base, locked_args=self.locked_args, **self.properties_mapping)
        return self.__CACHE.setdefault(self, cls)

    @property
    def interaction_name_info(self):
        home_world = getattr(self, 'home_world', None)
        suffix = getattr(self, 'interaction_name_suffix', None)
        name_base = getattr(self, 'interaction_name_base')

        if home_world:
            return name_base(home_world)
        elif suffix:
            return name_base._get_hash_for_suffix(suffix)
        else:
            base = name_base.interaction_name_base

            return base, hash_util.hash64(base)

    @property
    def interaction_resource_key(self):
        return get_resource_key(self.interaction_name_info[1], Types.INTERACTION)

    @property
    def interaction_name(self):
        return self.interaction_name_info[0]

    @property
    def interaction_data(self):
        return InteractionRegistryData(self.command_interaction, self.interaction_resource_key)

    def inject(self):
        return self.injection_target.update_and_register_affordances(self.interaction_data)


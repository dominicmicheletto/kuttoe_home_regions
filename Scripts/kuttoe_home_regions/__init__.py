#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Dict
from collections import namedtuple

# miscellaneous
from services import get_instance_manager
from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target

# sims4 imports
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunablePackSafeReference
from sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunable, TunableRange
from sims4.resources import Types
from sims4.collections import frozendict
from sims4.commands import Command, CommandType

# local imports
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.tuning import InteractionType, TunableInteractionName, InteractionRegistryData
from kuttoe_home_regions.tuning import InteractionData
from kuttoe_home_regions.settings import Settings
from kuttoe_home_regions.commands import kuttoe_set_world_id
from kuttoe_home_regions.utils import on_load_complete, InteractionTargetType


#######################################################################################################################
#  Named Tuples                                                                                                       #
#######################################################################################################################


ConsoleCommands = namedtuple('ConsoleCommands', ['sim', 'settings'])


#######################################################################################################################
#  World Data Tuning                                                                                                  #
#######################################################################################################################


class WorldData(HasTunableFactory, AutoFactoryInit):
    SOFT_FILTER_VALUE = Tunable(tunable_type=float, default=0.1)
    FACTORY_TUNABLES = {
        'pie_menu_priority': TunableRange(tunable_type=int, default=2, maximum=10, minimum=0)
    }

    def __init__(self, home_world: HomeWorldIds, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._home_world = home_world

    @property
    def home_world(self):
        return self._home_world

    @property
    def region(self):
        return self.home_world.region

    @property
    def interaction_display_name(self):
        return self.home_world.region_name

    @property
    def pack(self):
        return self.home_world.pack

    @property
    def pie_menu_icon(self):
        return self.home_world.pie_menu_icon

    @property
    def command_name(self):
        return self.home_world.command_name

    @property
    def user_has_required_pack(self):
        return self.home_world.is_available

    def create_console_command(self):
        command_name, value = self.command_name, self.home_world.value

        @Command(command_name, command_type=CommandType.Live)
        def _kuttoe_set_world_id(opt_sim: OptionalSimInfoParam = None, _connection=None):
            sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)

            kuttoe_set_world_id(self.home_world, sim_info, _connection)

        return ConsoleCommands(_kuttoe_set_world_id, Settings.create_console_commands(self.home_world))

    def inject_into_filter(self, sim_filter):
        new_dict = dict(sim_filter.value.region_to_filter_terms)
        settings_data = Settings.get_world_settings(self.home_world)
        new_data = new_dict[self.region][0]
        if self.region not in new_dict:
            return

        regions = set(new_dict[self.region][0].region)
        regions.update(HomeWorldIds[region].region for region in settings_data['Worlds'])
        new_data.region = tuple(regions)

        if settings_data['Soft']:
            new_data.minimum_filter_score = self.SOFT_FILTER_VALUE

        new_dict[self.region] = (new_data, )
        sim_filter.value.region_to_filter_terms = frozendict(new_dict)

    def register_and_inject_affordances(self, interaction_data: InteractionData) -> Dict[InteractionTargetType, int]:
        return interaction_data(self).inject()


#######################################################################################################################
#  Injection Tuning                                                                                                   #
#######################################################################################################################


class HomeWorldMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'home_world'
        kwargs['key_type'] = TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT)
        kwargs['value_name'] = 'world_data'
        kwargs['value_type'] = WorldData.TunableFactory()

        super().__init__(*args, **kwargs)


class HomeRegionsCommandTuning:
    HOME_WORLD_MAPPING = HomeWorldMapping()
    INTERACTION_DATA = InteractionData.TunableFactory()
    LOCATION_BASED_FILTER = TunablePackSafeReference(manager=get_instance_manager(Types.SNIPPET), allow_none=False,
                                                     class_restrictions=('LocationBasedFilterTerms', ))

    @staticmethod
    @on_load_complete(Types.TUNING, safe=False)
    def _register_all_data(_):
        cls = HomeRegionsCommandTuning
        data: Dict[HomeWorldIds, WorldData] = cls.HOME_WORLD_MAPPING

        InteractionTargetType.verify_all_values()
        for (home_world, world_data) in data.items():
            command_data: WorldData = world_data(home_world)

            if not command_data.user_has_required_pack:
                continue

            command_data.create_console_command()
            command_data.inject_into_filter(cls.LOCATION_BASED_FILTER)
            command_data.register_and_inject_affordances(cls.INTERACTION_DATA)
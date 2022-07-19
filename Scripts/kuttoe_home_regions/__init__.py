#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# C-API game imports
from _collections import defaultdict

# python imports
from collections import namedtuple
from typing import Dict, List

# miscellaneous
import services
from services import get_instance_manager

# objects
from objects.definition_manager import DefinitionManager
from objects.game_object import GameObject
from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target
from sims4.collections import frozendict
from sims4.commands import Command, CommandType

# sims4 imports
from sims4.tuning.instance_manager import InstanceManager
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunablePackSafeReference
from sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunable, TunableRange
from sims4.resources import Types
from sims4.utils import classproperty

# local imports
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.tuning import InteractionType, TunableInteractionName, InteractionRegistryData, \
    InteractionData
from kuttoe_home_regions.settings import Settings
from kuttoe_home_regions.commands import kuttoe_set_world_id
from kuttoe_home_regions.utils import on_load_complete


#######################################################################################################################
#  World Data Tuning                                                                                                  #
#######################################################################################################################


class WorldData(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'pie_menu_priority': TunableRange(tunable_type=int, default=2, maximum=10, minimum=0)
    }

    def __init__(self, home_world: HomeWorldIds, interaction_data, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._home_world = home_world
        self._interaction_data: InteractionData = interaction_data(self)

        for key in self.interaction_data.forwarded_properties:
            prop_name = f'{key}_interaction_data'
            prop = getattr(self.interaction_data, prop_name.replace('_world', ''), None)

            setattr(self, prop_name, prop)

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
    def interaction_data(self):
        return self._interaction_data

    @property
    def user_has_required_pack(self):
        return self.home_world.is_available

    def create_console_command(self):
        command_name, value = self.command_name, self.home_world.value

        @Command(command_name, command_type=CommandType.Live)
        def _kuttoe_set_world_id(opt_sim: OptionalSimInfoParam = None, _connection=None):
            sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)

            kuttoe_set_world_id(self.home_world, sim_info, _connection)

        return _kuttoe_set_world_id

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
            new_data.minimum_filter_score = 0.1

        new_dict[self.region] = (new_data, )
        sim_filter.value.region_to_filter_terms = frozendict(new_dict)


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
    SIM_OBJECT = Tunable(tunable_type=int, default=0, allow_empty=False, needs_tuning=True)
    TERRAIN_OBJECT = Tunable(tunable_type=int, default=0, allow_empty=False, needs_tuning=True)
    HOME_WORLD_MAPPING = HomeWorldMapping()
    INTERACTION_DATA = InteractionData.TunableFactory()
    LOCATION_BASED_FILTER = TunablePackSafeReference(manager=get_instance_manager(Types.SNIPPET), allow_none=False,
                                                     class_restrictions=('LocationBasedFilterTerms', ))

    @classproperty
    def sim_object(cls) -> GameObject:
        definition_manager = services.definition_manager()

        return super(DefinitionManager, definition_manager).get(cls.SIM_OBJECT)

    @classproperty
    def terrain_object(cls) -> GameObject:
        definition_manager = services.definition_manager()

        return super(DefinitionManager, definition_manager).get(cls.TERRAIN_OBJECT)

    @classproperty
    def tuning_definitions(cls):
        sim_object = cls.sim_object
        if not sim_object:
            raise AttributeError('Sim Object definition could not be found')

        terrain_object = cls.terrain_object
        if not terrain_object:
            raise AttributeError('Terrain Object definition could not be found')

        return namedtuple('TuningDefinitions', ['sim', 'terrain'])(sim_object, terrain_object)

    @staticmethod
    @on_load_complete(Types.TUNING, safe=False)
    def _register_all_data(tuning_manager):
        cls = HomeRegionsCommandTuning
        data: Dict[HomeWorldIds, WorldData] = cls.HOME_WORLD_MAPPING
        tuning_defs = cls.tuning_definitions
        sim_object = tuning_defs.sim
        terrain_object = tuning_defs.terrain

        interactions: Dict[GameObject, List[InteractionRegistryData]] = defaultdict(list)
        for (home_world, world_data) in data.items():
            command_data: WorldData = world_data(home_world, cls.INTERACTION_DATA)

            if not command_data.user_has_required_pack:
                continue

            command_data.create_console_command()
            command_data.inject_into_filter(cls.LOCATION_BASED_FILTER)
            interactions[sim_object].append(command_data.command_interaction_data)
            interactions[terrain_object].append(command_data.allow_world_interaction_data)
            interactions[terrain_object].append(command_data.disallow_world_interaction_data)
            interactions[terrain_object].append(command_data.picker_interaction_data)

            Settings.create_console_commands(home_world)

        affordance_manager: InstanceManager = get_instance_manager(Types.INTERACTION)
        for (obj, interactions_data) in interactions.items():
            sa_list = list()
            for interaction_data in interactions_data:
                interaction = interaction_data.interaction
                resource_key = interaction_data.resource_key

                affordance_manager.register_tuned_class(interaction, resource_key)
                sa_list.append(interaction)

            obj._super_affordances += tuple(sa_list)

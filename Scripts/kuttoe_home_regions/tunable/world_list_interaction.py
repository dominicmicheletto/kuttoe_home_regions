#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from collections import defaultdict

# miscellaneous
from services import get_instance_manager

# sim4 imports
from sims4.resources import Types, get_resource_key
from sims4.utils import classproperty, constproperty
from sims4.tuning.tunable import OptionalTunable, TunableTuple
from sims4.tuning.instances import lock_instance_tunables
from sims4.localization import TunableLocalizedStringFactory

# interaction imports
from interactions import ParticipantType
from interactions.picker.interaction_picker import InteractionPickerItem

# event testing imports
from event_testing.tests import TestList, CompoundTestList

# ui imports
from ui.ui_dialog_picker import UiItemPicker

# local imports
from kuttoe_home_regions.utils import construct_auto_init_factory, make_immutable_slots_class
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides
from kuttoe_home_regions.home_worlds import HomeWorldIds, TunableIconDefinition
from kuttoe_home_regions.commands import AlterType
from kuttoe_home_regions.interactions import WorldListPickerInteraction, AlterWorldListImmediateSuperInteraction
from kuttoe_home_regions.tunable import TunableInteractionName
from kuttoe_home_regions.tunable.python_based_interaction_data import PythonBasedInteractionWithRegionData


#######################################################################################################################
#  World List Interactions                                                                                            #
#######################################################################################################################


class _WorldListInteractionTuningDataBase(PythonBasedInteractionWithRegionData):
    BIDIRECTIONAL_TOGGLE_TOKEN = TunableLocalizedStringFactory()
    ENABLED_TOKEN = TunableLocalizedStringFactory()
    DISABLED_TOKEN = TunableLocalizedStringFactory()

    FACTORY_TUNABLES = {
        'picker_dialog': UiItemPicker.TunableFactory(),
        'picker_interaction_name': TunableLocalizedStringFactory(),
        'picker_description': TunableLocalizedStringFactory(),
        'disabled_interaction_behaviour': OptionalTunable(
            tunable=TunableTuple(disable_tooltip=OptionalTunable(TunableLocalizedStringFactory())),
            disabled_name='do_not_show',
            enabled_name='show_interactions',
        ),
        'no_worlds_available_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
        'item_icon': TunableIconDefinition(),
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls._SUB_INTERACTION_CACHE = defaultdict(dict)

    @constproperty
    def properties_mapping() -> dict:
        properties_mapping = dict()
        properties_mapping['possible_actions'] = 'possible_actions'
        properties_mapping['picker_dialog'] = 'custom_picker_dialog'

        return properties_mapping

    @classproperty
    def sub_interaction_cache(cls):
        return cls._SUB_INTERACTION_CACHE

    @constproperty
    def class_base():
        return WorldListPickerInteraction

    @staticmethod
    def _register_interaction(interaction_cls, interaction_data):
        affordance_manager = get_instance_manager(Types.INTERACTION)
        resource_key = get_resource_key(interaction_data[1], Types.INTERACTION)

        affordance_manager.register_tuned_class(interaction_cls, resource_key)

    def _create_sub_interaction(self, target_world: HomeWorldIds):
        source_world = self.home_world
        interaction_data = TunableInteractionName._Wrapper(self.interaction_name)(target_world)

        class _AlterWorldInteraction(AlterWorldListImmediateSuperInteraction):
            pass

        locked_args = dict()
        locked_args['source_world'] = source_world
        locked_args['target_home_world'] = target_world
        locked_args['alter_type'] = self.alter_type
        _AlterWorldInteraction.__name__ = interaction_data[0]
        lock_instance_tunables(_AlterWorldInteraction, **locked_args)
        self._register_interaction(_AlterWorldInteraction, interaction_data)

        return _AlterWorldInteraction

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for home_world in HomeWorldIds:
            if home_world in (HomeWorldIds.DEFAULT, self.home_world):
                continue

            self.sub_interaction_cache[self.home_world][home_world] = self._create_sub_interaction(home_world)

    def custom_picker_dialog(self):
        region_text = self.home_world.region_name()
        text = self.picker_dialog.text

        def new_text(*tokens):
            from kuttoe_home_regions.settings import Settings

            base_text = text(region_text, *tokens)
            state_text = Settings.get_token('bidirectional_toggle', self.ENABLED_TOKEN, self.DISABLED_TOKEN)
            return self.BIDIRECTIONAL_TOGGLE_TOKEN(base_text, state_text)

        if not text:
            return self.picker_dialog
        return create_tunable_factory_with_overrides(self.picker_dialog, text=new_text)

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.Actor, is_npc=False))

        tooltip = self.no_worlds_available_tooltip
        base_tests.append(self.get_worlds_available_left_test(self.home_world, self.alter_type, tooltip))

        return TestList(base_tests)

    @classmethod
    def _create_continuation(cls, source_world: HomeWorldIds, target_world: HomeWorldIds):
        args = dict()
        args['actor'] = ParticipantType.Actor
        args['target'] = ParticipantType.Object
        args['affordance'] = cls.sub_interaction_cache[source_world][target_world]
        args['carry_target'] = None
        args['inventory_carry_target'] = None
        args['preserve_preferred_object'] = True
        args['preserve_target_part'] = False
        args['si_affordance_override'] = None

        return make_immutable_slots_class(**args)

    def _get_picker_item_icon(self, target_world: HomeWorldIds):
        return self.item_icon(target_world).resource if self.item_icon else target_world.pie_menu_icon

    def _create_picker_item(self, target_world: HomeWorldIds):
        args = dict()
        args['continuation'] = (self._create_continuation(self.home_world, target_world),)
        args['icon'] = self._get_picker_item_icon(target_world)
        args['item_description'] = None
        args['item_tooltip'] = None
        args['localization_tokens'] = None
        args['name'] = target_world.region_name

        tests = self.get_enabled_tests(target_world)
        if self.disabled_interaction_behaviour:
            args['enable_tests'] = tests
            args['disable_tooltip'] = self.get_disabled_tooltip(target_world)
            args['visibility_tests'] = None
        else:
            args['enable_tests'] = None
            args['disable_tooltip'] = None
            args['visibility_tests'] = tests

        return construct_auto_init_factory(InteractionPickerItem, **args)

    def get_picker_description(self, target_world: HomeWorldIds):
        target_name = target_world.region_name()
        picker_description = self.picker_description

        if not picker_description:
            return None

        return lambda *tokens: picker_description(target_name, *tokens)

    def get_disabled_tooltip(self, target_world: HomeWorldIds):
        source_name = self.home_world.region_name()
        target_name = target_world.region_name()
        disabled_tooltip = getattr(self.disabled_interaction_behaviour, 'disable_tooltip', None)

        if not disabled_tooltip:
            return None
        return lambda *tokens: disabled_tooltip(target_name, source_name, *tokens)

    def get_enabled_tests(self, target_world: HomeWorldIds):
        base_tests = list()
        base_tests.append(self.get_is_world_available_test(self.home_world, target_world, self.alter_type))

        return CompoundTestList([TestList(base_tests)])

    @property
    def interaction_display_name(self):
        interaction_name = super().interaction_display_name()

        return lambda *args: self.picker_interaction_name(interaction_name, *args)

    def is_world_available(self, home_world: HomeWorldIds):
        return home_world.is_available and home_world not in (self.home_world, HomeWorldIds.DEFAULT)

    @property
    def available_worlds(self):
        return tuple(home_world for home_world in HomeWorldIds if self.is_world_available(home_world))

    def possible_actions(self):
        return tuple(self._create_picker_item(world) for world in self.available_worlds)


class AllowWorldInteractionTuningData(_WorldListInteractionTuningDataBase):
    @constproperty
    def alter_type():
        return AlterType.ALLOW_WORLD


class DisallowWorldInteractionTuningData(_WorldListInteractionTuningDataBase):
    @constproperty
    def alter_type():
        return AlterType.DISALLOW_WORLD

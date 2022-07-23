#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Tuple, Iterable, Dict, Any, List
from collections import namedtuple, defaultdict
from inspect import ismethod

# miscellaneous
from services import get_instance_manager

# sim4 imports
from sims4 import hash_util
from sims4.resources import Types, get_resource_key
from sims4.utils import classproperty, constproperty
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, Tunable, TunableMapping
from sims4.tuning.tunable import TunableTuple, TunablePackSafeReference, TunableEnumEntry
from sims4.tuning.instances import lock_instance_tunables
from sims4.localization import TunableLocalizedStringFactory

# interaction imports
from interactions import TargetType, ParticipantType
from interactions.utils.localization_tokens import _TunableObjectLocalizationTokenFormatterSingle, LocalizationTokens
from interactions.utils.tunable_icon import TunableIconVariant
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.picker.interaction_picker import InteractionPickerItem

# event testing imports
from event_testing.tests import TestList, CompoundTestList

# tunable utils imports
from tunable_utils.tunable_object_generator import _ObjectGeneratorFromParticipant

# ui imports
from ui.ui_dialog_picker import UiSimPicker, UiItemPicker

# local imports
from kuttoe_home_regions.utils import construct_auto_init_factory, make_immutable_slots_class
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides, InteractionTargetType
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.commands import AlterType
from kuttoe_home_regions.ui import InteractionType
from kuttoe_home_regions.tests import _TestSetMixin
from kuttoe_home_regions.interactions import _DisplayNotificationMixin
from kuttoe_home_regions.interactions import HomeWorldPickerInteraction, WorldListPickerInteraction
from kuttoe_home_regions.interactions import CommandImmediateSuperInteraction, AlterWorldListImmediateSuperInteraction
from kuttoe_home_regions.interactions import SoftTogglePickerInteraction, ToggleSettingImmediateSuperInteraction


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
# Tunable Python-Generated Interaction Data                                                                           #
#######################################################################################################################


class _InteractionTypeMixin:
    FACTORY_TUNABLES = {
        'injection_target': TunableEnumEntry(tunable_type=InteractionTargetType,
                                             default=InteractionTargetType.INVALID,
                                             invalid_enums=(InteractionTargetType.INVALID, )),
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
        return self.create_tuning_class(self.class_base, locked_args=self.locked_args, **self.properties_mapping)

    @property
    def interaction_name_info(self):
        return self.interaction_name_base(self.home_world)

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


class PythonBasedInteractionData(
    HasTunableFactory, AutoFactoryInit,
    _DisplayNotificationMixin, _TestSetMixin, _InteractionTypeMixin
):
    FACTORY_TUNABLES = {
        'interaction_category': TunablePackSafeReference(manager=get_instance_manager(Types.PIE_MENU_CATEGORY),
                                                         allow_none=False),
        'display_tooltip': OptionalTunable(tunable=TunableLocalizedStringFactory()),
    }

    @classmethod
    def get_display_name_text_tokens(
            cls,
            participants: Iterable[ParticipantType] = (ParticipantType.Actor, ParticipantType.Object,)
    ):
        formatter = construct_auto_init_factory(_TunableObjectLocalizationTokenFormatterSingle)

        def _create_tokens(participant: ParticipantType):
            args = dict()
            args['participant'] = participant
            args['in_slot'] = None

            return construct_auto_init_factory(_ObjectGeneratorFromParticipant, **args)

        def _create_value(participant=ParticipantType.Actor):
            args = dict()
            args['token_type'] = LocalizationTokens.TOKEN_PARTICIPANT
            args['objects'] = _create_tokens(participant)
            args['formatter'] = formatter

            return make_immutable_slots_class(**args)

        tokens = tuple(_create_value(participant) for participant in participants)
        return construct_auto_init_factory(LocalizationTokens, tokens=tokens)

    @constproperty
    def progress_bar_enabled():
        args = dict()
        args['bar_enabled'] = False
        args['remember_progress'] = False
        args['override_min_max_values'] = None
        args['interaction_exceptions'] = make_immutable_slots_class(is_music_interaction=False)
        args['force_listen_statistic'] = None
        args['blacklist_statistics'] = None

        return make_immutable_slots_class(**args)

    @constproperty
    def base_properties_mapping():
        properties_mapping = dict()
        properties_mapping['progress_bar_enabled'] = 'progress_bar_enabled'
        properties_mapping['display_tooltip'] = 'interaction_display_tooltip'
        properties_mapping['category'] = 'category'
        properties_mapping['test_globals'] = 'global_tests'
        properties_mapping['pie_menu_priority'] = 'pie_menu_priority'
        properties_mapping['display_name'] = 'interaction_display_name'
        properties_mapping['notification'] = 'notification'
        properties_mapping['target_home_world'] = 'home_world'
        properties_mapping['pie_menu_icon'] = 'pie_menu_icon'

        return properties_mapping

    def __init__(self, world_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._world_data = world_data

    @property
    def world_data(self):
        return self._world_data

    @property
    def region(self):
        return self.world_data.region

    @property
    def pie_menu_priority(self):
        return self.world_data.pie_menu_priority

    @property
    def interaction_display_name(self):
        return self.world_data.interaction_display_name

    @property
    def pie_menu_icon(self):
        return self.world_data.pie_menu_icon

    @property
    def category(self):
        return self.interaction_category

    @property
    def home_world(self) -> HomeWorldIds:
        return self.world_data.home_world

    @property
    def command_name(self):
        return self.home_world.command_name

    @property
    def interaction_display_tooltip(self):
        tooltip_base = self.display_tooltip
        if not tooltip_base:
            return None

        interaction_name = self.interaction_display_name()
        return lambda *tokens: tooltip_base(interaction_name, *tokens)

    @classproperty
    def get_display_name_tokens(cls):
        participants = [ParticipantType.Actor, ParticipantType.Object]

        if cls.interaction_type == InteractionType.PICKER:
            participants.append(ParticipantType.PickedSim)

        return cls.get_display_name_text_tokens(participants)

    @classproperty
    def default_locked_tunables(cls):
        locked_tunables = dict()
        locked_tunables['display_name_text_tokens'] = cls.get_display_name_tokens
        locked_tunables['target_type'] = TargetType.OBJECT
        locked_tunables['cheat'] = True

        return locked_tunables

    def create_tuning_class(
            self,
            cls_base: ImmediateSuperInteraction,
            locked_args: Dict[str, Any] = None,
            **properties_mapping: Dict[str, str]
    ):
        locked_tunables = locked_args or dict()
        locked_tunables.update(self.default_locked_tunables)

        properties_mapping.update(self.base_properties_mapping)
        removed_tunables = tuple(properties_mapping.keys())

        class _InteractionTuningClass(cls_base):
            REMOVE_INSTANCE_TUNABLES = removed_tunables

        for (name, value) in properties_mapping.items():
            def prop_getter(prop_name):
                prop = getattr(self, prop_name, None)
                prop_value = prop() if ismethod(prop) else prop

                return classproperty(lambda cls: prop_value)

            setattr(_InteractionTuningClass, name, prop_getter(value))

        lock_instance_tunables(_InteractionTuningClass, **locked_tunables)
        _InteractionTuningClass.__name__ = self.interaction_name
        return _InteractionTuningClass


class CommandInteractionTuningData(PythonBasedInteractionData):
    @constproperty
    def class_base():
        return CommandImmediateSuperInteraction

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test())
        base_tests.append(self.get_identity_test())
        base_tests.append(self.get_trait_blacklist())
        base_tests.append(self.get_zone_test())
        base_tests.append(self.get_home_region_test())

        return TestList(base_tests)


class PickerInteractionTuningData(PythonBasedInteractionData):
    FACTORY_TUNABLES = {
        'sim_picker': UiSimPicker.TunableFactory(),
        'picker_icon': OptionalTunable(tunable=TunableIconVariant()),
    }

    @constproperty
    def class_base():
        return HomeWorldPickerInteraction

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.Actor, is_npc=False))

        return TestList(base_tests)

    @property
    def sim_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.PickedSim))
        base_tests.append(self.get_trait_blacklist(participant=ParticipantType.PickedSim))
        base_tests.append(self.get_zone_test(participant=ParticipantType.PickedSim))
        base_tests.append(self.get_home_region_test(participant=ParticipantType.PickedSim))

        return CompoundTestList([TestList(base_tests)])

    @constproperty
    def locked_args() -> dict:
        locked_args = dict()
        locked_args['include_actor_sim'] = False
        locked_args['include_uninstantiated_sims'] = True

        return locked_args

    @constproperty
    def properties_mapping() -> dict:
        properties_mapping = dict()
        properties_mapping['sim_tests'] = 'sim_tests'
        properties_mapping['_icon'] = 'picker_icon'
        properties_mapping['picker_dialog'] = 'sim_picker'

        return properties_mapping


class _WorldListInteractionTuningDataBase(PythonBasedInteractionData):
    FACTORY_TUNABLES = {
        'picker_dialog': UiItemPicker.TunableFactory(),
        'picker_interaction_name': TunableLocalizedStringFactory(),
        'picker_description': TunableLocalizedStringFactory(),
        'disabled_interaction_behaviour': OptionalTunable(
            tunable=TunableTuple(disable_tooltip=OptionalTunable(TunableLocalizedStringFactory())),
            disabled_name='do_not_show',
            enabled_name='show_interactions',
        ),
        'no_worlds_available_tooltip': OptionalTunable(TunableLocalizedStringFactory())
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
            return text(region_text, *tokens)

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

    def _create_picker_item(self, target_world: HomeWorldIds):
        args = dict()
        args['continuation'] = (self._create_continuation(self.home_world, target_world),)
        args['icon'] = target_world.pie_menu_icon
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


class SoftFilterInteractionTuningData(PythonBasedInteractionData):
    _SUB_INTERACTION_CACHE = defaultdict(dict)
    FACTORY_TUNABLES = {
        'disabled_interaction_behaviour': OptionalTunable(
            tunable=TunableTuple(
                base=TunableLocalizedStringFactory(),
                tooltip_reason_mapping=TunableMapping(
                    key_name='toggle_value',
                    key_type=Tunable(tunable_type=bool, default=False),
                    value_name='display_text',
                    value_type=TunableLocalizedStringFactory()
                )
            ),
            disabled_name='do_not_show',
            enabled_name='show_interactions',
        ),
        'setting_value_mapping': TunableMapping(
            key_type=Tunable(tunable_type=bool, default=False),
            key_name='setting_value',
            value_type=TunableTuple(
                text=TunableLocalizedStringFactory(),
                pie_menu_icon=OptionalTunable(TunableIconVariant())
            ),
            value_name='display_data',
        ),
        'picker_dialog': UiItemPicker.TunableFactory(),
    }

    @constproperty
    def properties_mapping() -> dict:
        properties_mapping = dict()
        properties_mapping['possible_actions'] = 'possible_actions'
        properties_mapping['picker_dialog'] = 'custom_picker_dialog'

        return properties_mapping

    @constproperty
    def class_base():
        return SoftTogglePickerInteraction

    @classproperty
    def sub_interaction_cache(cls) -> Dict[HomeWorldIds, Dict[bool, ImmediateSuperInteraction]]:
        return cls._SUB_INTERACTION_CACHE

    @staticmethod
    def _register_interaction(interaction_cls, interaction_data):
        affordance_manager = get_instance_manager(Types.INTERACTION)
        resource_key = get_resource_key(interaction_data[1], Types.INTERACTION)

        affordance_manager.register_tuned_class(interaction_cls, resource_key)

    def _get_sub_interaction_name(self, toggle_value: bool):
        suffix = {True: 'On', False: 'Off'}[toggle_value]
        func = TunableInteractionName._Wrapper._get_hash_for_name

        return func(self.interaction_name, suffix)

    def _create_sub_interaction(self, toggle_value: bool):
        interaction_data = self._get_sub_interaction_name(toggle_value)

        class _ToggleSettingImmediateSuperInteraction(ToggleSettingImmediateSuperInteraction):
            pass

        locked_args = dict()
        locked_args['target_home_world'] = self.home_world
        locked_args['toggle_value'] = toggle_value
        _ToggleSettingImmediateSuperInteraction.__name__ = interaction_data[0]
        lock_instance_tunables(_ToggleSettingImmediateSuperInteraction, **locked_args)
        self._register_interaction(_ToggleSettingImmediateSuperInteraction, interaction_data)

        return _ToggleSettingImmediateSuperInteraction

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for home_world in HomeWorldIds:
            if home_world is HomeWorldIds.DEFAULT:
                continue

            for toggle_value in (True, False):
                self.sub_interaction_cache[self.home_world][toggle_value] = self._create_sub_interaction(toggle_value)

    def custom_picker_dialog(self):
        region_text = self.home_world.region_name()
        text = self.picker_dialog.text

        def new_text(*tokens):
            return text(region_text, *tokens)

        if not text:
            return self.picker_dialog
        return create_tunable_factory_with_overrides(self.picker_dialog, text=new_text)

    @property
    def global_tests(self):
        base_tests = list()
        base_tests.append(self.get_sim_info_test(participant=ParticipantType.Actor, is_npc=False))

        return TestList(base_tests)

    @classmethod
    def _create_continuation(cls, source_world: HomeWorldIds, toggle_value: bool):
        args = dict()
        args['actor'] = ParticipantType.Actor
        args['target'] = ParticipantType.Object
        args['affordance'] = cls.sub_interaction_cache[source_world][toggle_value]
        args['carry_target'] = None
        args['inventory_carry_target'] = None
        args['preserve_preferred_object'] = True
        args['preserve_target_part'] = False
        args['si_affordance_override'] = None

        return make_immutable_slots_class(**args)

    def get_display_data(self, toggle_value: bool):
        return self.setting_value_mapping[toggle_value]

    def _create_picker_item(self, toggle_value: bool):
        display_data = self.get_display_data(toggle_value)

        args = dict()
        args['continuation'] = (self._create_continuation(self.home_world, toggle_value),)
        args['item_description'] = None
        args['item_tooltip'] = None
        args['localization_tokens'] = None
        args['name'] = display_data.text
        args['icon'] = display_data.pie_menu_icon

        tests = self.get_enabled_tests(toggle_value)
        if self.disabled_interaction_behaviour:
            args['enable_tests'] = tests
            args['disable_tooltip'] = self.get_disabled_tooltip(toggle_value)
            args['visibility_tests'] = None
        else:
            args['enable_tests'] = None
            args['disable_tooltip'] = None
            args['visibility_tests'] = tests

        return construct_auto_init_factory(InteractionPickerItem, **args)

    def get_disabled_tooltip(self, toggle_value: bool):
        disabled_interaction_behaviour = self.disabled_interaction_behaviour
        base = disabled_interaction_behaviour.base
        tooltip_reason = disabled_interaction_behaviour.tooltip_reason_mapping[toggle_value]()
        region_name = self.home_world.region_name()

        return lambda *tokens: base(region_name, tooltip_reason, *tokens)

    def get_enabled_tests(self, toggle_value: bool):
        base_tests = list()
        base_tests.append(self.get_soft_filter_toggle_test(self.home_world, toggle_value))

        return CompoundTestList([TestList(base_tests)])

    def possible_actions(self):
        return tuple(self._create_picker_item(toggle_value) for toggle_value in (True, False))


class NotificationSettingsInteractionTuningData(PythonBasedInteractionData):
    _SUB_INTERACTION_CACHE = defaultdict(dict)
    FACTORY_TUNABLES = {}


class InteractionData(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'command': CommandInteractionTuningData.TunableFactory(),
        'picker': PickerInteractionTuningData.TunableFactory(),
        'allow_world': AllowWorldInteractionTuningData.TunableFactory(),
        'disallow_world': DisallowWorldInteractionTuningData.TunableFactory(),
        'soft_filter': SoftFilterInteractionTuningData.TunableFactory(),
    }

    @staticmethod
    def _create_properties(inst, key: str):
        tuning_cls = getattr(inst, key, None)
        if not tuning_cls:
            return

        tuning = tuning_cls(inst.world_data)
        setattr(inst, f'{key}_data', tuning)

    def __init__(self, world_data, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._world_data = world_data
        for key in self.forwarded_properties:
            self._create_properties(self, key)

    @property
    def forwarded_properties(self):
        return tuple(InteractionData.FACTORY_TUNABLES.keys())

    @property
    def world_data(self):
        return self._world_data

    def __iter__(self):
        for prop in self.forwarded_properties:
            yield getattr(self, f'{prop}_data', None)

    @property
    def interaction_target_mapping(self) -> Dict[InteractionTargetType, List[InteractionRegistryData]]:
        mapping = defaultdict(list)

        for interaction_data in self:
            if not interaction_data:
                continue

            mapping[interaction_data.injection_target].append(interaction_data.interaction_data)

        return {**mapping}

    def inject(self) -> Dict[InteractionTargetType, int]:
        mapping = defaultdict(int)

        for (target, affordance_infos) in self.interaction_target_mapping.items():
            mapping[target] += target.update_and_register_affordances(*affordance_infos)

        return {**mapping}

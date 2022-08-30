#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Dict

# miscellaneous
from services import get_instance_manager

# sim4 imports
from sims4.resources import Types, get_resource_key
from sims4.utils import classproperty, constproperty
from sims4.tuning.instances import lock_instance_tunables

# interaction imports
from interactions import ParticipantType
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.picker.interaction_picker import InteractionPickerItem

# event testing imports
from event_testing.tests import CompoundTestList

# ui imports
from ui.ui_dialog_picker import UiItemPicker

# local imports
from kuttoe_home_regions.utils import construct_auto_init_factory, make_immutable_slots_class
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides
from kuttoe_home_regions.interactions import BooleanSettingTogglePickerInteraction
from kuttoe_home_regions.interactions import BooleanToggleSettingImmediateSuperInteraction
from kuttoe_home_regions.snippets.disabled_interation_behaviour import TunableDisabledInteractionBehaviourSnippet
from kuttoe_home_regions.snippets.disabled_interation_behaviour import DisabledInteractionBehaviour
from kuttoe_home_regions.snippets.setting_value_mapping import TunableSettingValue
from kuttoe_home_regions.tunable import TunableInteractionName
from kuttoe_home_regions.tunable.python_based_interaction_data import PythonBasedInteractionWithoutRegionData


#######################################################################################################################
#  Toggle Base Classes                                                                                                #
#######################################################################################################################


class _ToggleInteractionTuningDataBase:
    __CACHE = dict()
    FACTORY_TUNABLES = {
        'disabled_interaction_behaviour': TunableDisabledInteractionBehaviourSnippet(),
        'setting_value_mapping': TunableSettingValue(),
        'picker_dialog': UiItemPicker.TunableFactory(),
    }

    @constproperty
    def properties_mapping() -> dict:
        properties_mapping = dict()
        properties_mapping['possible_actions'] = 'possible_actions'
        properties_mapping['picker_dialog'] = 'custom_picker_dialog'

        return properties_mapping

    @staticmethod
    def _register_interaction(interaction_cls, interaction_data):
        affordance_manager = get_instance_manager(Types.INTERACTION)
        resource_key = get_resource_key(interaction_data[1], Types.INTERACTION)

        affordance_manager.register_tuned_class(interaction_cls, resource_key)

    def _get_sub_interaction_name(self, toggle_value: bool):
        suffix = {True: 'On', False: 'Off'}[toggle_value]
        func = TunableInteractionName._Wrapper._get_hash_for_name

        return func(self.interaction_name_base.interaction_name_base, suffix)

    def _create_sub_interaction(self, toggle_value: bool):
        interaction_data = self._get_sub_interaction_name(toggle_value)
        if interaction_data[1] in self.__CACHE:
            return self.__CACHE[interaction_data[1]]
        base_class = self.sub_interaction_base_class

        class _ToggleSettingImmediateSuperInteraction(base_class):
            pass

        locked_args = dict()
        locked_args.update(self.sub_interaction_locked_args)
        locked_args['toggle_value'] = toggle_value
        _ToggleSettingImmediateSuperInteraction.__name__ = interaction_data[0]
        lock_instance_tunables(_ToggleSettingImmediateSuperInteraction, **locked_args)
        self._register_interaction(_ToggleSettingImmediateSuperInteraction, interaction_data)

        return self.__CACHE.setdefault(interaction_data[1], _ToggleSettingImmediateSuperInteraction)

    @property
    def additional_picker_item_args(self):
        return {'args': (), 'kwargs': {}}

    def possible_actions(self):
        additional_picker_item_args = self.additional_picker_item_args or dict()
        args = additional_picker_item_args.get('args', tuple())
        kwargs = additional_picker_item_args.get('kwargs', dict())

        return tuple(self._create_picker_item(toggle_value, *args, **kwargs) for toggle_value in (True, False))

    @classmethod
    def _create_continuation(cls, toggle_value: bool, *additional_args, **kwargs):
        args = dict()
        args['actor'] = ParticipantType.Actor
        args['target'] = ParticipantType.Object
        args['affordance'] = cls._get_continuation_affordance(toggle_value, *additional_args, **kwargs)
        args['carry_target'] = None
        args['inventory_carry_target'] = None
        args['preserve_preferred_object'] = True
        args['preserve_target_part'] = False
        args['si_affordance_override'] = None

        return make_immutable_slots_class(**args)

    @classmethod
    def create_picker_item(cls, **kwargs):
        kwargs.setdefault('item_description', None)
        kwargs.setdefault('item_tooltip', None)
        kwargs.setdefault('localization_tokens', None)
        kwargs.setdefault('enable_tests', None)
        kwargs.setdefault('disable_tooltip', None)
        kwargs.setdefault('enable_tests', None)
        kwargs.setdefault('disable_tooltip', None)
        kwargs.setdefault('visibility_tests', None)

        return construct_auto_init_factory(InteractionPickerItem, **kwargs)

    def get_display_data(self, toggle_value: bool):
        return self.setting_value_mapping.get_display_data(toggle_value)

    def get_display_data_args(self, toggle_value: bool):
        display_data = self.get_display_data(toggle_value)

        return dict(name=display_data.text, icon=display_data.pie_menu_icon)

    def get_disabled_interaction_behaviour(self, toggle_value: bool):
        dib: DisabledInteractionBehaviour = self.disabled_interaction_behaviour
        tokens = self.additional_disable_token_reasons or tuple()
        tests = self.get_enabled_tests(toggle_value)

        if not dib:
            return dict(visibility_tests=tests)
        return dib.value(toggle_value, tests, tokens)

    def _create_picker_item(self, toggle_value: bool, *additional_args, **kwargs):
        args = dict()
        args['continuation'] = (self._create_continuation(toggle_value, *additional_args, **kwargs),)
        args.update(self.get_display_data_args(toggle_value))
        args.update(self.get_disabled_interaction_behaviour(toggle_value))

        return self.create_picker_item(**args)

    def get_enabled_tests(self, toggle_value: bool):
        return CompoundTestList()

    @property
    def additional_disable_token_reasons(self):
        return ()

    @property
    def additional_picker_dialog_tokens(self):
        return ()

    def custom_picker_dialog(self):
        additional_tokens = self.additional_picker_dialog_tokens
        text = self.picker_dialog.text

        def new_text(*tokens):
            return text(*additional_tokens, *tokens)

        if not text:
            return self.picker_dialog
        return create_tunable_factory_with_overrides(self.picker_dialog, text=new_text)


class _BooleanToggleInteractionTuningDataBase(_ToggleInteractionTuningDataBase,
                                              PythonBasedInteractionWithoutRegionData):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls._SUB_INTERACTION_CACHE = dict()

    @classproperty
    def sub_interaction_cache(cls) -> Dict[bool, ImmediateSuperInteraction]:
        return cls._SUB_INTERACTION_CACHE

    @constproperty
    def class_base():
        return BooleanSettingTogglePickerInteraction

    @constproperty
    def sub_interaction_base_class():
        return BooleanToggleSettingImmediateSuperInteraction

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for toggle_value in (True, False):
            self.sub_interaction_cache.setdefault(toggle_value, self._create_sub_interaction(toggle_value))

    @property
    def interaction_name_suffix(self):
        return None

    @property
    def sub_interaction_locked_args(self):
        locked_args = dict()

        locked_args['command_name'] = self.command_name
        return locked_args

    @classmethod
    def _get_continuation_affordance(cls, toggle_value: bool):
        return cls.sub_interaction_cache[toggle_value]

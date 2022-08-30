#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Iterable, Dict, Any
from inspect import ismethod

# miscellaneous
from services import get_instance_manager

# sim4 imports
from sims4.resources import Types
from sims4.utils import classproperty, constproperty
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, Tunable
from sims4.tuning.tunable import TunablePackSafeReference, TunableEnumEntry, TunableRange, TunableMapping
from sims4.tuning.instances import lock_instance_tunables
from sims4.localization import TunableLocalizedStringFactory

# interaction imports
from interactions import TargetType, ParticipantType
from interactions.utils.localization_tokens import _TunableObjectLocalizationTokenFormatterSingle, LocalizationTokens
from interactions.utils.tunable_icon import TunableIconVariant
from interactions.base.immediate_interaction import ImmediateSuperInteraction

# tunable utils imports
from tunable_utils.tunable_object_generator import _ObjectGeneratorFromParticipant

# local imports
from kuttoe_home_regions.utils import construct_auto_init_factory, make_immutable_slots_class
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.ui import InteractionType, NotificationType
from kuttoe_home_regions.tests import _TestSetMixin
from kuttoe_home_regions.interactions import _DisplayNotificationMixin
from kuttoe_home_regions.tunable import _InteractionTypeMixin


#######################################################################################################################
# Tunable Python-Generated Interaction Data                                                                           #
#######################################################################################################################


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
        properties_mapping['_pie_menu_priority'] = 'pie_menu_priority'
        properties_mapping['display_name'] = 'interaction_display_name'
        properties_mapping['notification'] = 'notification'
        properties_mapping['target_home_world'] = 'home_world'
        properties_mapping['pie_menu_icon'] = 'pie_menu_icon'

        return properties_mapping

    @property
    def category(self):
        return self.interaction_category

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


class PythonBasedInteractionWithRegionData(PythonBasedInteractionData):
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
    def home_world(self) -> HomeWorldIds:
        return self.world_data.home_world

    @property
    def command_name(self):
        return self.home_world.command_name


class InteractionDisplayNameMap(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'notification_type'
        kwargs['key_type'] = TunableEnumEntry(tunable_type=NotificationType, default=NotificationType.SUCCESS)
        kwargs['value_name'] = 'interaction_display_name'
        kwargs['value_type'] = TunableLocalizedStringFactory()
        super().__init__(*args, **kwargs)


class PythonBasedInteractionWithoutRegionData(PythonBasedInteractionData):
    FACTORY_TUNABLES = {
        'interaction_display_name': TunableLocalizedStringFactory(),
        'pie_menu_icon': OptionalTunable(TunableIconVariant()),
        'command_name': Tunable(tunable_type=str, default=None, allow_empty=False),
        'pie_menu_priority': TunableRange(tunable_type=int, maximum=10, default=1),
    }

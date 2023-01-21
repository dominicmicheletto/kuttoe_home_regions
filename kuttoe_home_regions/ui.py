"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details UI elements.
"""

#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from collections import namedtuple

# miscellaneous
import enum

# sim imports
from sims.sim_info import SimInfo

# interaction imports
from interactions import ParticipantType
from interactions.base.super_interaction import SuperInteraction
from interactions.utils.tunable_icon import TunableIconVariant

# sim4 imports
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, Tunable, TunableVariant
from sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning
from sims4.utils import classproperty

# ui imports
from ui.ui_dialog_notification import UiDialogNotification

# local imports
from kuttoe_home_regions.enum import DynamicFactoryEnumMetaclass, EnumItemFactory, EnumItem
from kuttoe_home_regions.utils import enum_entry_factory, SnippetMixin


#######################################################################################################################
#  Notification Colour Code                                                                                           #
#######################################################################################################################


_NotificationInfo = namedtuple('_NotificationInfo', ['information_level', 'urgency', 'visual_type'])


class NotificationInfo(EnumItemFactory):
    FACTORY_TYPE = _NotificationInfo
    _VALUE_MAPPING = {
        'information_level': UiDialogNotification.UiDialogNotificationLevel,
        'urgency': UiDialogNotification.UiDialogNotificationUrgency,
        'visual_type': UiDialogNotification.UiDialogNotificationVisualType,
    }

    def __init__(self, *args, **kwargs):
        _base = Tunable(tunable_type=str, default='', allow_empty=False, needs_tuning=True)

        kwargs['information_level'] = _base
        kwargs['urgency'] = _base
        kwargs['visual_type'] = _base
        super().__init__(*args, **kwargs)

    def load_etree_node(self, node, source, expect_error):
        value = super().load_etree_node(node, source, expect_error)
        enum_info_raw = {name: self._VALUE_MAPPING[name][value] for (name, value) in value.enum_info._asdict().items()}
        enum_info = self.FACTORY_TYPE(**enum_info_raw)

        return EnumItem(enum_name=value.enum_name, enum_value=value.enum_value, enum_info=enum_info)


@enum_entry_factory(default='INVALID', invalid=('INVALID', ))
class NotificationColour(enum.Int, metaclass=DynamicFactoryEnumMetaclass, factory_cls=NotificationInfo):
    INVALID = -1

    @property
    def as_dict(self):
        return self.factory_value._asdict()


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


@enum_entry_factory(default='NONE', invalid=())
class InteractionType(enum.Int):
    NONE = 0
    COMMAND = 1
    PICKER = 2
    SETTING_WORLD_PICKER = 3
    SOFT_FILTER = 4
    WORLD_SELECTION = 5
    TOURISTS_TOGGLE = 6
    NOTIFICATION = 7


@enum_entry_factory(default='SUCCESS', invalid=())
class NotificationType(enum.Int):
    SUCCESS = 0
    SETTINGS_CHANGED = 1
    WORLD_EXEMPTION = 2
    NOTIFICATION_SETTINGS = 3

    @classproperty
    def exported_values(cls): return frozenset({cls.SUCCESS, cls.SETTINGS_CHANGED, cls.WORLD_EXEMPTION})

    @classproperty
    def exported_values_enum(cls): return cls.to_enum_entry(invalid=tuple(set(cls) - cls.exported_values))

    @classproperty
    def notifications(cls):
        return ', '.join(notif.name for notif in cls if notif is not cls.exported_values)

    @property
    def setting_name(self) -> str:
        return 'Show{}Notification'.format(self.name.title().replace('_', ''))

    @property
    def pretty_name(self) -> str:
        return self.name.lower()

#######################################################################################################################
#  Icon Definition Variant Definition                                                                                 #
#######################################################################################################################


class TunableIconDefinitionVariant(TunableVariant):
    def __init__(self, *args, **kwargs):
        kwargs['enabled'] = TunableIconVariant()
        kwargs['locked_args'] = dict(disabled=None, use_icon_from_interaction=True)

        super().__init__(*args, **kwargs)

#######################################################################################################################
#  Notification Tuning                                                                                                #
#######################################################################################################################


class _NotificationData(
    namedtuple('_NotificationData', ('sim_infos', 'regions', 'toggle_value', ), defaults=(tuple(), tuple(), None))
):
    @staticmethod
    def _sort_sim_infos(*sim_infos: SimInfo):
        if len(sim_infos) <= 2:
            return sim_infos

        return sorted(sim_infos, key=lambda sim_info: sim_info.gender, reverse=True)

    def __new__(cls, *args, **kwargs):
        if 'sim_infos' in kwargs:
            kwargs['sim_infos'] = tuple(cls._sort_sim_infos(*kwargs.pop('sim_infos')))

        return super(__class__, cls).__new__(cls, *args, **kwargs)

    @property
    def has_sim_infos(self): return bool(self.sim_infos)

    @property
    def has_regions(self): return bool(self.regions)

    @property
    def has_toggle_value(self): return self.toggle_value is not None


class Notification(HasTunableFactory, AutoFactoryInit, SnippetMixin, snippet_name='custom_notification'):
    FACTORY_TUNABLES = {
        'text': OptionalTunable(tunable=TunableLocalizedStringFactory()),
        'title': OptionalTunable(tunable=TunableLocalizedStringFactory()),
        'icon': TunableIconDefinitionVariant(),
        'colour': NotificationColour.to_enum_entry(),
    }

    def __init__(self, interaction: SuperInteraction, interaction_type: InteractionType, **kwargs):
        factory_kwargs = dict()
        for arg_name in self.FACTORY_TUNABLES:
            factory_kwargs[arg_name] = kwargs.pop(arg_name)

        super().__init__(**factory_kwargs)
        self._notification_data = _NotificationData(**kwargs)
        self._interaction = interaction
        self._interaction_type = interaction_type

    def __getattr__(self, name: str):
        if name in self._notification_data._fields:
            return getattr(self._notification_data, name)

    @property
    def interaction_type(self): return self._interaction_type

    @property
    def interaction(self): return self._interaction

    def get_participant(self, participant_type=ParticipantType.TargetSim):
        recipients = self.interaction.get_participants(participant_type)

        if not recipients:
            return None
        return recipients[0]

    @property
    def recipient(self):
        if self._interaction_type is InteractionType.PICKER:
            return self.get_participant(ParticipantType.PickedSim)
        return self.get_participant() or self.get_participant(ParticipantType.Actor)

    @property
    def sim_name_list(self):
        sim_names = tuple(LocalizationHelperTuning.get_sim_full_name(sim_info) for sim_info in self.sim_infos)

        return LocalizationHelperTuning.get_bulleted_list(None, *sim_names)

    @property
    def region_list(self):
        region_names = tuple(world.region_name() for world in self.regions)

        return LocalizationHelperTuning.get_bulleted_list(None, *region_names)

    @property
    def display_name(self): return self._interaction._get_name()

    @property
    def tokens(self):
        display_name = self.display_name

        if self._interaction_type is InteractionType.PICKER:
            count = len(self.sim_infos)
            return (count, display_name, self.sim_name_list, *self.sim_infos)
        elif self._interaction_type is InteractionType.WORLD_SELECTION:
            count = len(self.regions)
            return count, self.recipient, self.region_list
        elif self._interaction_type is InteractionType.NOTIFICATION:
            return self.toggle_value,
        return self.recipient, display_name

    @property
    def resolver(self): return self._interaction.get_resolver()

    @property
    def notification_icon(self):
        if self.icon is True:
            icon = self._interaction.get_pie_menu_icon_info()

            return lambda *_, **__: icon if icon is not None else icon
        return self.icon

    @property
    def colour_properties(self) -> dict: return self.colour.as_dict

    def _get_text_with_tokens(self, attr_name: str):
        attr = getattr(self, attr_name, None)
        return (lambda *tokens: attr(*self.tokens, *tokens)) if attr else None

    @property
    def params(self):
        params = dict()
        params['text'] = self._get_text_with_tokens('text')
        params['title'] = self._get_text_with_tokens('title')
        params['icon'] = self.notification_icon
        params.update(self.colour_properties)

        return params

    @property
    def dialog(self): return UiDialogNotification.TunableFactory().default(None, resolver=self.resolver, **self.params)

#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################


(TunableNotificationSnippetReference, TunableNotificationSnippet) = Notification._snippet
__all__ = (
    'TunableNotificationSnippetReference', 'TunableNotificationSnippet',
    'Notification', 'NotificationType',
    'InteractionType',
)

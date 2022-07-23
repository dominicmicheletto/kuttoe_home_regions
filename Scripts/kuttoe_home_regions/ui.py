#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from collections import namedtuple

# miscellaneous
import enum

# interaction imports
from interactions import ParticipantType
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.utils.tunable_icon import TunableIconVariant

# sim4 imports
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, Tunable, TunableEnumEntry
from sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning
from sims4.utils import classproperty

# ui imports
from ui.ui_dialog_notification import UiDialogNotification

# local imports
from kuttoe_home_regions.enum import DynamicFactoryEnumMetaclass, EnumItemFactory, EnumItem

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


class NotificationColour(enum.Int, metaclass=DynamicFactoryEnumMetaclass, factory_cls=NotificationInfo):
    INVALID = -1

    @property
    def as_dict(self):
        return self.factory_value._asdict()


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


class InteractionType(enum.Int):
    NONE = 0
    COMMAND = 1
    PICKER = 2
    SETTING_WORLD_PICKER = 3
    SOFT_FILTER = 4


class NotificationType(enum.Int):
    SUCCESS = 0
    SETTINGS_CHANGED = 1

    @classproperty
    def notifications(cls):
        return ', '.join(notif.name for notif in cls)

    @property
    def setting_name(self) -> str:
        return 'Show{}Notification'.format(self.name.title().replace('_', ''))

    @property
    def pretty_name(self) -> str:
        return self.name.lower()


#######################################################################################################################
#  Notification Tuning                                                                                                #
#######################################################################################################################


class Notification(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'text': OptionalTunable(tunable=TunableLocalizedStringFactory()),
        'title': OptionalTunable(tunable=TunableLocalizedStringFactory()),
        'icon': OptionalTunable(tunable=TunableIconVariant()),
        'use_icon_from_interaction': Tunable(tunable_type=bool, default=False),
        'colour': TunableEnumEntry(tunable_type=NotificationColour, default=NotificationColour.INVALID,
                                   invalid_enums=(NotificationColour.INVALID, )),
    }

    def __init__(
            self,
            interaction: ImmediateSuperInteraction,
            interaction_type: InteractionType,
            additional_tokens=(),
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._interaction = interaction
        self._interaction_type = interaction_type
        self._additional_tokens = additional_tokens or tuple()

    @property
    def interaction_type(self):
        return self._interaction_type

    @property
    def additional_tokens(self):
        return self.additional_tokens

    @property
    def has_additional_tokens(self):
        return bool(self.additional_tokens)

    @property
    def interaction(self):
        return self._interaction

    def get_participant(self, participant_type=ParticipantType.TargetSim):
        recipients = self.interaction.get_participants(participant_type)

        if not recipients:
            return None
        return recipients[0]

    @property
    def recipient(self):
        if self._interaction_type == InteractionType.PICKER:
            return self.get_participant(ParticipantType.PickedSim)
        return self.get_participant() or self.get_participant(ParticipantType.Actor)

    @property
    def tokens(self):
        display_name = self.interaction.display_name()

        if self._interaction_type == InteractionType.PICKER:
            count = len(self._additional_tokens)
            return count, display_name, LocalizationHelperTuning.get_bulleted_list(None, *self._additional_tokens)
        return self.recipient, display_name

    @property
    def resolver(self):
        return self.interaction.get_resolver()

    @property
    def notification_icon(self):
        if self.use_icon_from_interaction:
            return self.interaction.pie_menu_icon
        return self.icon

    @property
    def colour_properties(self) -> dict:
        return self.colour.as_dict

    @property
    def params(self):
        text = self.text(*self.tokens)

        params = dict()
        params['text'] = lambda *_, **__: text
        params['title'] = self.title
        params['icon'] = self.notification_icon
        params.update(self.colour_properties)

        return params

    @property
    def dialog(self):
        return UiDialogNotification.TunableFactory().default(None, resolver=self.resolver, **self.params)

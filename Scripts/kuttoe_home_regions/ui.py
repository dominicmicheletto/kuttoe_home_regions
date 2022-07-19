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
from sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning

# sim4 imports
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, Tunable, TunableEnumEntry

# ui imports
from ui.ui_dialog_notification import UiDialogNotification


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


class InteractionType(enum.Int):
    NONE = 0
    COMMAND = 1
    PICKER = 2
    SETTING_WORLD_PICKER = 3


class NotificationType(enum.Int):
    SUCCESS = 0
    SETTINGS_CHANGED = 1

    @property
    def setting_name(self) -> str:
        return 'Show{}Notification'.format(self.name.title().replace('_', ''))


class NotificationColour(enum.Int):
    NotificationInfo = namedtuple('NotificationInfo', ['information_level', 'urgency', 'visual_type'])
    _VALUES_MAPPING = {
        0: NotificationInfo('PLAYER', 'DEFAULT', 'INFORMATION'),
        1: NotificationInfo('SIM', 'DEFAULT', 'INFORMATION'),
        2: NotificationInfo('SIM', 'DEFAULT', 'SPECIAL_MOMENT'),
        3: NotificationInfo('PLAYER', 'URGENT', 'INFORMATION'),
    }

    GREEN = 0
    BLUE = 1
    PURPLE = 2
    ORANGE = 3

    def _get_enum_value(self, enum_base, enum_key):
        return enum_base[getattr(self._notification_info_value, enum_key)]

    @property
    def _notification_info_value(self):
        return self._VALUES_MAPPING[self.value]

    @property
    def information_level(self):
        return self._get_enum_value(UiDialogNotification.UiDialogNotificationLevel, 'information_level')

    @property
    def urgency(self):
        return self._get_enum_value(UiDialogNotification.UiDialogNotificationUrgency, 'urgency')

    @property
    def visual_type(self):
        return self._get_enum_value(UiDialogNotification.UiDialogNotificationVisualType, 'visual_type')

    @property
    def notification_info(self):
        return self.NotificationInfo(self.information_level, self.urgency, self.visual_type)

    @property
    def as_dict(self):
        return self.notification_info._asdict()


#######################################################################################################################
#  Notification Tuning                                                                                                #
#######################################################################################################################


class Notification(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'text': OptionalTunable(tunable=TunableLocalizedStringFactory()),
        'title': OptionalTunable(tunable=TunableLocalizedStringFactory()),
        'icon': OptionalTunable(tunable=TunableIconVariant()),
        'use_icon_from_interaction': Tunable(tunable_type=bool, default=False),
        'colour': TunableEnumEntry(tunable_type=NotificationColour, default=NotificationColour.BLUE),
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

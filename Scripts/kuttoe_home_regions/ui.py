#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from collections import namedtuple, defaultdict
from typing import Dict

# miscellaneous
import enum
from snippets import define_snippet

# sim imports
from sims.sim_info import SimInfo
from sims.sim_info_types import Gender

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

    @staticmethod
    def _sort_sim_infos(*sim_infos: SimInfo):
        if len(sim_infos) <= 2:
            return sim_infos

        sims: Dict[Gender, list] = defaultdict(list)
        for sim_info in sim_infos:
            sims[sim_info.gender].append(sim_info)

        sims_list = list()
        if Gender.FEMALE in sims:
            sims_list.append(sims[Gender.FEMALE].pop())
        sims_list.extend(sims[Gender.MALE])
        sims_list.extend(sims[Gender.FEMALE])
        return tuple(sims_list)

    def __init__(
            self,
            interaction: ImmediateSuperInteraction,
            interaction_type: InteractionType,
            sim_infos=(),
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._interaction = interaction
        self._interaction_type = interaction_type
        self._sim_infos = self._sort_sim_infos(*sim_infos)

    @property
    def interaction_type(self):
        return self._interaction_type

    @property
    def has_sim_infos(self):
        return bool(self.sim_infos)

    @property
    def sim_infos(self):
        return self._sim_infos

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
    def sim_name_list(self):
        sim_names = tuple(LocalizationHelperTuning.get_sim_full_name(sim_info) for sim_info in self.sim_infos)

        return LocalizationHelperTuning.get_bulleted_list(None, *sim_names)

    @property
    def tokens(self):
        display_name = self.interaction.display_name()

        if self._interaction_type == InteractionType.PICKER:
            count = len(self.sim_infos)
            return (count, display_name, self.sim_name_list, *self.sim_infos)
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
    def dialog(self):
        return UiDialogNotification.TunableFactory().default(None, resolver=self.resolver, **self.params)


(
    TunableNotificationSnippetReference, TunableNotificationSnippet
) = define_snippet('custom_notification', Notification.TunableFactory())

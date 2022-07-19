#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# miscellaneous
import services

# sim4 imports
from sims4.utils import classproperty
from sims4.tuning.tunable import OptionalTunable, TunableEnumEntry
from sims4.tuning.instances import lock_instance_tunables
from sims4.localization import LocalizationHelperTuning
from sims4.commands import execute as execute_command

# interaction imports
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.base.picker_interaction import SimPickerInteraction
from interactions.picker.interaction_picker import InteractionPickerSuperInteraction

# sim imports
from sims.sim_info_manager import SimInfoManager

# local imports
from kuttoe_home_regions.utils import make_do_command, CommandsList
from kuttoe_home_regions.home_worlds import HomeWorldIds
from kuttoe_home_regions.commands import AlterType
from kuttoe_home_regions.ui import NotificationType, Notification, InteractionType


#######################################################################################################################
# Mixins                                                                                                              #
#######################################################################################################################


class _DisplayNotificationMixin:
    INSTANCE_TUNABLES = {
        'interaction_type': TunableEnumEntry(tunable_type=InteractionType, default=InteractionType.COMMAND),
        'notification': OptionalTunable(tunable=Notification.TunableFactory())
    }
    FACTORY_TUNABLES = {k: v for (k, v) in INSTANCE_TUNABLES.items() if k != 'interaction_type'}

    @property
    def has_notification(self):
        return self.notification is not None

    def display_notification(self, *additional_tokens, notification_type=NotificationType.SUCCESS):
        from kuttoe_home_regions.settings import Settings

        if not self.has_notification or not Settings.should_show_notification[notification_type]:
            return

        dialog = self.notification(self, self.interaction_type, additional_tokens=additional_tokens).dialog
        dialog.show_dialog()


class _TargetHomeWorldMixin:
    INSTANCE_TUNABLES = {
        'target_home_world': TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT)
    }
    FACTORY_TUNABLES = INSTANCE_TUNABLES

    @classproperty
    def command_name(cls) -> str:
        return cls.target_home_world.command_name


#######################################################################################################################
# Picker Interactions                                                                                                 #
#######################################################################################################################


class HomeWorldPickerInteraction(_DisplayNotificationMixin, _TargetHomeWorldMixin, SimPickerInteraction):
    @classproperty
    def client_id(cls):
        return services.client_manager().get_first_client_id()

    @staticmethod
    def create_sim_token(sim_id):
        manager: SimInfoManager = services.sim_info_manager()
        return LocalizationHelperTuning.get_sim_full_name(manager.get(sim_id))

    @classmethod
    def create_tokens_list(cls, *sim_ids):
        return tuple(cls.create_sim_token(sim_id) for sim_id in sim_ids)

    def _push_continuations(self, *args, **kwargs):
        sim_ids = args[0]
        for sim_id in sim_ids:
            execute_command('{} {}'.format(self.command_name, sim_id), self.client_id)

        self._set_inventory_carry_target()
        super()._push_continuations(*args, **kwargs)

        self.display_notification(*self.create_tokens_list(*sim_ids))


class WorldListPickerInteraction(_DisplayNotificationMixin, _TargetHomeWorldMixin, InteractionPickerSuperInteraction):
    REMOVE_INSTANCE_TUNABLES = ('possible_actions', )

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        if picked_choice is None or len(picked_choice) == 0:
            return

        for choice in picked_choice:
            self.push_tunable_continuation(choice.continuation)

        self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED)

    def on_choice_selected(self, choice, **kwargs):
        return self.on_multi_choice_selected((choice, ), **kwargs)


#######################################################################################################################
# Immediate Interactions                                                                                              #
#######################################################################################################################


class CommandImmediateSuperInteraction(_DisplayNotificationMixin, _TargetHomeWorldMixin, ImmediateSuperInteraction):
    REMOVE_INSTANCE_TUNABLES = ('basic_extras', )

    @classproperty
    def command_arguments(cls):
        return CommandsList().add_participant()

    @classproperty
    def do_command(cls):
        return make_do_command(cls.command_name, *cls.command_arguments)

    @classproperty
    def basic_extras(cls):
        return (cls.do_command, )

    def _run_interaction_gen(self, timeline):
        super()._run_interaction_gen(timeline)

        self.display_notification()


class AlterWorldListImmediateSuperInteraction(_TargetHomeWorldMixin, ImmediateSuperInteraction):
    REMOVE_INSTANCE_TUNABLES = ('basic_extras',)

    INSTANCE_TUNABLES = {
        'alter_type': TunableEnumEntry(tunable_type=AlterType, default=AlterType.ALLOW_WORLD),
        'source_world': TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT)
    }

    @classproperty
    def command_name(cls) -> str:
        from kuttoe_home_regions.settings import Settings
        name = cls.alter_type.name.lower()
        base = getattr(Settings.COMMAND_NAME_BASES, name)

        return base(cls.source_world)[0]

    @classproperty
    def command_arguments(cls):
        return CommandsList().add_string(cls.target_home_world.name)

    @classproperty
    def do_command(cls):
        return make_do_command(cls.command_name, *cls.command_arguments)

    @classproperty
    def basic_extras(cls):
        return (cls.do_command,)


#######################################################################################################################
# Tuning Locking                                                                                                      #
#######################################################################################################################


lock_instance_tunables(HomeWorldPickerInteraction, interaction_type=InteractionType.PICKER)
lock_instance_tunables(CommandImmediateSuperInteraction, interaction_type=InteractionType.COMMAND)
lock_instance_tunables(WorldListPickerInteraction, interaction_type=InteractionType.SETTING_WORLD_PICKER)

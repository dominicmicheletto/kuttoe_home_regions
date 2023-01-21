"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the base for toggle interactions. These are simple interactions that display a picker that can have
a variety of known values and after a selection sends the value to a given console command.
"""


#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.tuning.tunable import Tunable
from sims4.commands import execute as execute_command
from sims4.utils import classproperty, flexmethod

# miscellaneous imports
from services import client_manager
from singletons import DEFAULT
from interactions.base.picker_interaction import PickerSuperInteraction

# local imports
from kuttoe_home_regions.interactions.mixins import DisplayNotificationMixin
from kuttoe_home_regions.tunable.toggle_item import TunableToggleEntrySnippet
from kuttoe_home_regions.tunable.toggle_item_picker import ToggleItemPicker
from kuttoe_home_regions.ui import InteractionType, NotificationType


#######################################################################################################################
#  Super Interactions                                                                                                 #
#######################################################################################################################

class ToggleSuperInteraction(PickerSuperInteraction, DisplayNotificationMixin):
    INSTANCE_TUNABLES = {
        'command_name': Tunable(tunable_type=str, default=None, allow_empty=False),
        'setting_key': Tunable(tunable_type=str, default=None, allow_empty=False),
        'picker_dialog': ToggleItemPicker()(),
        'toggle_items': TunableToggleEntrySnippet(),
    }

    @classproperty
    def client_id(cls):
        return client_manager().get_first_client_id()

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        yield from inst_or_cls.toggle_items(cls.setting_key).picker_rows_gen(resolver)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)

        return True

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass

    def on_choice_selected(self, picked_choice, **kwargs):
        if picked_choice is None or len(picked_choice) == 0:
            return

        execute_command(f'{self.command_name} {picked_choice}', self.client_id)
        self._display_notification()

    def _display_notification(self):
        self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED)


#######################################################################################################################
#  Instance Tunable Locking                                                                                           #
#######################################################################################################################

lock_instance_tunables(ToggleSuperInteraction, interaction_type=InteractionType.COMMAND)


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = ('ToggleSuperInteraction', )

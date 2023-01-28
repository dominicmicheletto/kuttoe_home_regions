"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details an interaction that resets all of Home Region's settings.
"""


#######################################################################################################################
# Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.localization import TunableLocalizedStringFactory
from sims4.tuning.tunable import OptionalTunable
from sims4.utils import classproperty

# miscellaneous imports
from ui.ui_dialog import UiEndSituationDialogOkCancel
from services import client_manager
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from os.path import basename

# local imports
from kuttoe_home_regions.interactions.mixins import DisplayNotificationMixin
from kuttoe_home_regions.ui import NotificationType, InteractionType
from kuttoe_home_regions.commands import kuttoe_reset_settings


#######################################################################################################################
# Super Interactions                                                                                                 #
#######################################################################################################################

class ResetSettingsImmediateSuperInteraction(ImmediateSuperInteraction, DisplayNotificationMixin):
    INSTANCE_TUNABLES = {
        'ok_cancel_dialog': UiEndSituationDialogOkCancel.TunableFactory(),
        'backup_text': OptionalTunable(TunableLocalizedStringFactory()),
    }

    @classproperty
    def client_id(cls): return client_manager().get_first_client_id()

    def get_backup_text(self, file_path: str):
        if file_path is None or self.backup_text is None:
            return None
        return self.backup_text(basename(file_path))

    def _on_response(self, dialog):
        # accepted -> backup
        # alt_accepted -> no backup
        # cancelled -> do nothing

        success = not dialog.canceled
        if success:
            backup_file_path = kuttoe_reset_settings(dialog.accepted, self.client_id)
            backup_text = self.get_backup_text(backup_file_path)

            self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED, backup_text=backup_text)
        return success

    def _run_interaction_gen(self, timeline):
        dialog = self.ok_cancel_dialog(None, self.get_resolver())
        dialog.show_dialog(on_response=self._on_response)

        return True


#######################################################################################################################
# Instance Tunable Locking                                                                                           #
#######################################################################################################################

lock_instance_tunables(ResetSettingsImmediateSuperInteraction, interaction_type=InteractionType.RESET_SETTINGS)

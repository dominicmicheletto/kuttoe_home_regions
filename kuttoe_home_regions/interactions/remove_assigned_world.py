"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details interactions that remove an assigned home world from Sims.
"""

#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.tuning.tunable import Tunable
from sims4.utils import classproperty, flexmethod
from sims4.commands import execute as execute_command

# interaction imports
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.base.picker_interaction import SimPickerInteraction

# miscellaneous imports
from services import client_manager, sim_info_manager

# local imports
from kuttoe_home_regions.interactions.mixins import DisplayNotificationMixin
from kuttoe_home_regions.ui import NotificationType, InteractionType


#######################################################################################################################
# Super Interactions                                                                                                  #
#######################################################################################################################


class RemoveAssignedWorldImmediateSuperInteraction(ImmediateSuperInteraction, DisplayNotificationMixin):
    def _run_interaction_gen(self, timeline):
        super()._run_interaction_gen(timeline)

        self.display_notification(notification_type=NotificationType.SUCCESS, sim_infos=(self.target, ))


class RemoveAssignedWorldPickerSuperInteration(SimPickerInteraction, DisplayNotificationMixin):
    COMMAND_NAME = Tunable(tunable_type=str, needs_tuning=True, default=None, allow_empty=False)

    @flexmethod
    def _use_ellipsized_name(cls, inst): return False

    @classproperty
    def command_name(cls): return cls.COMMAND_NAME

    @classproperty
    def client_id(cls): return client_manager().get_first_client_id()

    @staticmethod
    def get_sim_info(sim_id: int): return sim_info_manager().get(sim_id)

    @classmethod
    def get_sim_infos(cls, *sim_ids: int):
        return tuple(cls.get_sim_info(sim_id) for sim_id in sim_ids)

    def _push_continuations(self, *args, **kwargs):
        sim_ids = args[0]
        for sim_id in sim_ids:
            execute_command('{} {}'.format(self.command_name, sim_id), self.client_id)

        self._set_inventory_carry_target()
        super()._push_continuations(*args, **kwargs)

        self.display_notification(sim_infos=self.get_sim_infos(*sim_ids))

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass


#######################################################################################################################
# Instance Tunable Locking                                                                                            #
#######################################################################################################################

lock_instance_tunables(RemoveAssignedWorldImmediateSuperInteraction, interaction_type=InteractionType.COMMAND)
lock_instance_tunables(RemoveAssignedWorldPickerSuperInteration, interaction_type=InteractionType.PICKER)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('RemoveAssignedWorldImmediateSuperInteraction', 'RemoveAssignedWorldPickerSuperInteration', )

"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the main part of the script that injections the mod's own interactions and which creates the
dynamic console commands.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.resources import Types
from sims4.tuning.tunable import TunableMapping

# miscellaneous imports
from interactions.base.super_interaction import SuperInteraction

# local imports
from kuttoe_home_regions.settings import Settings
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.ui import NotificationType
from kuttoe_home_regions.utils import on_load_complete, InteractionTargetType


#######################################################################################################################
# Tunable Definitions                                                                                                 #
#######################################################################################################################

class TunableInteractionMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'affordance'
        kwargs['key_type'] = SuperInteraction.TunablePackSafeReference()
        kwargs['value_name'] = 'injection_target'
        kwargs['value_type'] = InteractionTargetType.to_enum_entry(default='SIM_OBJECT')

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Console Command Registration                                                                                        #
#######################################################################################################################

def _create_console_commands():
    for world in HomeWorldIds.available_worlds:
        Settings.create_world_console_commands(world)

    for notification_type in NotificationType.exported_values:
        Settings.create_settings_console_command(notification_type)


@on_load_complete(Types.TUNING, safe=False)
def _kuttoe_home_regions_main_injection_snippet(_manager):
    _create_console_commands()


#######################################################################################################################
# Affordance Injection                                                                                                #
#######################################################################################################################

class KuttoeHomeRegions:
    INTERACTIONS = TunableInteractionMapping()

    @staticmethod
    @on_load_complete(Types.TUNING)
    def _inject_affordances(_manager):
        InteractionTargetType.verify_all_values()

        for (affordance, target) in KuttoeHomeRegions.INTERACTIONS.items():
            target.update_affordance_list(affordance)

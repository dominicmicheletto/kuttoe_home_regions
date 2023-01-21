"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details utilities used for console commands.
"""

#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Optional
from collections import namedtuple

# misc imports
import enum
import services

# sims4 imports
from sims4.commands import CheatOutput as Output
from sims.sim_info_manager import SimInfoManager

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.ui import NotificationType
from kuttoe_home_regions.utils import enum_entry_factory


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


@enum_entry_factory(default='ALLOW_WORLD', invalid=())
class AlterType(enum.Int):
    ALLOW_WORLD = 0
    DISALLOW_WORLD = 1


#######################################################################################################################
#  Named Tuples                                                                                                       #
#######################################################################################################################


SimHouseholdData = namedtuple('SimHouseholdData', ['sim_info', 'sim_name', 'sim_id', 'household'])


#######################################################################################################################
#  Helper Functions                                                                                                   #
#######################################################################################################################


def kuttoe_set_world_id(home_world_id: HomeWorldIds, sim_info, _connection=None):
    name, value = home_world_id.desc, home_world_id.value
    output = Output(_connection)
    household_data = get_sim_household_data(sim_info, _connection)

    if not household_data:
        return False

    previous_world_id = household_data.household._home_world_id
    household_data.household._home_world_id = value
    home_world_id.apply_fixup_to_sim_info(sim_info, previous_world_id)
    output('Home world ID for {} ({}) is now {} ({})'.format(household_data.sim_name, household_data.sim_id, name, value))

    return True


def kuttoe_allow_sim_in_world(home_world_id: HomeWorldIds, sim_info, _connection=None):
    from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

    output = Output(_connection)
    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    stat = LivesInRegionWithExceptions.get_stat_from_sim_info(sim_info)
    stat.allow_region(home_world_id)
    output(f'Sim {household_data.sim_name} ({household_data.sim_id}) is now specially allowed in {home_world_id.desc}')
    return True


def kuttoe_disallow_sim_in_world(home_world_id: HomeWorldIds, sim_info, _connection=None):
    from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

    output = Output(_connection)
    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    stat = LivesInRegionWithExceptions.get_stat_from_sim_info(sim_info)
    stat.disallow_region(home_world_id)
    output(f'Sim {household_data.sim_name} ({household_data.sim_id}) '
           f'is no longer specially allowed in {home_world_id.desc}')
    return True


def kuttoe_allow_sim_in_all_worlds(sim_info, _connection=None):
    from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

    output = Output(_connection)
    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    stat = LivesInRegionWithExceptions.get_stat_from_sim_info(sim_info)
    stat.allow_all_regions()
    regions_list = ', '.join(region.desc for region in HomeWorldIds.available_worlds)
    output(f'Sim {household_data.sim_name} ({household_data.sim_id}) '
           f'is now exempt from all region filters and allowed in: {regions_list}')
    return True


def kuttoe_disallow_sim_in_all_worlds(sim_info, _connection=None):
    from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

    output = Output(_connection)
    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    stat = LivesInRegionWithExceptions.get_stat_from_sim_info(sim_info)
    stat.disallow_all_regions()
    output(f'Sim {household_data.sim_name} ({household_data.sim_id}) is no longer specially exempt from region filters')
    return True


def get_home_world_from_name(*home_world_name, _connection=None) -> Optional[HomeWorldIds]:
    output = Output(_connection)
    world_key = ' '.join(home_world_name).upper().replace(' ', '_')

    if len(home_world_name) == 0:
        output('Missing World name!')
        return None

    if world_key not in HomeWorldIds:
        world_list = HomeWorldIds.world_list
        output('Invalid World name: {}\n\nValid World names: {}'.format(world_key, world_list))

        return None

    return HomeWorldIds[world_key]


def get_sim_info_by_name(first_name: str, last_name: str = '', _connection=None):
    manager: SimInfoManager = services.sim_info_manager()
    sim_info = manager.get_sim_info_by_name(first_name, last_name)

    if not sim_info:
        full_name = ' '.join((first_name, last_name,))
        Output(_connection)('No Sim found with name {}'.format(full_name))
        return None

    return sim_info


def get_sim_household_data(sim_info, _connection=None):
    output = Output(_connection)

    if not sim_info:
        output('Sim could not be found')
        return False

    household = getattr(sim_info, 'household', None)
    sim_name = '{} {}'.format(sim_info.first_name, sim_info.last_name)
    if household is None:
        output(f'Sim {sim_name} has no household object')
        return False

    return SimHouseholdData(sim_info, sim_name, sim_info.id, household)


def get_notification_type_from_name(*notification_type_name, _connection=None) -> Optional[NotificationType]:
    output = Output(_connection)
    notif_key = ' '.join(notification_type_name).upper().replace(' ', '_')

    if len(notif_key) == 0:
        output('Missing notification name!')
        return None

    if notif_key not in NotificationType:
        output('Invalid notification setting name: {}'.format(notif_key))
        return None

    return NotificationType[notif_key]


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = (
    'get_home_world_from_name', 'get_sim_info_by_name', 'get_sim_household_data',
    'kuttoe_allow_sim_in_world', 'kuttoe_disallow_sim_in_world',
    'kuttoe_allow_sim_in_all_worlds', 'kuttoe_disallow_sim_in_all_worlds',
    'kuttoe_set_world_id',
    'get_notification_type_from_name',
    'SimHouseholdData',
    'AlterType',
)

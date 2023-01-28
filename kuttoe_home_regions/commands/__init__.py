"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details console commands and helpful utility functions used to run them.
"""

#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.commands import Command, CommandType, CheatOutput as Output

# misc imports
from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.commands.base_commands import *
from kuttoe_home_regions.commands.utils import *


#######################################################################################################################
# Set Assigned World                                                                                                  #
#######################################################################################################################


@Command('kuttoe.set_world_id', command_type=CommandType.Live)
def set_world_id(*home_world_name, opt_sim: OptionalSimInfoParam = None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)

    if home_world is None:
        return False
    return kuttoe_set_world_id(home_world, sim_info, _connection=_connection)


@Command('kuttoe.set_world_id_by_sim_name', command_type=CommandType.Live)
def set_world_id_by_sim_name(first_name: str, last_name: str = '', *home_world_name, _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return set_world_id(*home_world_name, opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.set_world_id_by_sim_id', command_type=CommandType.Live)
def set_world_id_by_sim_id(sim_id: str, *home_world_name, _connection=None):
    opt_sim = OptionalSimInfoParam(sim_id)

    return set_world_id(*home_world_name, opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.allow_in_region', command_type=CommandType.Live)
def allow_in_region(*home_world_name, opt_sim: OptionalSimInfoParam = None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)

    if home_world is None:
        return False
    return kuttoe_allow_sim_in_world(home_world, sim_info, _connection)


@Command('kuttoe.allow_in_region_by_sim_id', command_type=CommandType.Live)
def allow_in_region_by_sim_id(sim_id: str, *home_world_name, _connection=None):
    opt_sim = OptionalSimInfoParam(sim_id)

    return allow_in_region(*home_world_name, opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.allow_in_region_by_sim_name', command_type=CommandType.Live)
def allow_in_region_by_sim_name(first_name: str, last_name: str = '', *home_world_name, _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return allow_in_region(*home_world_name, opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.allow_household_in_region_by_sim_name', command_type=CommandType.Live)
def allow_household_in_region_by_sim_name(first_name: str, last_name: str = '', *home_world_name, _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)
    if home_world is None:
        return False

    for sim_info in household_data.household.get_humans_gen():
        if sim_info.is_baby:
            continue

        kuttoe_allow_sim_in_world(home_world, sim_info, _connection=_connection)

    return True


@Command('kuttoe.disallow_in_region', command_type=CommandType.Live)
def disallow_in_region(*home_world_name, opt_sim: OptionalSimInfoParam = None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)

    if home_world is None:
        return False
    return kuttoe_disallow_sim_in_world(home_world, sim_info, _connection)


@Command('kuttoe.disallow_in_region_by_sim_id', command_type=CommandType.Live)
def allow_in_region_by_sim_id(sim_id: str, *home_world_name, _connection=None):
    opt_sim = OptionalSimInfoParam(sim_id)

    return disallow_in_region(*home_world_name, opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.disallow_in_region_by_sim_name', command_type=CommandType.Live)
def disallow_in_region_by_sim_name(first_name: str, last_name: str = '', *home_world_name, _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return disallow_in_region(*home_world_name, opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.disallow_household_in_region_by_sim_name', command_type=CommandType.Live)
def disallow_household_in_region_by_sim_name(first_name: str, last_name: str = '', *home_world_name, _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)
    if home_world is None:
        return False

    for sim_info in household_data.household.get_humans_gen():
        if sim_info.is_baby:
            continue

        kuttoe_disallow_sim_in_world(home_world, sim_info, _connection=_connection)

    return True


@Command('kuttoe.allow_in_all_regions', command_type=CommandType.Live)
def allow_in_all_regions(opt_sim: OptionalSimInfoParam = None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False

    return kuttoe_allow_sim_in_all_worlds(sim_info, _connection)


@Command('kuttoe.allow_in_all_regions_by_sim_name', command_type=CommandType.Live)
def allow_in_all_regions_by_sim_name(first_name: str, last_name: str = '', _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return allow_in_all_regions(opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.disallow_in_all_regions', command_type=CommandType.Live)
def disallow_in_all_regions(opt_sim: OptionalSimInfoParam = None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False

    return kuttoe_disallow_sim_in_all_worlds(sim_info, _connection)


@Command('kuttoe.disallow_in_all_regions_by_sim_name', command_type=CommandType.Live)
def disallow_in_all_regions_by_sim_name(first_name: str, last_name: str = '', _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return disallow_in_all_regions(opt_sim=opt_sim, _connection=_connection)


#######################################################################################################################
# Remove Assigned World                                                                                               #
#######################################################################################################################


@Command('kuttoe.remove_assigned_world', command_type=CommandType.Live)
def kuttoe_make_homeless(opt_sim: OptionalSimInfoParam = None, force: bool = True, _connection=None):
    output = Output(_connection)
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    household_data = get_sim_household_data(sim_info, _connection)
    if not household_data:
        return False

    previous_home_world_id = household_data.household._home_world_id
    household_data.household._home_world_id = 0
    previous_world = HomeWorldIds.get_matching_home_world_from_value(previous_home_world_id)

    if previous_world:
        name, value = previous_world.desc, previous_world.value
        previous_world.default_local_fixup.clear_all_data(sim_info)
    else:
        name, value = None, previous_home_world_id

    sim_details = f'{household_data.sim_name} ({household_data.sim_id})'
    home_world_desc = f'{name} ({value})' if name else f'{previous_home_world_id}'
    output(f'{sim_details} has had their previously assigned Home World of {home_world_desc} removed')

    return True


@Command('kuttoe.remove_assigned_world_by_sim_name', command_type=CommandType.Live)
def kuttoe_make_homeless_by_sim_name(first_name: str, last_name: str = '', force: bool = True, _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return kuttoe_make_homeless(opt_sim=opt_sim, force=force, _connection=_connection)


#######################################################################################################################
#  Toggles                                                                                                            #
#######################################################################################################################

@Command('kuttoe.settings.toggle_soft', command_type=CommandType.Live)
def kuttoe_settings_toggle_soft(*home_world_name, new_value: bool = None, _connection=None):
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)

    if home_world is None:
        return False
    return kuttoe_settings_soft_setting_toggle(home_world, new_value=new_value, _connection=_connection)


@Command('kuttoe.toggle_notification', command_type=CommandType.Live)
def toggle_notification_setting(*setting_name, new_value: bool = None, _connection=None):
    setting_name = get_notification_type_from_name(*setting_name, _connection=_connection)

    if setting_name is None:
        return False
    return kuttoe_notifications_toggle(setting_name, new_value=new_value, _connection=_connection)


@Command('kuttoe.toggle_notification_internal', command_type=CommandType.Live)
def toggle_notification_setting_internal(setting_name: str, new_value: bool = None, _connection=None):
    return toggle_notification_setting(setting_name, new_value=new_value, _connection=_connection)


@Command('kuttoe.toggle_bidirectional', command_type=CommandType.Live)
def toggle_bidirectional(new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings

    response = 'on' if Settings.toggle_setting('bidirectional_toggle', new_value) else 'off'
    Output(_connection)('Bidirectional toggle for Allow and Disallow World pickers is now turned {}'.format(response))

    return True


@Command('kuttoe.toggle_high_school', command_type=CommandType.Live)
def kuttoe_toggle_high_school(new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings

    response = 'on' if Settings.toggle_setting('high_school_toggle', new_value) else 'off'
    Output(_connection)('Region filter for Active High School situations is now turned {}'.format(response))

    return True


#######################################################################################################################
# Miscellaneous                                                                                                       #
#######################################################################################################################

@Command('kuttoe.settings.reset', command_type=CommandType.Live)
def kuttoe_reset_settings(backup: bool = False, _connection=None):
    from kuttoe_home_regions.settings import Settings

    output = Output(_connection)
    file_path = Settings.reset(backup=backup)

    output(f'All settings have been reset to their defaults')
    if backup:
        if file_path is not None:
            output(f'Your previous settings have been backed up to the following file: {file_path}')
        else:
            output(f'An error occurred while attempting to backup your previous settings file.')

    return file_path

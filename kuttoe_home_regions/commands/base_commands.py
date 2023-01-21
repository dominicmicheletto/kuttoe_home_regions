"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details base command functions. These are not console commands in themselves, but they define the boilerplate
code used for them.
"""

#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import List

# sims4 imports
from sims4.commands import Output

# local imports
from kuttoe_home_regions.commands.utils import *
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.ui import NotificationType


#######################################################################################################################
#  Base Console Command                                                                                               #
#######################################################################################################################


def kuttoe_settings_soft_setting_toggle(home_world_id: HomeWorldIds, new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings
    WorldSettingNames = Settings.WorldSettingNames

    new_value = new_value if new_value is not None else not Settings.get_world_settings(home_world_id)['Soft']
    Settings.update_setting('{}_{}'.format(home_world_id.settings_name_base, WorldSettingNames.SOFT), new_value)
    Output(_connection)('Soft filter setting for World {} set to {}'.format(home_world_id.desc, new_value))

    return True


def kuttoe_settings_tourists_toggle(home_world_id: HomeWorldIds, new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings
    name = Settings.WorldSettingNames.TOURISTS

    output = Output(_connection)
    if not home_world_id.has_tourists:
        output('{} does not support tourists'.format(home_world_id.desc))
        return False

    new_value = new_value if new_value is not None else not Settings.get_world_settings(home_world_id)[name]
    Settings.update_setting('{}_{}'.format(home_world_id.settings_name_base, name), new_value)
    Output(_connection)('Tourists filter setting for World {} set to {}'.format(home_world_id.desc, new_value))

    return True


def kuttoe_notifications_toggle(notification_type: NotificationType, new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings

    new_value = new_value if new_value is not None else not Settings.get_notification_setting(notification_type)
    Settings.update_setting(notification_type.setting_name, new_value)
    Output(_connection)('Notification settings for {} set to {}'.format(notification_type.name, new_value))

    return True


def _alter_worlds_list_helper(
        source_world: HomeWorldIds,
        target_world: HomeWorldIds,
        alter_type: AlterType,
        _connection=None):
    from kuttoe_home_regions.settings import Settings
    WorldSettingNames = Settings.WorldSettingNames

    output = Output(_connection)
    if target_world == source_world:
        words = {alter_type.ALLOW_WORLD: ('add', 'to'), alter_type.DISALLOW_WORLD: ('remove', 'from')}
        output('Cannot {} a World {} its own list'.format(*words[alter_type]))

        return False

    world_list: List[str] = Settings.get_world_settings(source_world)[WorldSettingNames.WORLDS]
    if alter_type == AlterType.ALLOW_WORLD:
        if target_world.name in world_list:
            output('{} is already in {}\'s allowed Worlds list!'.format(target_world.desc, source_world.desc))
            return False

        world_list.append(target_world.name)
        msg = 'added to'
    elif alter_type == AlterType.DISALLOW_WORLD:
        if target_world.name not in world_list:
            output('{} cannot be removed from {}\'s allowed Worlds list as it\'s not currently in it!'.format(
                target_world.desc, source_world.desc))
            return False

        world_list.remove(target_world.name)
        msg = 'removed from'
    else:
        msg = '[[Invalid Alter Type]]'

    Settings.update_setting('{}_Worlds'.format(source_world.settings_name_base), world_list)
    output('World {} {} {}\'s list of Worlds Townies are allowed to come from'.format(
        target_world.desc, msg, source_world.desc
    ))

    return True


def kuttoe_settings_alter_worlds_list(source_world: HomeWorldIds,
                                      *home_world_name,
                                      alter_type: AlterType,
                                      _connection=None):
    from kuttoe_home_regions.settings import Settings

    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)
    if home_world is None:
        return False

    _alter_worlds_list_helper(source_world, home_world, alter_type, _connection)
    if Settings.bidirectional_toggle:
        _alter_worlds_list_helper(home_world, source_world, alter_type, _connection)

    return True


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = (
    'kuttoe_settings_soft_setting_toggle',
    'kuttoe_settings_tourists_toggle',
    'kuttoe_settings_alter_worlds_list',
    'kuttoe_notifications_toggle',
    '_alter_worlds_list_helper',
)
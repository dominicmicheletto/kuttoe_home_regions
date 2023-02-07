"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details base command functions. These are not console commands in themselves, but they define the boilerplate
code used for them.
"""

#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from typing import List, Dict

# sims4 imports
from sims4.commands import Output
from sims4.math import almost_equal
from sims4.utils import Result

# miscellaneous imports
from enum import Int

# local imports
from kuttoe_home_regions.commands.utils import *
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.enum.neighbourhood_streets import NeighbourhoodStreets
from kuttoe_home_regions.ui import NotificationType
from kuttoe_home_regions.utils import matches_bounds, BoundTypes, enum_entry_factory


#######################################################################################################################
# Base Console Command                                                                                                #
#######################################################################################################################

def kuttoe_settings_soft_setting_toggle(home_world_id: HomeWorldIds, new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings
    soft = Settings.WorldSettingNames.SOFT

    new_value = new_value if new_value is not None else not Settings.get_world_settings(home_world_id)[soft]
    Settings.update_setting('{}_{}'.format(home_world_id.settings_name_base, soft), new_value)
    Output(_connection)('Soft filter setting for World {} set to {}'.format(home_world_id.desc, new_value))

    return True


def kuttoe_set_region_soft_filter_value(home_world_id: HomeWorldIds, new_value: float, _connection=None):
    from kuttoe_home_regions.settings import Settings
    output = Output(_connection)

    min_value, max_value = 0.0, 1.0
    valid = matches_bounds(new_value, BoundTypes.NONE, (min_value, max_value))

    if not valid:
        output(f'Soft filter for {home_world_id.desc} value must be between '
               f'{min_value} and {max_value} (exclusive), not: {new_value}')
    else:
        output(f'Soft filter value for {home_world_id.desc} updated to {new_value}')
        Settings.update_world_setting(home_world_id, Settings.WorldSettingNames.SOFT_FILTER_VALUE, new_value)

    return valid


def kuttoe_settings_tourists_toggle(home_world_id: HomeWorldIds, new_value: bool = None, _connection=None):
    from kuttoe_home_regions.settings import Settings
    name = Settings.WorldSettingNames.TOURISTS

    output = Output(_connection)
    if not home_world_id.has_tourists:
        output('{} does not support tourists'.format(home_world_id.desc))
        return False

    new_value = new_value if new_value is not None else not Settings.get_world_settings(home_world_id)[name]
    Settings.update_world_setting(home_world_id, name, new_value)
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
    from kuttoe_home_regions.settings import Settings, WorldSettingNames
    output = Output(_connection)

    if target_world == source_world:
        words = {alter_type.ALLOW_VALUE: ('add', 'to'), alter_type.DISALLOW_VALUE: ('remove', 'from')}
        output('Cannot {} a World {} its own list'.format(*words[alter_type]))

        return False

    world_list: List[str] = Settings.get_world_settings(source_world)[WorldSettingNames.WORLDS]
    if alter_type is AlterType.ALLOW_VALUE:
        if target_world.name in world_list:
            output('{} is already in {}\'s allowed Worlds list!'.format(target_world.desc, source_world.desc))
            return False

        world_list.append(target_world.name)
        msg = 'added to'
    elif alter_type is AlterType.DISALLOW_VALUE:
        if target_world.name not in world_list:
            output('{} cannot be removed from {}\'s allowed Worlds list as it\'s not currently in it!'.format(
                target_world.desc, source_world.desc))
            return False

        world_list.remove(target_world.name)
        msg = 'removed from'
    else:
        msg = '[[Invalid Alter Type]]'

    Settings.update_world_setting(source_world, Settings.WorldSettingNames.WORLDS, world_list)
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


@enum_entry_factory(default='INVALID_VALUE', invalid=())
class AlterStreetWeightReasons(Int):
    INVALID_VALUE = 0
    NEED_NON_ZERO_VALUE = 1


def kuttoe_alter_street_weights(
        street: NeighbourhoodStreets,
        world: HomeWorldIds,
        weight: float,
        _connection=None):
    from kuttoe_home_regions.settings import Settings, WorldSettingNames
    output = Output(_connection)

    if not world.supports_multiple_creation_streets:
        output(f'World {world.desc} only has one street a Sim can be assigned to')
        return Result(False, reason=AlterStreetWeightReasons.INVALID_VALUE)

    if not world.has_street(street.value):
        output(f'World {world.desc} does not have street {street.desc}!')
        return Result(False, reason=AlterStreetWeightReasons.INVALID_VALUE)

    if 0 > weight:
        output(f'Street weights must be a positive value.')
        return Result(False, reason=AlterStreetWeightReasons.INVALID_VALUE)

    default_weight = world.street_for_creation.get_default_weight(street)
    weights: Dict[str, float] = Settings.get_world_settings(world)[WorldSettingNames.STREET_WEIGHTS]

    if almost_equal(default_weight, weight):
        weights.pop(street.dict_key)
    else:
        weights[street.dict_key] = weight

    if all(almost_equal(weight, 0) for weight in weights.values()):
        output(f'There must be one street with a non-zero weight!')
        return Result(False, reason=AlterStreetWeightReasons.NEED_NON_ZERO_VALUE)

    Settings.update_world_setting(world, WorldSettingNames.STREET_WEIGHTS, weights)
    output(f'Street {street.desc} in World {world.desc} has had its weight updated to {weight}')

    return Result.TRUE


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = (
    'kuttoe_settings_soft_setting_toggle',
    'kuttoe_settings_tourists_toggle',
    'kuttoe_settings_alter_worlds_list',
    'kuttoe_notifications_toggle',
    'kuttoe_set_region_soft_filter_value',
    'kuttoe_alter_street_weights',
    '_alter_worlds_list_helper',
    'AlterStreetWeightReasons',
)

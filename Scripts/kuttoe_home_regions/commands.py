#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

from typing import List, Optional
import enum
import services
from sims4.commands import Command, CommandType, Output
from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target
from sims.sim_info_manager import SimInfoManager
from kuttoe_home_regions.home_worlds import HomeWorldIds


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################

class AlterType(enum.Int):
    ALLOW_WORLD = 0
    DISALLOW_WORLD = 1


#######################################################################################################################
#  Helper Functions                                                                                                   #
#######################################################################################################################


def kuttoe_set_world_id(home_world_id: HomeWorldIds, sim_info, _connection=None):
    name, value = home_world_id.desc, home_world_id.value
    output = Output(_connection)

    if sim_info is None:
        return False

    household = getattr(sim_info, 'household', None)
    sim_name = '{} {}'.format(sim_info.first_name, sim_info.last_name)
    if household is None:
        output('Sim {} has no household object'.format(sim_name))
        return False

    household._home_world_id = value
    output('Home world ID for {} ({}) is now {} ({})'.format(sim_name, sim_info.id, name, value))
    return True


def get_home_world_from_name(*home_world_name, _connection=None) -> Optional[HomeWorldIds]:
    world_key = ' '.join(home_world_name).upper().replace(' ', '_')

    if world_key not in HomeWorldIds:
        Output(_connection)('Invalid world name: {}'.format(world_key))
        return None

    return HomeWorldIds[world_key]


#######################################################################################################################
#  Base Console Command                                                                                               #
#######################################################################################################################


def kuttoe_settings_soft_setting_toggle(home_world_id: HomeWorldIds, _connection=None):
    from kuttoe_home_regions.settings import Settings

    new_value = not Settings.get_world_settings(home_world_id)['Soft']
    Settings.update_setting('{}_Soft'.format(home_world_id.settings_name_base), new_value)
    Output(_connection)('Soft filter setting for world {} set to {}'.format(home_world_id.desc, new_value))

    return True


def kuttoe_settings_alter_worlds_list(source_world: HomeWorldIds,
                                      *home_world_name,
                                      alter_type: AlterType,
                                      _connection=None):
    from kuttoe_home_regions.settings import Settings

    output = Output(_connection)
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)
    if home_world is None:
        return False

    if home_world == source_world:
        output('Cannot {} a world from its own list'.format('add' if alter_type == AlterType.ALLOW_WORLD else 'remove'))
        return False

    world_list: List[str] = Settings.get_world_settings(source_world)['Worlds']
    if alter_type == AlterType.ALLOW_WORLD:
        if home_world.name in world_list:
            output('{} is already in {}\'s allowed Worlds list!'.format(home_world.desc, source_world.desc))
            return False

        world_list.append(home_world.name)
        msg = 'added to'
    elif alter_type == AlterType.DISALLOW_WORLD:
        if home_world.name not in world_list:
            output('{} cannot be removed from {}\'s allowed Worlds list as it\'s not currently in it!'.format(
                home_world.desc, source_world.desc))
            return False

        world_list.remove(home_world.name)
        msg = 'removed from'

    Settings.update_setting('{}_Worlds'.format(source_world.settings_name_base), world_list)
    output('World {} {} {}\'s list of Worlds Townies are allowed to come from'.format(
        home_world.desc, msg, source_world.desc
    ))
    return True


@Command('kuttoe.settings.toggle_soft', command_type=CommandType.Live)
def kuttoe_settings_toggle_soft(*home_world_name, _connection=None):
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)

    if home_world is None:
        return False
    return kuttoe_settings_soft_setting_toggle(home_world, _connection=_connection)


@Command('kuttoe.set_world_id', command_type=CommandType.Live)
def set_world_id(*home_world_name, opt_sim: OptionalSimInfoParam = None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    home_world = get_home_world_from_name(*home_world_name, _connection=_connection)

    if home_world is None:
        return False
    return kuttoe_set_world_id(home_world, sim_info, _connection=_connection)


@Command('kuttoe.set_world_id_by_sim_name', command_type=CommandType.Live)
def set_world_id_by_sim_name(first_name: str, last_name: str = '', *home_world_name, _connection=None):
    manager: SimInfoManager = services.sim_info_manager()
    sim_info = manager.get_sim_info_by_name(first_name, last_name)

    if not sim_info:
        full_name = ' '.join(*(first_name, last_name, ))
        Output(_connection)('No Sim found with name {}'.format(full_name))
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return set_world_id(*home_world_name, opt_sim=opt_sim, _connection=_connection)


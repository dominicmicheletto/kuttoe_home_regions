"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details debug console commands. These are for dev-use only and are locked behind AllCheats.
"""

#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from typing import Callable, Any, Union

# sims4 imports
from sims4.commands import Command, CommandType, CheatOutput as Output

# misc imports
from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target

# local imports
from kuttoe_home_regions.commands.utils import get_sim_household_data, get_sim_info_by_name


#######################################################################################################################
# Helper Functions                                                                                                    #
#######################################################################################################################

def dump_data_to_file(
        file_name: str, data: dict, file_path: str = None, _connection=None,
        file_writer: Callable[[Union[str, int], Any], str] = None
):
    from kuttoe_home_regions.settings import Settings
    from os import path
    from subprocess import Popen

    output = Output(_connection)
    gv_data = Settings.gv_directory
    file_path = path.join(file_path or gv_data.directory_path, file_name)

    def _default_file_writer(item_key, item_value):
        return f'{item_key}: {item_value}\n\n'

    with open(file_path, 'w+') as file:
        for (key, value) in data.items():
            file.write((file_writer or _default_file_writer)(key, value))

    output(f'Successfully wrote data to file: {file_path}')
    Popen(['notepad', file_path])
    return True


class DebugDumpCommand:
    class _Command:
        def __init__(self, func, base):
            self._func = func
            self._base: DebugDumpCommand = base

        def file_writer(self, func):
            self._base._file_writer = func
            return self

        def invoke(self, _connection=None):
            return self._func(_connection)

        @property
        def _file_name(self): return self._base._file_name

        @property
        def _command_names(self): return self._base._command_names

        @property
        def _command_type(self): return self._base._command_type

        @property
        def _file_writer(self): return self._base._file_writer

        def __call__(self, file_path: str = None, _connection=None):
            value = self.invoke(_connection)

            return dump_data_to_file(self._file_name, value, file_path, _connection, file_writer=self._file_writer)

    __slots__ = ('_file_name', '_command_names', '_file_writer', '_command_type',)
    FILE_NAME_FORMAT = '{}.txt'
    COMMAND_NAME_FORMAT = 'kuttoe.{}'

    @classmethod
    def _format_command_names(cls, *command_names, should_format: bool = True):
        formatter = lambda name: (cls.COMMAND_NAME_FORMAT if should_format else '{}').format(name)

        return tuple(map(formatter, command_names))

    @classmethod
    def _format_file_name(cls, file_name, should_format: bool = True):
        return (cls.FILE_NAME_FORMAT if should_format else '{}').format(file_name)

    def __init__(self, file_name: str, *command_names: str, file_writer=None,
                 infer_file_type: bool = True, infer_command_names: bool = True,
                 command_type: CommandType = CommandType.Cheat):
        self._file_name = self._format_file_name(file_name, infer_file_type)
        self._command_names = self._format_command_names(*command_names, should_format=infer_command_names)
        self._file_writer = file_writer
        self._command_type = command_type

    def __call__(self, func):
        return Command(*self._command_names, command_type=self._command_type)(self._Command(func, self))


#######################################################################################################################
# World Getter Commands                                                                                               #
#######################################################################################################################

@Command('kuttoe.get_world_id', command_type=CommandType.Cheat)
def get_world_id(opt_sim: OptionalSimInfoParam = None, _connection=None):
    output = Output(_connection)
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)

    household_data = get_sim_household_data(sim_info, _connection=_connection)
    if not household_data:
        return False

    sim_name, household = household_data.sim_name, household_data.household
    output('Home world ID for {} ({}) is {}'.format(sim_name, sim_info.id, household._home_world_id))
    return True


@Command('kuttoe.get_world_id_by_sim_name', command_type=CommandType.Cheat)
def get_world_id_by_sim_name(first_name: str, last_name: str = '', _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return get_world_id(opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.get_allowed_regions', command_type=CommandType.Cheat)
def get_allowed_regions(opt_sim: OptionalSimInfoParam = None, _connection=None):
    from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

    output = Output(_connection)
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)

    household_data = get_sim_household_data(sim_info, _connection=_connection)
    if not household_data:
        return False

    stat = LivesInRegionWithExceptions.get_stat_from_sim_info(sim_info)
    regions = stat.get_allowed_regions()
    regions_list = 'None' if not regions else ', '.join(region.desc for region in regions)
    sim_name, sim_id = household_data.sim_name, household_data.sim_id
    output(f'Sim {sim_name} ({sim_id}) is exempt from region filtering in the following worlds: {regions_list}')
    return True


@Command('kuttoe.get_allowed_regions_by_sim_name', command_type=CommandType.Cheat)
def get_allowed_regions_by_sim_name(first_name: str, last_name: str = '', _connection=None):
    sim_info = get_sim_info_by_name(first_name, last_name, _connection)
    if sim_info is None:
        return False

    opt_sim = OptionalSimInfoParam(str(sim_info.id))
    return get_allowed_regions(opt_sim=opt_sim, _connection=_connection)


@Command('kuttoe.get_soft_filter_value', command_type=CommandType.Cheat)
def get_soft_filter_value(_connection=None):
    from kuttoe_home_regions.settings import Settings

    Output(_connection)(f'Soft filter value is currently: {Settings.soft_filter_value}')
    return True


@Command('kuttoe.get_gallery_behaviour', command_type=CommandType.Cheat)
def get_gallery_behaviour(_connection=None):
    from kuttoe_home_regions.settings import Settings

    value = Settings.save_across_gallery_toggle
    Output(_connection)(f'World Exemption settings do {"" if value else "not "}save from the gallery')

    return True


#######################################################################################################################
#  Dump Commands                                                                                                      #
#######################################################################################################################

@DebugDumpCommand('Kuttoe_Filter_Dump', 'dump_filters', 'df')
def dump_filters(_connection=None):
    from kuttoe_home_regions.injections import SituationJobModifications

    return dict(soft=SituationJobModifications.SOFT_FILTER, main=SituationJobModifications.MAIN_FILTER)


@dump_filters.file_writer
def dump_filters_file_writer(key, value):
    return f'{key} ({value}):\n{getattr(value, "value")}\n\n'


@DebugDumpCommand('Kuttoe_Situation_Jobs_Dump', 'dump_bypassed_sjs', 'dbsj')
def dump_bypassed_situation_jobs(_connection=None):
    from kuttoe_home_regions.injections import SituationJobModifications
    from kuttoe_home_regions.settings import Settings

    situation_jobs_info = {
        "high_school_filter": Settings.high_school_toggle,
        "soft_filter": SituationJobModifications.soft_list,
        "soft_filter_value": Settings.soft_filter_value,
        "bypassed_jobs": SituationJobModifications._BYPASSED_JOBS,
        "high_school_situations": SituationJobModifications.high_school_situations,
        "tourists_situations": SituationJobModifications.tourists_situations,
    }

    return situation_jobs_info


@DebugDumpCommand('Kuttoe_Registered_Injection_Hooks', 'registered_injection_hooks', 'rih')
def dump_registered_injection_hooks(_connection=None):
    from kuttoe_home_regions.injections import SituationJobModifications

    hooks = SituationJobModifications._HOOKS
    return {hook: getattr(hook, 'value', None) for hook in hooks}


@DebugDumpCommand('Kuttoe_RegionsBitSet', 'regions_bit_set_values', 'rbsv')
def dump_registered_injection_hooks(_connection=None):
    from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
    from collections import OrderedDict

    values = OrderedDict()
    keys = sorted(region.raw_bit_value for region in HomeWorldIds)
    regions = {region.raw_bit_value: region for region in HomeWorldIds}
    for key in keys:
        values[key] = regions[key]

    values[-1] = set(HomeWorldIds) - set(values.values())

    return values


@DebugDumpCommand('Kuttoe_FilterExemptionsTracking', 'filters.dump_progress')
def dump_filter_progress(_connection=None):
    from kuttoe_home_regions.filters.custom_filters import LivesInRegionWithExceptions

    return dict(progress=LivesInRegionWithExceptions._FILTER_PROGRESS)


@dump_filter_progress.file_writer
def dump_filter_progress_file_writer(_, value):
    return '\n'.join(str(row) for row in value)


@Command('kuttoe.filters.toggle_tracking', command_type=CommandType.Cheat)
def toggle_filter_tracking(should_track: bool = None, _connection=None):
    import kuttoe_home_regions.filters.custom_filters as custom_filters

    is_tracking = not custom_filters._TRACK_FILTER_PROGRESS if should_track is None else should_track
    custom_filters._TRACK_FILTER_PROGRESS = is_tracking
    if not is_tracking:
        custom_filters.LivesInRegionWithExceptions._FILTER_PROGRESS.clear()

    output = Output(_connection)
    output(f'Tracking of filter exemptions has been {"enabled" if is_tracking else "disabled"}')


#######################################################################################################################
# Miscellaneous Commands                                                                                              #
#######################################################################################################################

@Command('kuttoe.show_settings', command_type=CommandType.Cheat)
def show_settings(_connection=None):
    from kuttoe_home_regions.settings import Settings
    from subprocess import Popen

    try:
        Popen(['notepad', Settings.settings_directory])
    except BaseException as ex:
        raise ex
    else:
        Output(_connection)('Successfully opened settings file for Home Regions')
    return True

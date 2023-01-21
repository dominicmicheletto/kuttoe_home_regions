"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details settings. These settings have defaults defined in tunable but get stored as a dictionary that
can be accessed after tunable is loaded.
"""

#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Dict, Any, Iterable
from os import path, pardir, listdir, mkdir
from json import load, dump, JSONDecodeError
from datetime import datetime
from collections import namedtuple

# game imports
from sims4.utils import classproperty, exception_protected
from sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableMapping, TunableRange, Tunable
from sims4.tuning.tunable import TunableEnumSet, TunableTuple, OptionalTunable
from sims4.commands import Command, CommandType
from sims4.math import MAX_FLOAT

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.tunable import TunableInteractionName
from kuttoe_home_regions.ui import NotificationType
from kuttoe_home_regions.utils import matches_bounds, BoundTypes


#######################################################################################################################
#  Settings Tuning                                                                                                    #
#######################################################################################################################

class TunableWorldSettings(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'soft': Tunable(tunable_type=bool, default=False, allow_empty=False),
        'world_list': TunableEnumSet(enum_type=HomeWorldIds, enum_default=HomeWorldIds.DEFAULT, allow_empty_set=True),
        'tourist_toggle': OptionalTunable(Tunable(tunable_type=bool, default=True, allow_empty=False)),
    }

    @classmethod
    def get_dict_values(cls, home_world: HomeWorldIds, **values) -> Dict[str, Any]:
        dict_values = dict()
        base_name = home_world.settings_name_base
        WorldSettingNames = Settings.WorldSettingNames

        dict_values['{}_{}'.format(base_name, WorldSettingNames.SOFT)] = values.get('soft', False)
        if home_world.has_tourists:
            dict_values['{}_{}'.format(base_name, WorldSettingNames.TOURISTS)] = values.get('tourist_toggle', True)
        dict_values['{}_{}'.format(base_name, WorldSettingNames.WORLDS)] = list(
            world.name for world in values.get('world_list', list())
        )

        return dict_values

    def __init__(self, home_world: HomeWorldIds, *args, **kwargs):
        self._home_world = home_world
        super().__init__(*args, **kwargs)

    @property
    def home_world(self):
        return self._home_world

    @property
    def as_dict(self):
        return {key: getattr(self, key) for key in self.FACTORY_TUNABLES.keys()}

    @property
    def dict_values(self):
        return self.get_dict_values(self.home_world, **self.as_dict)


class TunableDefaultWorldSettingsMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'home_world'
        kwargs['key_type'] = HomeWorldIds.create_enum_entry()
        kwargs['value_name'] = 'setting_values'
        kwargs['value_type'] = TunableWorldSettings.TunableFactory()

        super().__init__(*args, **kwargs)


class TunableNotificationSettingsMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'notification_type'
        kwargs['key_type'] = NotificationType.exported_values_enum
        kwargs['value_name'] = 'default_value'
        kwargs['value_type'] = Tunable(tunable_type=bool, default=False, allow_empty=False)

        super().__init__(*args, **kwargs)


class Settings:
    DEFAULT_WORLD_SETTINGS = TunableDefaultWorldSettingsMapping()
    COMMAND_NAME_BASES = TunableTuple(
        soft=TunableInteractionName(),
        tourists=TunableInteractionName(),
        allow_world=TunableInteractionName(),
        disallow_world=TunableInteractionName(),
        notification=TunableInteractionName(),
    )
    NOTIFICATION_SETTINGS = TunableNotificationSettingsMapping()
    BIDIRECTIONAL_TOGGLE = Tunable(tunable_type=bool, default=False, allow_empty=False, needs_tuning=True)
    HIGH_SCHOOL_TOGGLE = Tunable(tunable_type=bool, default=True, allow_empty=False, needs_tuning=True)
    SOFT_FILTER_VALUE = TunableRange(tunable_type=float, default=0.1, minimum=0.0, maximum=1.0)
    _SETTINGS = None

    class WorldSettingNames:
        SOFT = 'Soft'
        WORLDS = 'Worlds'
        TOURISTS = 'TouristsToggle'

        @classmethod
        def _names(cls, world: HomeWorldIds):
            names = (cls.SOFT, cls.WORLDS)

            if world.has_tourists:
                names += (cls.TOURISTS, )

            return names

    class SettingNames:
        BIDIRECTIONAL_TOGGLE = 'bidirectional_toggle'
        HIGH_SCHOOL_TOGGLE = 'high_school_toggle'
        SOFT_FILTER_VALUE = 'soft_filter_value'

        @staticmethod
        def _filter(item):
            key, value = item

            return not key.startswith('_') and not isinstance(value, classmethod)

        @classmethod
        def values(cls) -> Dict[str, str]:
            return dict(filter(cls._filter, vars(cls).items()))

        @classmethod
        def names(cls) -> Iterable[str]:
            return cls.values().keys()

        @classmethod
        def items(cls):
            return cls.values().items()

    @classmethod
    def create_settings_console_command(cls, notification_type: NotificationType):
        notif_name_builder = cls.COMMAND_NAME_BASES.notification
        command_name = notif_name_builder._get_hash_for_suffix(notification_type.pretty_name)[0]

        @Command(command_name, command_type=CommandType.Live)
        def _kuttoe_notification_toggle(new_value: bool = None, _connection=None):
            from kuttoe_home_regions.commands import kuttoe_notifications_toggle

            return kuttoe_notifications_toggle(notification_type, new_value=new_value, _connection=_connection)

        return _kuttoe_notification_toggle

    @classmethod
    def create_world_console_commands(cls, home_world: HomeWorldIds):
        command_name = {key: value(home_world)[0] for (key, value) in cls.COMMAND_NAME_BASES}

        @Command(command_name['soft'], command_type=CommandType.Live)
        def _kuttoe_soft_toggle(new_value: bool = None, _connection=None):
            from kuttoe_home_regions.commands import kuttoe_settings_soft_setting_toggle

            return kuttoe_settings_soft_setting_toggle(home_world, new_value=new_value, _connection=_connection)

        @Command(command_name['tourists'], command_type=CommandType.Live)
        def _kuttoe_soft_toggle(new_value: bool = None, _connection=None):
            from kuttoe_home_regions.commands import kuttoe_settings_tourists_toggle

            return kuttoe_settings_tourists_toggle(home_world, new_value=new_value, _connection=_connection)

        @Command(command_name['allow_world'], command_type=CommandType.Live)
        def _kuttoe_allow_world(*home_world_name, _connection=None):
            from kuttoe_home_regions.commands import kuttoe_settings_alter_worlds_list, AlterType

            return kuttoe_settings_alter_worlds_list(home_world, *home_world_name, alter_type=AlterType.ALLOW_WORLD,
                                                     _connection=_connection)

        @Command(command_name['disallow_world'], command_type=CommandType.Live)
        def _kuttoe_disallow_world(*home_world_name, _connection=None):
            from kuttoe_home_regions.commands import kuttoe_settings_alter_worlds_list, AlterType

            return kuttoe_settings_alter_worlds_list(home_world, *home_world_name, alter_type=AlterType.DISALLOW_WORLD,
                                                     _connection=_connection)

        return _kuttoe_soft_toggle, _kuttoe_allow_world, _kuttoe_disallow_world

    @classmethod
    @exception_protected
    def report_error(cls, error_message: BaseException, timestamp: datetime, file_name: str):
        gv_data = cls.gv_directory
        file_path = path.join(gv_data.directory_path, file_name)

        with open(file_path, 'w+') as log:
            log.write('Keep Sims in Home Region Error Log\n\n')
            log.write(f'Game version {gv_data.game_version}\n{timestamp.strftime("%m/%d/%Y %H:%M:%S")}\n\n')
            log.write(f'Received error: {error_message}\n\n')
            log.write('Please join our Discord server and upload this file in a support channel.\n'
                      'https://discord.gg/RqPqCdBsdF')

        raise error_message

    @classmethod
    def dump_settings(cls, settings_directory, settings: Dict[str, any]):
        try:
            with open(settings_directory, "w+") as settings_file:
                dump(settings, settings_file, indent=4)
        except BaseException as ex:
            timestamp = datetime.now()
            cls.report_error(ex, timestamp, '[Kuttoe] HomeRegions_Exception.log')

    @classmethod
    def validate_bool(cls, key: str, settings: Dict[str, Any], default: Dict[str, Any], settings_directory):
        if not isinstance(settings[key], bool):
            settings[key] = default[key]
            cls.dump_settings(settings_directory, settings)

    @classmethod
    def validate_number(cls,
                        key: str,
                        settings: Dict[str, Any],
                        default: Dict[str, Any],
                        settings_directory,
                        **constraints):
        value = settings[key]
        min_value = constraints.setdefault('min_value', 0.0)
        max_value = constraints.setdefault('max_value', MAX_FLOAT)
        include_bounds = constraints.setdefault('include_bounds', BoundTypes.BOTH)

        value_type = constraints.setdefault('value_type', float)
        value_type = float if not isinstance(value_type, (int, float, )) else value_type

        if not isinstance(value, value_type) or not matches_bounds(value, include_bounds, (min_value, max_value)):
            settings[key] = default[key]
            cls.dump_settings(settings_directory, settings)

    @classmethod
    def validate_list(cls,
                      key: str,
                      settings: Dict[str, Any],
                      default: Dict[str, Any],
                      settings_directory,
                      value_constraints=None):
        try:
            iter(settings[key])
        except ValueError:
            settings[key] = [settings[key], ]
            cls.dump_settings(settings_directory, settings)

        if value_constraints:
            if not all(value_constraints(value) for value in settings[key]):
                settings[key] = default[key]
                cls.dump_settings(settings_directory, settings)

    @classproperty
    def base_directory(cls):
        return path.abspath(path.join(path.dirname(path.realpath(__file__)), path.pardir))

    @classproperty
    def gv_directory(cls):
        gv_directory = cls.base_directory
        for i in range(10):
            gv_directory = path.abspath(path.join(gv_directory, pardir))

            if ('mods' and 'saves') in map(lambda x: x.lower(), listdir(gv_directory)):
                break
            if i == 10:
                break
        try:
            with open(path.join(gv_directory, 'GameVersion.txt'), 'r') as gv_file:
                gv_content = gv_file.read()
                game_version = gv_content[gv_content.index('1.'):]
        except BaseException:
            game_version = 'Unknown'

        return namedtuple('GameVersionInfo', ['game_version', 'directory_path'])(game_version, gv_directory)

    @classproperty
    def settings_directory(cls):
        gv_directory = cls.gv_directory.directory_path
        base_path = path.abspath(path.join(gv_directory, 'saves', 'Kuttoe', '[Kuttoe] HomeRegions_Settings.cfg'))

        try:
            mkdir(path.abspath(path.join(gv_directory, 'saves', 'Kuttoe')))
        except FileExistsError:
            pass

        return base_path

    @classmethod
    def make_default_setting(cls, home_world: HomeWorldIds, **values):
        values.setdefault('soft', False)
        values.setdefault('tourist_toggle', True if home_world.has_tourists else None)
        values.setdefault('worlds_list', tuple())

        return TunableWorldSettings.get_dict_values(home_world, **values)

    @classproperty
    def notification_settings(cls):
        items = dict(cls.NOTIFICATION_SETTINGS.items())
        for item in NotificationType.exported_values:
            items.setdefault(item, True)

        return {notif_type.setting_name: value for (notif_type, value) in items.items()}

    @classproperty
    def additional_settings(cls):
        return {value: getattr(cls, key) for (key, value) in cls.SettingNames.items()}

    @classproperty
    def default_settings(cls):
        dict_values = dict()

        dict_values.update(cls.notification_settings)
        dict_values.update(cls.additional_settings)
        for home_world in HomeWorldIds:
            if home_world is HomeWorldIds.DEFAULT:
                continue

            dict_values.update(cls.make_default_setting(home_world))

        for (home_world, defaults) in cls.DEFAULT_WORLD_SETTINGS.items():
            dict_values.update(defaults(home_world).dict_values)

        return dict_values

    @classmethod
    def _validate_settings(cls,
                           settings_dict: Dict[str, Any],
                           default_settings: Dict[str, Any],
                           settings_directory: str):
        validate_args = dict(settings=settings_dict, default=default_settings, settings_directory=settings_directory)

        cls.validate_number(cls.SettingNames.SOFT_FILTER_VALUE, **validate_args, max_value=1.0, include_bounds=BoundTypes.NONE)
        cls.validate_bool(cls.SettingNames.HIGH_SCHOOL_TOGGLE, **validate_args)
        cls.validate_bool(cls.SettingNames.BIDIRECTIONAL_TOGGLE, **validate_args)

        for notification_type in NotificationType.exported_values:
            cls.validate_bool(notification_type.setting_name, **validate_args)

        for home_world in HomeWorldIds:
            if home_world == HomeWorldIds.DEFAULT:
                continue

            base_name = home_world.settings_name_base
            cls.validate_bool('{}_{}'.format(base_name, cls.WorldSettingNames.SOFT), **validate_args)
            cls.validate_list('{}_{}'.format(base_name, cls.WorldSettingNames.WORLDS), **validate_args,
                              value_constraints=lambda value: value in HomeWorldIds)
            if home_world.has_tourists:
                cls.validate_bool('{}_{}'.format(base_name, cls.WorldSettingNames.TOURISTS), **validate_args)

    @classmethod
    def _load_settings(cls):
        settings_directory = cls.settings_directory
        default_settings = cls.default_settings

        cls._SETTINGS = dict(**default_settings)
        try:
            with open(settings_directory) as settings_file:
                loaded_settings = load(settings_file)

                cls._SETTINGS.update(loaded_settings)
                cls._validate_settings(cls._SETTINGS, default_settings, settings_directory)
        except (FileNotFoundError, JSONDecodeError):
            cls.dump_settings(settings_directory, cls._SETTINGS)

        if cls._SETTINGS.keys() != default_settings.keys():
            keys = (key for key in set(cls._SETTINGS) if key not in default_settings)
            for key in keys:
                cls._SETTINGS.pop(key)

    @classproperty
    def settings(cls) -> dict:
        if cls._SETTINGS is None:
            cls._load_settings()

        return cls._SETTINGS

    @classmethod
    def get_world_settings(cls, home_world: HomeWorldIds) -> Dict[str, Any]:
        name_base = home_world.settings_name_base
        keys = cls.WorldSettingNames._names(home_world)

        return {key: cls.settings['{}_{}'.format(name_base, key)] for key in keys}

    @classmethod
    def get_notification_setting(cls, notification_type: NotificationType) -> bool:
        return cls.settings[notification_type.setting_name]

    @classproperty
    def should_show_notification(cls) -> Dict[NotificationType, bool]:
        return {notif_type: cls.settings[notif_type.setting_name] for notif_type in NotificationType.exported_values}

    @classproperty
    def bidirectional_toggle(cls) -> bool: return cls.settings[cls.SettingNames.BIDIRECTIONAL_TOGGLE]

    @classproperty
    def high_school_toggle(cls) -> bool: return cls.settings[cls.SettingNames.HIGH_SCHOOL_TOGGLE]

    @classproperty
    def soft_filter_value(cls) -> float: return cls.settings[cls.SettingNames.SOFT_FILTER_VALUE]

    @classmethod
    def get_token(cls, setting_key: str, enabled_token=None, disabled_token=None, *string_tokens):
        value = cls.settings.get(setting_key, False)
        token = enabled_token if value else disabled_token

        if not token:
            return token
        return token(*string_tokens)

    @classmethod
    def update_setting(cls, setting_key: str, setting_value):
        if setting_key not in cls.settings:
            return False

        cls.settings[setting_key] = setting_value
        cls.dump_settings(cls.settings_directory, cls.settings)

        return True

    @classmethod
    def toggle_setting(cls, setting_key: str, setting_value: bool = None):
        if setting_key not in cls.settings:
            raise KeyError(f'Setting key {setting_key} not in Settings!')

        new_value = setting_value if setting_value is not None else not cls.settings[setting_key]
        cls.update_setting(setting_key, new_value)

        return new_value


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = ('Settings', )
